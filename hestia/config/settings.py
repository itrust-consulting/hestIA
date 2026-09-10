from __future__ import annotations

import json
import os
import pathlib

from pydantic import BaseModel

from hestia.domain.exceptions import ConfigurationError


# ---------------------------------------------------------------------------
# Sub-configs (composed into Settings)
# ---------------------------------------------------------------------------

class AuthSettings(BaseModel):
    auth_mode: str = "local"            # "local" | "ldap" | "oidc"
    ldap_group_mapping: dict[str, list[str]] | None = None
    password_min_length: int = 15
    max_failed_attempts: int = 5
    lockout_duration_minutes: int = 5
    ip_rate_limit_max_attempts: int = 30      # shared anti-spraying budget across all logins,
    ip_rate_limit_window_minutes: int = 1     # see login_ip_key/login_ip_rate_limit (api/limiter.py)
    token_secret_key: str = ""          # required when auth is enabled
    token_encoding_alg: str = "HS256"
    token_lifetime_minutes: int = 60  # was 360 -- see M1 in the full-stack audit: with logout now
                                       # able to revoke a token (see revoke_token/is_token_revoked),
                                       # this only bounds exposure for tokens minted before that
                                       # existed, or never explicitly logged out
    audit_logs: bool = False


class OIDCSettings(BaseModel):
    provider_url: str = ""              # https://keycloak.example.com/realms/myrealm
    client_id: str = ""
    client_secret: str = ""
    scopes: list[str] = ["openid", "profile", "email"]
    role_claim: str = "roles"           # userinfo claim containing roles/groups
    role_mapping: dict[str, list[str]] | None = None  # OIDC role → local role
    org_claim: str = "organization"     # userinfo claim for tenant auto-assignment
    org_mapping: dict[str, str] | None = None  # OIDC org name → hestia tenant name
    redirect_uri_allowlist: list[str] = []  # exact redirect_uri values callers may request


class LDAPSettings(BaseModel):
    host: str = ""
    port: int = 636
    search_base: str = ""
    user_attribute: str = "uid"
    mail_attribute: str = "mail"
    use_ssl: bool = True
    validate_cert: bool = True
    bind_dn: str | None = None
    bind_password: str | None = None
    user_dn_template: str | None = None
    allowed_groups: set[str] | None = None
    mode: str = "auto"


# ---------------------------------------------------------------------------
# Root settings object
# ---------------------------------------------------------------------------

