from __future__ import annotations

import requests
from fastapi import APIRouter, Depends, HTTPException

from hestia.api.dependencies import get_handler
from hestia.api.security import assert_admin, get_current_user
from hestia.api.schemas.requests import AuthSettingsTestRequest, AuthSettingsUpdateRequest
from hestia.domain.auth.models import User
from hestia.domain.auth.users import LDAPService
from hestia.handler import RequestHandler
from hestia.infrastructure.logging.audit import audit

router = APIRouter()

# All auth_settings columns this request writes -- excludes request_id/meta
# (inherited from Request) and tested (a save-gate flag, not a column).
_SETTINGS_FIELDS = (
    "auth_mode", "password_min_length", "max_failed_attempts", "lockout_duration_minutes",
    "token_lifetime_minutes", "token_secret_key", "audit_logs", "ldap_group_mapping",
    "oidc_provider_url", "oidc_client_id", "oidc_client_secret", "oidc_scopes", "oidc_role_claim",
    "oidc_role_mapping", "oidc_org_claim", "oidc_org_mapping",
    "ldap_host", "ldap_port", "ldap_search_base", "ldap_user_attribute", "ldap_mail_attribute",
    "ldap_use_ssl", "ldap_validate_cert", "ldap_bind_dn", "ldap_bind_password", "ldap_user_dn_template",
    "ldap_allowed_groups",
)

def _mask(row: dict) -> dict:
    masked = {k: v for k, v in row.items() if k not in ("token_secret_key", "oidc_client_secret", "ldap_bind_password")}
    masked["has_token_secret_key"] = bool(row.get("token_secret_key"))
    masked["has_oidc_client_secret"] = bool(row.get("oidc_client_secret"))
    masked["has_ldap_bind_password"] = bool(row.get("ldap_bind_password"))
    return masked


@router.get("/auth/settings")
def get_auth_settings(
    h: RequestHandler = Depends(get_handler),
    user: User = Depends(get_current_user),
):
    assert_admin(user)
    repo = h.container.services.get("auth_settings")
    row = repo.get_settings() if repo else None
    if row is None:
        raise HTTPException(503, "Authentication settings are unavailable.")
    return _mask(row)


@router.put("/auth/settings")
def update_auth_settings(
    req: AuthSettingsUpdateRequest,
    h: RequestHandler = Depends(get_handler),
    user: User = Depends(get_current_user),
):
    assert_admin(user)
    repo = h.container.services.get("auth_settings")
    if repo is None:
        raise HTTPException(503, "Authentication settings are unavailable.")
    if req.token_secret_key is not None and len(req.token_secret_key) < 32:
        raise HTTPException(400, "Signing key must be at least 32 characters.")

    # The frontend always calls POST /auth/settings/test immediately before
    # this and blocks the save on a failed test -- same client-enforced
    # pattern as the LLM connection save flow (llm_settings.py has no
    # server-side "was tested" check either); this endpoint trusts that.
    current = repo.get_settings() or {}
    changed = [
        key for key in _SETTINGS_FIELDS
        if key not in ("token_secret_key", "oidc_client_secret", "ldap_bind_password")
        and getattr(req, key) != current.get(key)
    ]
    if req.token_secret_key is not None:
        changed.append("token_secret_key")
    if req.oidc_client_secret is not None:
        changed.append("oidc_client_secret")
    if req.ldap_bind_password is not None:
        changed.append("ldap_bind_password")

    fields = {key: getattr(req, key) for key in _SETTINGS_FIELDS}
    repo.update_settings(**fields)
    h.container.apply_auth_update()

    audit.admin_action(actor_id=str(user.id), action="auth_settings_update", target="auth", detail={"changed": changed})
    return {"ok": True}


@router.post("/auth/settings/test")
def test_auth_settings(
    req: AuthSettingsTestRequest,
    h: RequestHandler = Depends(get_handler),
    user: User = Depends(get_current_user),
):
    """Tests connectivity for OIDC/LDAP config that isn't (yet) saved --
    gates saving a mode switch or a connectivity-field edit, mirroring the
    LLM connection test-before-save pattern in llm_settings.py."""
    assert_admin(user)
    repo = h.container.services.get("auth_settings")
    current = (repo.get_settings() if repo else None) or {}

    if req.auth_mode == "local":
        return {"ok": True}

    if req.auth_mode == "ldap":
        bind_password = req.ldap_bind_password
        if not bind_password:
            bind_password = current.get("ldap_bind_password")
        try:
            ldap = LDAPService(
                host=req.ldap_host, port=req.ldap_port, search_base=req.ldap_search_base,
                user_attribute=req.ldap_user_attribute, mail_attribute=req.ldap_mail_attribute,
                bind_dn=req.ldap_bind_dn, bind_password=bind_password,
                use_ssl=req.ldap_use_ssl, validate_cert=req.ldap_validate_cert,
            )
            conn = ldap._service_bind()
            if conn is None:
                return {"ok": False, "error": "Bind failed -- check host/port/bind DN/password."}
            conn.unbind()
            return {"ok": True}
        except Exception as e:
            return {"ok": False, "error": f"Unexpected error: {e}"}

    # oidc -- a real token exchange needs an actual authorization code, so
    # this only checks that the provider is reachable at all (same scope as
    # the LLM connection test: connectivity, not a full round trip).
    if not req.oidc_provider_url.strip():
        raise HTTPException(400, "Provider URL is required")
    try:
        resp = requests.get(req.oidc_provider_url.strip(), timeout=10)
        return {"ok": True, "status": resp.status_code}
    except requests.RequestException as e:
        return {"ok": False, "error": str(e)}
