from __future__ import annotations

import logging
import uuid

from hestia.config.settings import AuthSettings
from hestia.domain.auth.models import AuthResult
from hestia.domain.auth.oidc import OIDCService
from hestia.domain.auth.users import LDAPService, UserService
from hestia.infrastructure.logging.audit import audit

_log = logging.getLogger("hestia.system")


class AuthenticationService:

    def __init__(
        self,
        local: UserService,
        ldap: LDAPService | None = None,
        oidc: OIDCService | None = None,
        *,
        config: AuthSettings | None = None,
    ):
        self.local = local
        self.ldap = ldap
        self.oidc = oidc
        self.config = config

    def _audit_auth_attempt(self, **kwargs) -> None:
        """Gated by AuthSettings.audit_logs -- off by default. config is
        realistically never None (this service is only built when auth is
        enabled, always with config=settings.auth), but fails open just in
        case, matching the previous unconditional behavior."""
        if self.config is None or self.config.audit_logs:
            audit.auth_attempt(**kwargs)

    def audit_logout(self, *, user_id: str, username: str, source: str) -> None:
        """Called from the /logout route (api/routers/auth.py) -- unlike
        _audit_auth_attempt this is invoked externally, so it's public.
        Gated by the same AuthSettings.audit_logs toggle as login attempts,
        keeping the whole auth audit trail (login + logout) governed by one
        setting."""
        if self.config is None or self.config.audit_logs:
            audit.logout(user_id=user_id, username=username, source=source)

    def authenticate(self, identifier: str, password: str) -> AuthResult:
        local_result = self.local.authenticate(identifier, password)

        if local_result.success:
            local_result.auth_source = "local"
            self._audit_auth_attempt(username=identifier, success=True, source="local")
            return local_result

        if self.ldap:
            ldap_result = self.ldap.authenticate(identifier, password)

            if ldap_result.success:
                roles: list[str] = []
                if self.config and self.config.ldap_group_mapping:
                    role_names: set[str] = set()
                    for group in (ldap_result.groups or []):
                        role_names.update(self.config.ldap_group_mapping.get(group, []))
                    roles = list(role_names)

                if local_result.user_id:
                    local_result.success = True
                    local_result.message = "Login successful."
                    self._audit_auth_attempt(username=identifier, success=True, source="ldap")
                    return local_result

                new_user_id = self.local.create_user(
                    username=ldap_result.username,
                    email=ldap_result.email,
                    auth_source="ldap",
                    password="__ldap__",
                    first_name=ldap_result.first_name or "",
                    last_name=ldap_result.last_name or "",
                    roles=roles or ["user"],
                    must_change_pw=0,
                    expires_at=None,
                )

                _log.info("ldap_user_provisioned", extra={"username": ldap_result.username})
                self._audit_auth_attempt(username=identifier, success=True, source="ldap",
                                          reason="auto-provisioned")

                return AuthResult(
                    success=True,
                    message="Login successful (LDAP, auto-provisioned).",
                    user_id=new_user_id,
                    username=ldap_result.username,
                    email=ldap_result.email,
                    first_name=ldap_result.first_name,
                    last_name=ldap_result.last_name,
                    groups=ldap_result.groups,
                    auth_source="ldap",
                    must_change_pw=0,
                )

        source = "local+ldap" if self.ldap else "local"
        self._audit_auth_attempt(username=identifier, success=False, source=source,
                                  reason="invalid_credentials")
        return AuthResult.nack()

    async def authenticate_oidc(self, code: str, redirect_uri: str, code_verifier: str | None = None) -> AuthResult:
        if not self.oidc:
            self._audit_auth_attempt(username="unknown", success=False, source="oidc",
                                      reason="oidc_not_configured")
            return AuthResult.nack("OIDC not configured.")

        try:
            token_data = await self.oidc.exchange_code(code, redirect_uri, code_verifier=code_verifier)
        except Exception as e:
            _log.warning("oidc_token_exchange_failed", extra={"error": str(e)})
            self._audit_auth_attempt(username="unknown", success=False, source="oidc",
                                      reason="token_exchange_failed")
            return AuthResult.nack("OIDC token exchange failed.")

        access_token = token_data.get("access_token")
        if not access_token:
            self._audit_auth_attempt(username="unknown", success=False, source="oidc",
                                      reason="missing_access_token")
            return AuthResult.nack("OIDC response missing access_token.")

        try:
            user_info = await self.oidc.get_user_info(access_token)
        except Exception as e:
            _log.warning("oidc_userinfo_failed", extra={"error": str(e)})
            self._audit_auth_attempt(username="unknown", success=False, source="oidc",
                                      reason="userinfo_failed")
            return AuthResult.nack("Failed to fetch OIDC user info.")

        email = user_info.get("email")
        if not email:
            fallback_username = user_info.get("preferred_username") or "unknown"
            self._audit_auth_attempt(username=fallback_username, success=False, source="oidc",
                                      reason="missing_email")
            return AuthResult.nack("OIDC user info missing email.")

        username = user_info.get("preferred_username") or email
        first_name = user_info.get("given_name") or ""
        last_name = user_info.get("family_name") or ""

        oidc_roles = self.oidc.extract_roles(user_info)
        roles: list[str] = []
        if self.oidc.settings.role_mapping:
            mapped: set[str] = set()
            for r in oidc_roles:
                mapped.update(self.oidc.settings.role_mapping.get(r, []))
            roles = list(mapped)

        oidc_orgs = self.oidc.extract_orgs(user_info)
        first_org = oidc_orgs[0] if oidc_orgs else None

        existing = self.local.repo.get_user_by_email(email)
        if existing:
            user_id = uuid.UUID(bytes=existing["id"])
            self._audit_auth_attempt(username=username, success=True, source="oidc")
            return AuthResult(
                success=True,
                message="Login successful.",
                user_id=user_id,
                username=existing["username"],
                email=email,
                first_name=existing["first_name"],
                last_name=existing["last_name"],
                auth_source="oidc",
                must_change_pw=0,
            )

        user_id = self.local.create_user(
            username=username,
            email=email,
            auth_source="oidc",
            password="__oidc__",
            first_name=first_name,
            last_name=last_name,
            roles=roles or ["user"],
            organization=first_org,
            must_change_pw=0,
        )

        _log.info("oidc_user_provisioned", extra={"username": username, "email": email})
        self._audit_auth_attempt(username=username, success=True, source="oidc", reason="auto-provisioned")

        return AuthResult(
            success=True,
            message="Login successful (OIDC, auto-provisioned).",
            user_id=user_id,
            username=username,
            email=email,
            first_name=first_name,
            last_name=last_name,
            auth_source="oidc",
            must_change_pw=0,
        )