# @MRS-005
class Settings(BaseModel):
    model_config = {"arbitrary_types_allowed": True}

    # --- app ---
    version: str = "alpha_v0.3.0"
    port: int = 5556

    # --- backends ---
    llm_backend: str = "vllm"
    db_backend: str = "qdrant"
    services_to_start: list[str] = ["encDense", "encSparse", "generate", "chat", "search", "ingestion"]

    # --- urls ---
    llm_url: str = "http://localhost:8000"
    emb_url: str = llm_url
    rrk_url: str = llm_url
    db_url: str = "http://localhost:6333"
    llm_api_key: str | None = None
    db_api_key: str | None = None

    # --- models ---
    default_gen_model: str = "ministral-3:14b"
    default_emb_model: str = "qwen3-embedding:0.6b"
    default_rkk_model: str = "dengcao/Qwen3-Reranker-4B:Q8_0"

    # --- auth ---
    auth: AuthSettings | None = None
    ldap: LDAPSettings | None = None
    oidc: OIDCSettings | None = None

    # --- bootstrap admin (first-boot only; see container._bootstrap_admin_user) ---
    bootstrap_admin_username: str | None = None
    bootstrap_admin_password: str | None = None
    bootstrap_admin_email: str | None = None
    bootstrap_admin_first_name: str = "Admin"
    bootstrap_admin_last_name: str = "User"

    # --- paths ---
    project_root: pathlib.Path = pathlib.Path(".")
    app_data: pathlib.Path = pathlib.Path("./app/data")
    udb_path: pathlib.Path = pathlib.Path("./app/data/users.db")
    corpus_stats: pathlib.Path = pathlib.Path("./app/data/corpus_stats")

    # --- logging ---
    log_level: str = "INFO"
    log_dir: pathlib.Path = pathlib.Path("./app/logs")
    log_to_console: bool = True

    # --- limits ---
    pbkdf2_iterations: int = 210_000
    request_timeout: tuple[float, float] = (10.0, 800.0)

    # --- context budget ---
    max_context_tokens: int = 32000
    summary_target_tokens: int = 6000
    summary_model: str | None = None   # falls back to default_gen_model if unset

    classification_labels: list[str] = [
        "public", "public (pu)",
        "internal", "internal (in)",
        "confidential", "confidential (co)",
        "restricted", "restricted (re)",
        "secret", "secret (se)",
    ]

    def insecure_llm_urls(self) -> list[tuple[str, str]]:
        """(setting_name, url) pairs among llm_url/emb_url/rrk_url that are
        explicitly http:// (not just schemeless/misconfigured) and not
        localhost/127.0.0.1 -- HttpClient sends these an
        Authorization: Bearer <api_key> header, so a non-https, non-local
        base_url means that key travels in cleartext."""
        from urllib.parse import urlparse
        insecure = []
        for name in ("llm_url", "emb_url", "rrk_url"):
            url = getattr(self, name)
            parsed = urlparse(url)
            if parsed.scheme == "http" and parsed.hostname not in ("localhost", "127.0.0.1"):
                insecure.append((name, url))
        return insecure

    # ---------------------------------------------------------------------------
    # Factory — the single place all env vars are read
    # ---------------------------------------------------------------------------

    @classmethod
    def load(cls) -> "Settings":
        llm_url = os.getenv("LLM_URL", "localhost:8000")
        default_llm_model = os.getenv("DEFAULT_GEN_MODEL")

        project_root = pathlib.Path(
            os.path.abspath(os.path.join(__file__, "../../.."))
        ).resolve()
        app_data = project_root / (os.getenv("HESTIA_DATA_DIR") or "app/data")

        max_context_tokens = int(os.getenv("MAX_CONTEXT_TOKENS", "32000"))
        summary_target_tokens = int(os.getenv("SUMMARY_TARGET_TOKENS", "6000"))
        if summary_target_tokens >= max_context_tokens:
            raise ConfigurationError("SUMMARY_TARGET_TOKENS must be less than MAX_CONTEXT_TOKENS")

        auth = _load_auth_settings()
        ldap: LDAPSettings | None = None
        oidc: OIDCSettings | None = None
        if auth.auth_mode == "ldap":
            ldap = _load_ldap_settings()
        elif auth.auth_mode == "oidc":
            oidc = _load_oidc_settings()

        return cls(
            port=int(os.getenv("PORT", "5555")),
            llm_backend=os.getenv("LLM_BACKEND", "vllm"),
            db_backend=os.getenv("DB_BACKEND", "qdrant"),
            llm_url=llm_url,
            emb_url=os.getenv("EMB_URL", llm_url),
            rrk_url=os.getenv("RRK_URL", llm_url),
            db_url=os.getenv("DB_URL", "http://localhost:6333"),
            llm_api_key=os.getenv("LLM_API_KEY") or None,
            db_api_key=os.getenv("DB_API_KEY") or None,
            default_gen_model=default_llm_model,
            default_emb_model=os.getenv("DEFAULT_EMB_MODEL", default_llm_model),
            default_rkk_model=os.getenv("DEFAULT_RKK_MODEL", default_llm_model),
            auth=auth,
            ldap=ldap,
            oidc=oidc,
            bootstrap_admin_username=os.getenv("DEFAULT_ADMIN_USERNAME") or None,
            bootstrap_admin_password=os.getenv("DEFAULT_ADMIN_PASSWORD") or None,
            bootstrap_admin_email=os.getenv("DEFAULT_ADMIN_EMAIL") or None,
            bootstrap_admin_first_name=os.getenv("DEFAULT_ADMIN_FIRST_NAME", "Admin"),
            bootstrap_admin_last_name=os.getenv("DEFAULT_ADMIN_LAST_NAME", "User"),
            project_root=project_root,
            app_data=app_data,
            udb_path=app_data / "users.db",
            corpus_stats=app_data / "corpus_stats",
            log_level=os.getenv("LOG_LEVEL", "INFO"),
            log_dir=app_data.parent / (os.getenv("LOG_DIR") or "logs"),
            log_to_console=os.getenv("LOG_TO_CONSOLE", "true").lower() == "true",
            max_context_tokens=max_context_tokens,
            summary_target_tokens=summary_target_tokens,
            summary_model=os.getenv("SUMMARY_MODEL") or None,
        )


# ---------------------------------------------------------------------------
# Private loaders — called only from Settings.load()
# ---------------------------------------------------------------------------

