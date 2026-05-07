
from hestia.schemas.api import AuthResult
from hestia.services.users import UserService, LDAPService
from hestia.config.auth import AuthConfig

class AuthenticationService:
    """
    Handles authentication logic:
      - Local DB auth
      - LDAP auth fallback
      - Optional auto-provisioning for LDAP users
    """

    def __init__(
        self,
        local: UserService,
        ldap: LDAPService | None = None,
        *,
        config: AuthConfig | None = None
    ):
        self.local = local
        self.ldap = ldap
        self.config = config

    def authenticate(self, identifier: str, password: str) -> AuthResult:
        """
        Local auth → LDAP fallback → auto-provision shadow users.
        """

        local_result = self.local.authenticate(identifier, password)

        if local_result.success:
            local_result.auth_source = "local"
            return local_result

        if self.ldap:
            ldap_result = self.ldap.authenticate(identifier, password)

            if ldap_result.success:
                
                roles: list[str] = []
                if self.config.ldap_group_mapping:
                    role_names: set[str] = set()
                    for group in ldap_result.groups:
                        role_names.update(self.config.ldap_group_mapping.get(group, []))
                    roles = list(role_names)

                if local_result.user_id:
                    local_result.success = True
                    local_result.message = "Login Successful."
                    # TODO assign roles even if user already exist to sync with AD
                    return local_result
                
                new_user_id = self.local.create_user(
                    username=ldap_result.username,
                    email=ldap_result.email,
                    auth_source="ldap",
                    password="__ldap__",     # never used
                    first_name=ldap_result.first_name or "",
                    last_name=ldap_result.last_name or "",
                    roles=roles or ["user"],
                    organization="itrust consulting",
                    must_change_pw=0,        # LDAP users never change passwords locally
                    expires_at=None,
                )

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

        return AuthResult.nack()