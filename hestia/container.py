from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Dict, Optional

from hestia.config.settings import Settings
from hestia.domain.exceptions import ConfigurationError

_log = logging.getLogger("hestia.system")
from hestia.application.ingestion import IngestionPipeline
from hestia.domain.auth.oidc import OIDCService
from hestia.domain.auth.service import AuthenticationService
from hestia.domain.auth.users import LDAPService, UserService
from hestia.domain.rag.services import DenseEncoder, Generator, Retriever, SparseEncoder
from hestia.infrastructure.db.llm_settings_repository import LLMSettingsRepository
from hestia.infrastructure.db.qdrant import QdrantDB
from hestia.infrastructure.db.sync_repository import SyncManifestRepository
from hestia.infrastructure.db.user_repository import UserRepository, create_sqlite_connection
from hestia.infrastructure.http.client import HttpClient
from hestia.infrastructure.llm.ollama import OllamaProvider
from hestia.infrastructure.llm.protocol import LLMProvider
from hestia.infrastructure.llm.vllm import vLLMProvider

# Purposes an LLM connection can be assigned to. "reranking" has no live
# consuming service yet, but its provider is still built/cached eagerly so
# the admin settings page can test/use it immediately.
_PURPOSE_SERVICES = {
    "generation": ("generate", "chat"),
    "embedding": ("encDense",),
    "reranking": (),
}


def build_llm_provider(
    backend_type: str, http: str | HttpClient, api_key: Optional[str], timeout: tuple[float, float],
) -> LLMProvider:
    if backend_type == "ollama":
        return OllamaProvider(http=http, timeout=timeout)
    elif backend_type == "openai":
        return vLLMProvider(chat=http, embed=http, rerank=http, timeout=timeout, api_key=api_key)
    raise ConfigurationError(f"Unknown LLM connection backend_type: '{backend_type}'")


def build_db_provider(backend_type: str, base_url: str, api_key: Optional[str]) -> QdrantDB:
    if backend_type == "qdrant":
        return QdrantDB(http=base_url, api_key=api_key)
    raise ConfigurationError(f"Unknown DB connection backend_type: '{backend_type}'")


def _provider_http_client(provider: LLMProvider) -> HttpClient:
    return provider.http if isinstance(provider, OllamaProvider) else provider.http_chat