def _load_auth_settings() -> AuthSettings:
    settings = AuthSettings(
        auth_mode=os.getenv("AUTH_MODE", "local").lower(),
        ldap_group_mapping=_parse_ldap_group_mapping(os.getenv("LDAP_GROUP_MAPPING")),
        password_min_length=int(os.getenv("AUTH_PW_LENGTH", "15")),
        max_failed_attempts=int(os.getenv("AUTH_MAX_ATTEMPTS", "5")),
        lockout_duration_minutes=int(os.getenv("AUTH_LOCKOUT_DURATION", "5")),
        ip_rate_limit_max_attempts=int(os.getenv("AUTH_IP_RATE_LIMIT_ATTEMPTS", "30")),
        ip_rate_limit_window_minutes=int(os.getenv("AUTH_IP_RATE_LIMIT_WINDOW_MINUTES", "1")),
        token_secret_key=os.getenv("AUTH_SECRET_KEY", ""),
        token_encoding_alg=os.getenv("AUTH_ENCODING_ALGORITHM", "HS256"),
        token_lifetime_minutes=int(os.getenv("AUTH_TOKEN_LIFETIME", "60")),
        audit_logs=os.getenv("AUTH_AUDIT_LOGS", "false").lower() == "true",
    )
    if len(settings.token_secret_key) < 32:
        raise ConfigurationError(
            "AUTH_SECRET_KEY must be at least 32 characters. "
            "Generate one with: python -c \"import secrets; print(secrets.token_hex(32))\""
        )
    return settings


def _load_oidc_settings() -> OIDCSettings:
    return OIDCSettings(
        provider_url=os.getenv("OIDC_PROVIDER_URL", ""),
        client_id=os.getenv("OIDC_CLIENT_ID", ""),
        client_secret=os.getenv("OIDC_CLIENT_SECRET", ""),
        scopes=_parse_list(os.getenv("OIDC_SCOPES", "openid,profile,email")),
        role_claim=os.getenv("OIDC_ROLE_CLAIM", "roles"),
        role_mapping=_parse_ldap_group_mapping(os.getenv("OIDC_ROLE_MAPPING")),
        org_claim=os.getenv("OIDC_ORG_CLAIM", "organization"),
        org_mapping=_parse_str_mapping(os.getenv("OIDC_ORG_MAPPING")),
        redirect_uri_allowlist=_parse_list(os.getenv("OIDC_REDIRECT_ALLOWLIST", "")),
    )


def _load_ldap_settings() -> LDAPSettings:
    return LDAPSettings(
        host=os.getenv("LDAP_HOST", ""),
        port=int(os.getenv("LDAP_PORT", "636")),
        search_base=os.getenv("LDAP_SEARCH_BASE", ""),
        user_attribute=os.getenv("LDAP_USER_ATTRIBUTE", "uid"),
        mail_attribute=os.getenv("LDAP_MAIL_ATTRIBUTE", "mail"),
        user_dn_template=os.getenv("LDAP_USER_DN_TEMPLATE", ""),
        allowed_groups=_parse_set(os.getenv("LDAP_GROUP_FILTER")),
        bind_dn=os.getenv("LDAP_APP_DN", ""),
        bind_password=os.getenv("LDAP_APP_PASSWORD", ""),
        use_ssl=os.getenv("LDAP_USE_SSL", "true").lower() == "true",
        validate_cert=os.getenv("LDAP_VALIDATE_CERT", "true").lower() == "true",
        mode=os.getenv("LDAP_MODE", "auto"),
    )


def _parse_str_mapping(raw: str | None) -> dict[str, str] | None:
    if not raw:
        return None
    data = json.loads(raw)
    if not isinstance(data, dict):
        raise ConfigurationError("OIDC_ORG_MAPPING must be a JSON object")
    return data


def _parse_ldap_group_mapping(raw: str | None) -> dict[str, list[str]] | None:
    if not raw:
        return None
    data = json.loads(raw)
    if not isinstance(data, dict):
        raise ConfigurationError("LDAP_GROUP_MAPPING must be a JSON object")
    return {k.lower(): v for k, v in data.items()}


def _parse_set(value: str | None) -> set[str] | None:
    if not value:
        return None
    return {v.strip().lower() for v in value.split(",") if v.strip()}


def _parse_list(value: str | None) -> list[str]:
    if not value:
        return []
    return [v.strip() for v in value.split(",") if v.strip()]
