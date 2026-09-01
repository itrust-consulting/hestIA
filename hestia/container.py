from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Dict, Optional

from hestia.config.settings import AuthSettings, LDAPSettings, OIDCSettings, Settings
from hestia.domain.exceptions import ConfigurationError

_log = logging.getLogger("hestia.system")
from hestia.application.ingestion import IngestionPipeline
from hestia.domain.auth.oidc import OIDCService
from hestia.domain.auth.service import AuthenticationService
from hestia.domain.auth.users import LDAPService, UserService
from hestia.domain.rag.services import DenseEncoder, Generator, Retriever, SparseEncoder
from hestia.infrastructure.db.auth_settings_repository import AuthSettingsRepository
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


def _auth_settings_from_row(row: Dict[str, Any]) -> tuple[AuthSettings, OIDCSettings, LDAPSettings]:
    auth = AuthSettings(
        auth_mode=row["auth_mode"], ldap_group_mapping=row["ldap_group_mapping"],
        password_min_length=row["password_min_length"], max_failed_attempts=row["max_failed_attempts"],
        lockout_duration_minutes=row["lockout_duration_minutes"], token_secret_key=row["token_secret_key"],
        token_encoding_alg=row["token_encoding_alg"], token_lifetime_minutes=row["token_lifetime_minutes"],
        audit_logs=row["audit_logs"],
    )
    oidc = OIDCSettings(
        provider_url=row["oidc_provider_url"], client_id=row["oidc_client_id"], client_secret=row["oidc_client_secret"],
        scopes=row["oidc_scopes"], role_claim=row["oidc_role_claim"], role_mapping=row["oidc_role_mapping"],
        org_claim=row["oidc_org_claim"], org_mapping=row["oidc_org_mapping"],
    )
    ldap = LDAPSettings(
        host=row["ldap_host"], port=row["ldap_port"], search_base=row["ldap_search_base"],
        user_attribute=row["ldap_user_attribute"], mail_attribute=row["ldap_mail_attribute"],
        use_ssl=row["ldap_use_ssl"], validate_cert=row["ldap_validate_cert"], bind_dn=row["ldap_bind_dn"],
        bind_password=row["ldap_bind_password"], user_dn_template=row["ldap_user_dn_template"],
        allowed_groups=set(row["ldap_allowed_groups"]) if row["ldap_allowed_groups"] is not None else None,
        mode=row["ldap_mode"],
    )
    return auth, oidc, ldap


def _build_auth_stack(settings: Settings, user_repo: UserRepository) -> tuple[UserService, AuthenticationService]:
    """Shared by build_container (first boot) and Container.apply_auth_update
    (live hot-reload after an admin edits auth settings) so both construct
    the service stack identically."""
    user_service = UserService(user_repo, password_min_length=settings.auth.password_min_length)

    ldap: LDAPService | None = None
    if settings.auth.auth_mode == "ldap" and settings.ldap:
        ldap = LDAPService(
            host=settings.ldap.host, port=settings.ldap.port, search_base=settings.ldap.search_base,
            user_attribute=settings.ldap.user_attribute, mail_attribute=settings.ldap.mail_attribute,
            bind_dn=settings.ldap.bind_dn, bind_password=settings.ldap.bind_password,
            user_dn_template=settings.ldap.user_dn_template, allowed_groups=settings.ldap.allowed_groups,
            use_ssl=settings.ldap.use_ssl, validate_cert=settings.ldap.validate_cert, mode=settings.ldap.mode,
        )
        _log.info("service_init", extra={"service": "ldap", "host": settings.ldap.host})

    oidc: OIDCService | None = None
    if settings.auth.auth_mode == "oidc" and settings.oidc:
        oidc = OIDCService(settings.oidc)
        _log.info("service_init", extra={"service": "oidc", "provider": settings.oidc.provider_url})

    auth_service = AuthenticationService(user_service, ldap, oidc, config=settings.auth)
    _log.info("service_init", extra={"service": "auth", "mode": settings.auth.auth_mode})
    return user_service, auth_service


