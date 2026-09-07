from __future__ import annotations

from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field

from hestia.api.schemas.base import APIModel, Request
from hestia.domain.rag.types import DenseVector, HybridQuery, Query, SparseVector


# ---- LLM generation ----

class GenerateRequest(Request):
    prompt: str
    model: Optional[str] = None
    model_kwargs: Optional[Dict[str, Any]] = None
    collection: Optional[str] = None
    query_kwargs: Optional[Dict[str, Any]] = None
    stream: bool = False


# ---- Chat ----

# @MRS-037
class ChatRequest(Request):
    conversation_id: Optional[str] = None
    conversation_title: Optional[str] = None
    messages: List[Dict[str, Any]]
    model: Optional[str] = None
    model_kwargs: Optional[Dict[str, Any]] = None
    collection: Optional[str] = None
    query_kwargs: Optional[Dict[str, Any]] = None
    save_chat: bool = False
    stream: bool = False
    last_user_display_content: Optional[str] = None
    last_user_attachments: Optional[List[Dict[str, Any]]] = None


# ---- Encode ----

class EncodeRequest(BaseModel):
    type: Literal["dense", "sparse"]
    input: str
    model: Optional[str] = None
    options: Optional[Dict[str, Any]] = None
    collection: Optional[str] = None


class EncodeResponse(BaseModel):
    type: Literal["dense", "sparse"]
    vector: Any
    model: Optional[str] = None
    meta: Optional[Dict[str, Any]] = None


# ---- Search ----

QueryMode = Literal["semantic", "keyword", "hybrid"]


class SearchRequest(Request):
    mode: QueryMode = Field("dense")
    query: List[float | int] | Dict[str, Any]
    collection: str
    options: Dict[str, Any] = None


# ---- User management ----

class CreateUserRequest(Request):
    username: str
    email: str
    first_name: str
    last_name: str
    password: str
    roles: list[int] = Field([0])
    organization: str | None = None
    expires_at: int | None = None


class CreateOrgRequest(Request):
    name: str
    abbreviation: str


class UpdateOrgRequest(Request):
    name: str
    abbreviation: str


# ---- LLM settings ----
# A connection backs one purpose (generation/embedding/reranking/vector_db);
# a purpose may have several connections but at most one active at a time.
# purpose and backend_type are fixed at creation and can't be edited
# afterward (delete + recreate under the other section to change them).

class LLMConnectionCreateRequest(Request):
    purpose: Literal["generation", "embedding", "reranking", "vector_db"]
    backend_type: Literal["ollama", "openai", "qdrant"]
    base_url: str
    api_key: Optional[str] = None


class LLMConnectionUpdateRequest(Request):
    base_url: str
    api_key: Optional[str] = None  # blank/omitted means "keep existing key"
    model: str = ""
    params: Dict[str, Any] = {}
    # Only meaningful for a purpose='generation' connection -- ignored for
    # any other. compaction_model blank means "use this connection's own
    # model"; compaction_context_window/compaction_summary_length blank
    # fall back to the global Settings.max_context_tokens/summary_target_tokens.
    compaction_enabled: bool = False
    compaction_model: Optional[str] = None
    compaction_context_window: Optional[int] = None
    compaction_summary_length: Optional[int] = None


class LLMConnectionTestRequest(Request):
    backend_type: Literal["ollama", "openai", "qdrant"]
    base_url: str
    api_key: Optional[str] = None
    # Present only when testing an edit to an existing connection. A blank
    # api_key there means "keep the existing key" (see
    # LLMConnectionUpdateRequest) -- the raw key is never sent to the
    # client, so the backend looks it up by id to test what will actually
    # be saved/used.
    connection_id: Optional[int] = None


# ---- Logging settings ----

class LogSettingsUpdateRequest(Request):
    log_level: str


# ---- Workflow settings ----

class WorkflowUpdateRequest(Request):
    yaml_text: str


class WorkflowCreateRequest(Request):
    name: str
    # Omitted/None means "use the minimal starter graph" -- see
    # hestia/api/routers/workflow_settings.py's _STARTER_YAML.
    yaml_text: Optional[str] = None


# ---- Auth settings ----
# Global, single-row config (mode, password policy, JWT signing, OIDC,
# LDAP). Secret fields (token_secret_key, oidc_client_secret,
# ldap_bind_password) are Optional[str] = None -- blank/omitted means "keep
# the existing value", never sent back to the client in GET responses.

class AuthSettingsUpdateRequest(Request):
    auth_mode: Literal["local", "ldap", "oidc"]
    password_min_length: int
    max_failed_attempts: int
    lockout_duration_minutes: int
    token_lifetime_minutes: int
    token_secret_key: Optional[str] = None
    audit_logs: bool = False
    ldap_group_mapping: Optional[Dict[str, List[str]]] = None

    oidc_provider_url: str = ""
    oidc_client_id: str = ""
    oidc_client_secret: Optional[str] = None
    oidc_scopes: List[str] = []
    oidc_role_claim: str = "roles"
    oidc_role_mapping: Optional[Dict[str, List[str]]] = None
    oidc_org_claim: str = "organization"
    oidc_org_mapping: Optional[Dict[str, str]] = None

    ldap_host: str = ""
    ldap_port: int = 636
    ldap_search_base: str = ""
    ldap_user_attribute: str = "uid"
    ldap_mail_attribute: str = "mail"
    ldap_use_ssl: bool = True
    ldap_validate_cert: bool = True
    ldap_bind_dn: Optional[str] = None
    ldap_bind_password: Optional[str] = None
    ldap_user_dn_template: Optional[str] = None
    ldap_allowed_groups: Optional[List[str]] = None


class AuthSettingsTestRequest(Request):
    auth_mode: Literal["local", "ldap", "oidc"]

    oidc_provider_url: str = ""
    oidc_client_id: str = ""
    oidc_client_secret: Optional[str] = None  # blank means "use the currently-saved secret"

    ldap_host: str = ""
    ldap_port: int = 636
    ldap_search_base: str = ""
    ldap_user_attribute: str = "uid"
    ldap_mail_attribute: str = "mail"
    ldap_use_ssl: bool = True
    ldap_validate_cert: bool = True
    ldap_bind_dn: Optional[str] = None
    ldap_bind_password: Optional[str] = None  # blank means "use the currently-saved password"
