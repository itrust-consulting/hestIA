from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Dict

from hestia.config.settings import Settings
from hestia.domain.exceptions import ConfigurationError

_log = logging.getLogger("hestia.system")
from hestia.application.ingestion import IngestionPipeline
from hestia.domain.auth.oidc import OIDCService
from hestia.domain.auth.service import AuthenticationService
from hestia.domain.auth.users import LDAPService, UserService
from hestia.domain.rag.services import DenseEncoder, Generator, Retriever, SparseEncoder
from hestia.infrastructure.db.qdrant import QdrantDB
from hestia.infrastructure.db.user_repository import UserRepository, create_sqlite_connection
from hestia.infrastructure.llm.ollama import OllamaProvider
from hestia.infrastructure.llm.vllm import vLLMProvider


@dataclass
class Container:
    settings: Settings
    providers: Dict[str, Any] = field(default_factory=dict)
    services: Dict[str, Any] = field(default_factory=dict)


def build_container(settings: Settings) -> Container:
    c = Container(settings=settings)

    # --- LLM provider ---
    if settings.llm_backend == "vllm":
        llm = vLLMProvider(
            chat=settings.llm_url,
            embed=settings.emb_url,
            rerank=settings.rrk_url,
            timeout=settings.request_timeout,
        )
    elif settings.llm_backend == "ollama":
        llm = OllamaProvider(http=settings.llm_url, timeout=settings.request_timeout)
    else:
        raise ConfigurationError(f"Unknown LLM backend: '{settings.llm_backend}'")
    c.providers["llm"] = llm
    _log.info("provider_init", extra={"provider": "llm", "backend": settings.llm_backend, "url": settings.llm_url})

    # --- DB provider ---
    if settings.db_backend == "qdrant":
        c.providers["db"] = QdrantDB(http=settings.db_url)
    else:
        raise ConfigurationError(f"Unknown DB backend: '{settings.db_backend}'")
    _log.info("provider_init", extra={"provider": "db", "backend": settings.db_backend, "url": settings.db_url})

    # --- Auth services ---
    if settings.enable_auth:
        get_conn, close, lock = create_sqlite_connection(str(settings.udb_path))
        repo = UserRepository(get_conn, lock)
        repo.initialize()
        close()

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

    # --- RAG services ---
    requested = set(settings.services_to_start)
    generator = Generator(provider=llm, model=settings.default_gen_model)

    if "encDense" in requested:
        c.services["encDense"] = DenseEncoder(provider=llm, model=settings.default_emb_model)
        _log.info("service_init", extra={"service": "encDense", "model": settings.default_emb_model})

    if "encSparse" in requested:
        sparse_enc = SparseEncoder(corpus_dir=settings.corpus_dir)
        sparse_enc.preload_all()
        c.services["encSparse"] = sparse_enc
        _log.info("service_init", extra={"service": "encSparse", "corpus_dir": str(settings.corpus_dir)})

    if "generate" in requested:
        c.services["generate"] = generator
        _log.info("service_init", extra={"service": "generate", "model": settings.default_gen_model})

    if "chat" in requested:
        c.services["chat"] = generator
        _log.info("service_init", extra={"service": "chat", "model": settings.default_gen_model})

    if "search" in requested:
        c.services["search"] = Retriever(provider=c.providers["db"])
        _log.info("service_init", extra={"service": "search", "backend": settings.db_backend})

    if "ingestion" in requested:
        dense_enc = c.services.get("encDense")
        sparse_enc = c.services.get("encSparse")
        if dense_enc is None or sparse_enc is None:
            raise ConfigurationError("'ingestion' service requires 'encDense' and 'encSparse' to be enabled")
        c.services["ingestion"] = IngestionPipeline(
            dense_encoder=dense_enc,
            sparse_encoder=sparse_enc,
            db=c.providers["db"],
        )
        _log.info("service_init", extra={"service": "ingestion"})

    return c