def _bootstrap_admin_user(settings: Settings, repo: UserRepository, user_service: UserService) -> None:
    """First-boot only: if the user table is empty (fresh install, or every
    account having been deleted), create the initial admin from DEFAULT_ADMIN_*
    env vars so there's always a way to log in. Runs regardless of AUTH_MODE
    (local/ldap/oidc) as a break-glass account. No-op once any user exists."""
    if repo.list_users():
        return
    if not (settings.bootstrap_admin_username and settings.bootstrap_admin_password
            and settings.bootstrap_admin_email):
        raise ConfigurationError(
            "No users exist in the user database and DEFAULT_ADMIN_USERNAME / "
            "DEFAULT_ADMIN_PASSWORD / DEFAULT_ADMIN_EMAIL are not all set -- "
            "set them so a first admin account can be created on boot."
        )
    user_service.create_user(
        username=settings.bootstrap_admin_username,
        email=settings.bootstrap_admin_email,
        password=settings.bootstrap_admin_password,
        first_name=settings.bootstrap_admin_first_name,
        last_name=settings.bootstrap_admin_last_name,
        roles=["admin"],
        must_change_pw=1,
        auth_source="local",
    )
    _log.info("bootstrap_admin_created", extra={"username": settings.bootstrap_admin_username})


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
                if purpose == "generation":
                    svc.compaction_enabled = bool(row["compaction_enabled"])
                    svc.compaction_model = row["compaction_model"]
                    svc.compaction_context_window = row["compaction_context_window"]
                    svc.compaction_summary_length = row["compaction_summary_length"]

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
        change without themselves being rewired. Also refresh the live
        Retriever's default_options, mirroring what _rewire_purpose does for
        Generator/DenseEncoder."""
        db = self.providers.get("db")
        if db is None:
            return
        db.client = build_db_provider(row["backend_type"], row["base_url"], row["api_key"]).client
        search_svc = self.services.get("search")
        if search_svc is not None:
            search_svc.default_options = row["params"] or None

    def apply_auth_update(self) -> None:
        """Auth settings row changed (mode/password policy/token lifetime/
        signing key/OIDC/LDAP config). Rebuilds the auth service stack from
        the DB row and swaps services["auth"]/services["users"] in place --
        get_current_user/_issue_token (api/security.py) read auth_svc.config
        fresh on every request, so this takes effect on the very next
        request. No restart needed. If the signing key or auth_mode changed,
        every previously-issued token becomes invalid on the next request
        that uses it (by design -- the caller is responsible for warning the
        admin before triggering this)."""
        repo: Optional[AuthSettingsRepository] = self.services.get("auth_settings")
        user_repo: Optional[UserRepository] = self.services.get("user_repository")
        if repo is None or user_repo is None:
            return
        row = repo.get_settings()
        if row is None:
            return
        self.settings.auth, self.settings.oidc, self.settings.ldap = _auth_settings_from_row(row)
        user_service, auth_service = _build_auth_stack(self.settings, user_repo)
        self.services["auth"] = auth_service
        self.services["users"] = user_service

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

    # --- Auth settings (global, single row; overlays env-sourced settings.auth/.oidc/.ldap before the auth stack below is built) ---
    auth_settings_repo = AuthSettingsRepository(get_conn, lock)
    auth_settings_repo.initialize(settings)
    c.services["auth_settings"] = auth_settings_repo
    if settings.enable_auth:
        auth_row = auth_settings_repo.get_settings()
        if auth_row is not None:
            settings.auth, settings.oidc, settings.ldap = _auth_settings_from_row(auth_row)

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
        c.services["user_repository"] = repo

        user_service, auth_service = _build_auth_stack(settings, repo)
        _bootstrap_admin_user(settings, repo, user_service)
        c.services["auth"] = auth_service
        c.services["users"] = user_service

    close()

    # --- RAG services ---
    requested = set(settings.services_to_start)

    def _provider_for(row: Optional[Dict[str, Any]]) -> Optional[LLMProvider]:
        return c.get_or_build_provider(row["id"]) if row else None

    gen_cfg = llm_settings_repo.get_connection_by_purpose("generation")
    generator: Optional[Generator] = None
    if gen_cfg is not None:
        generator = Generator(
            provider=_provider_for(gen_cfg), model=gen_cfg["model"], default_options=gen_cfg["params"] or None,
            compaction_enabled=bool(gen_cfg["compaction_enabled"]), compaction_model=gen_cfg["compaction_model"],
            compaction_context_window=gen_cfg["compaction_context_window"],
            compaction_summary_length=gen_cfg["compaction_summary_length"],
        )
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
            c.services["search"] = Retriever(provider=c.providers["db"], default_options=db_cfg["params"] or None)
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