@dataclass
class Container:
    settings: Settings
    providers: Dict[str, Any] = field(default_factory=dict)
    services: Dict[str, Any] = field(default_factory=dict)
    providers_by_connection: Dict[int, LLMProvider] = field(default_factory=dict)

    async def aclose(self) -> None:
        for llm in self.providers_by_connection.values():
            if hasattr(llm, "aclose"):
                await llm.aclose()

    def get_or_build_provider(self, connection_id: int) -> LLMProvider:
        provider = self.providers_by_connection.get(connection_id)
        if provider is not None:
            return provider
        repo: LLMSettingsRepository = self.services["llm_settings"]
        row = repo.get_connection(connection_id)
        provider = build_llm_provider(row["backend_type"], row["base_url"], row["api_key"], self.settings.request_timeout)
        self.providers_by_connection[connection_id] = provider
        return provider

    def _rewire_purpose(self, purpose: str, provider: LLMProvider, row: Dict[str, Any]) -> None:
        for service_name in _PURPOSE_SERVICES.get(purpose, ()):
            svc = self.services.get(service_name)
            if svc is not None:
                svc.provider = provider
                svc.default_model = row["model"]
                svc.default_options = row["params"] or None

    def apply_connection_update(self, connection_id: int) -> None:
        """A connection's row changed (URL/API key/model/params). Since each
        connection IS one purpose's config 1:1, this both mutates the URL/key
        on the already-open HttpClient in place -- read fresh on every call,
        so nothing needs to be rebuilt -- and refreshes the model/options on
        that purpose's Generator/DenseEncoder. Takes effect on the very next
        request, no restart. backend_type is immutable after creation (the
        UI doesn't expose changing it), so there's no wrapper-class swap to
        handle here."""
        repo: LLMSettingsRepository = self.services["llm_settings"]
        row = repo.get_connection(connection_id)
        if row is None:
            return
        if row["purpose"] == "vector_db":
            self._apply_vector_db_update(row)
            return
        provider = self.get_or_build_provider(connection_id)
        http = _provider_http_client(provider)
        http.base_url = row["base_url"]
        http.api_key = row["api_key"]
        self._rewire_purpose(row["purpose"], provider, row)

    def _apply_vector_db_update(self, row: Dict[str, Any]) -> None:
        """Unlike the LLM purposes' HttpClient (URL/key read fresh per call),
        QdrantDB bakes its URL/api_key into a QdrantClient built once in
        __init__. Rebuild that client in place on the same QdrantDB instance
        already held by Retriever/IngestionPipeline, so they pick up the
        change without themselves being rewired."""
        db = self.providers.get("db")
        if db is None:
            return
        db.client = build_db_provider(row["backend_type"], row["base_url"], row["api_key"]).client

    def apply_connection_delete(self, connection_id: int, purpose: Optional[str] = None) -> None:
        """Drops a no-longer-needed provider from the cache, and unwires
        whatever live service/provider that purpose was backing -- any
        connection can be deleted now, so without this a deleted connection
        would keep silently serving requests through its stale provider
        (old URL/API key) until the process restarts. `purpose` must be read
        by the caller before deleting the row, since it's gone by the time
        this runs."""
        self.providers_by_connection.pop(connection_id, None)
        if purpose == "vector_db":
            self.providers.pop("db", None)
            return
        for service_name in _PURPOSE_SERVICES.get(purpose, ()):
            self.services.pop(service_name, None)

    def require_service(self, name: str) -> Any:
        svc = self.services.get(name)
        if svc is None:
            raise ConfigurationError(f"'{name}' is not configured -- add a connection for it in Admin Settings.")
        return svc

    def require_db_provider(self) -> QdrantDB:
        db = self.providers.get("db")
        if db is None:
            raise ConfigurationError("No vector database connection configured -- add one in Admin Settings.")
        return db


# @MRS-001, @MRS-039
def build_container(settings: Settings) -> Container:
    c = Container(settings=settings)

    # --- Shared SQLite connection (users, sync manifests) ---
    get_conn, close, lock = create_sqlite_connection(str(settings.udb_path))

    # --- LLM settings (one connection per purpose, incl. the vector DB) ---
    llm_settings_repo = LLMSettingsRepository(get_conn, lock)
    llm_settings_repo.initialize(settings)
    c.services["llm_settings"] = llm_settings_repo

    # --- DB provider ---
    db_cfg = llm_settings_repo.get_connection_by_purpose("vector_db")
    if db_cfg is not None:
        c.providers["db"] = build_db_provider(db_cfg["backend_type"], db_cfg["base_url"], db_cfg["api_key"])
        _log.info("provider_init", extra={"provider": "db", "backend": db_cfg["backend_type"], "url": db_cfg["base_url"]})
    else:
        _log.warning("provider_init_skipped", extra={"provider": "db", "purpose": "vector_db"})

    sync_repo = SyncManifestRepository(get_conn, lock)
    sync_repo.initialize()
    c.services["sync_manifest"] = sync_repo

    # --- Auth services ---
    if settings.enable_auth:
        repo = UserRepository(get_conn, lock)
        repo.initialize()

        user_service = UserService(repo, password_min_length=settings.auth.password_min_length)

        ldap: LDAPService | None = None
        if settings.auth and settings.auth.auth_mode == "ldap" and settings.ldap:
            ldap = LDAPService(
                host=settings.ldap.host,
                port=settings.ldap.port,
                search_base=settings.ldap.search_base,
                user_attribute=settings.ldap.user_attribute,
                mail_attribute=settings.ldap.mail_attribute,
                bind_dn=settings.ldap.bind_dn,
                bind_password=settings.ldap.bind_password,
                user_dn_template=settings.ldap.user_dn_template,
                allowed_groups=settings.ldap.allowed_groups,
                use_ssl=settings.ldap.use_ssl,
                validate_cert=settings.ldap.validate_cert,
                mode=settings.ldap.mode,
            )
            _log.info("service_init", extra={"service": "ldap", "host": settings.ldap.host})

        oidc: OIDCService | None = None
        if settings.auth and settings.auth.auth_mode == "oidc" and settings.oidc:
            oidc = OIDCService(settings.oidc)
            _log.info("service_init", extra={"service": "oidc", "provider": settings.oidc.provider_url})

        c.services["auth"] = AuthenticationService(user_service, ldap, oidc, config=settings.auth)
        c.services["users"] = user_service
        _log.info("service_init", extra={"service": "auth", "mode": settings.auth.auth_mode})

    close()

    # --- RAG services ---
    requested = set(settings.services_to_start)

    def _provider_for(row: Optional[Dict[str, Any]]) -> Optional[LLMProvider]:
        return c.get_or_build_provider(row["id"]) if row else None

    gen_cfg = llm_settings_repo.get_connection_by_purpose("generation")
    generator: Optional[Generator] = None
    if gen_cfg is not None:
        generator = Generator(provider=_provider_for(gen_cfg), model=gen_cfg["model"], default_options=gen_cfg["params"] or None)
        _log.info("provider_init", extra={"provider": "llm", "purpose": "generation", "connection_id": gen_cfg["id"]})
    else:
        _log.warning("provider_init_skipped", extra={"provider": "llm", "purpose": "generation"})

    if "encDense" in requested:
        emb_cfg = llm_settings_repo.get_connection_by_purpose("embedding")
        if emb_cfg is not None:
            c.services["encDense"] = DenseEncoder(provider=_provider_for(emb_cfg), model=emb_cfg["model"], default_options=emb_cfg["params"] or None)
            _log.info("service_init", extra={"service": "encDense", "model": emb_cfg["model"]})
        else:
            _log.warning("service_init_skipped", extra={"service": "encDense", "reason": "no 'embedding' connection configured"})

    if "encSparse" in requested:
        sparse_enc = SparseEncoder(corpus_stats=settings.corpus_stats)
        sparse_enc.preload_all()
        c.services["encSparse"] = sparse_enc
        _log.info("service_init", extra={"service": "encSparse", "corpus_stats": str(settings.corpus_stats)})

    if "generate" in requested and generator is not None:
        c.services["generate"] = generator
        _log.info("service_init", extra={"service": "generate", "model": gen_cfg["model"]})

    if "chat" in requested and generator is not None:
        c.services["chat"] = generator
        _log.info("service_init", extra={"service": "chat", "model": gen_cfg["model"]})

    # Reranking has no live consuming service yet, but its provider is built
    # eagerly (if a connection is configured for it) so the admin settings
    # page can test/use it immediately.
    _provider_for(llm_settings_repo.get_connection_by_purpose("reranking"))

    if "search" in requested:
        if "db" in c.providers:
            c.services["search"] = Retriever(provider=c.providers["db"])
            _log.info("service_init", extra={"service": "search", "backend": db_cfg["backend_type"] if db_cfg else None})
        else:
            _log.warning("service_init_skipped", extra={"service": "search", "reason": "no 'vector_db' connection configured"})

    if "ingestion" in requested:
        dense_enc = c.services.get("encDense")
        sparse_enc = c.services.get("encSparse")
        if dense_enc is not None and sparse_enc is not None and "db" in c.providers:
            c.services["ingestion"] = IngestionPipeline(
                dense_encoder=dense_enc,
                sparse_encoder=sparse_enc,
                db=c.providers["db"],
            )
            _log.info("service_init", extra={"service": "ingestion"})
        else:
            _log.warning("service_init_skipped", extra={"service": "ingestion", "reason": "missing 'encDense'/'encSparse'/'vector_db'"})

    return c
