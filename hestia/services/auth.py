
from hestia.schemas.api import AuthResult
from hestia.services.users import UserService, LDAPService

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
    ):
        self.local = local
        self.ldap = ldap

    def authenticate(self, identifier: str, password: str) -> AuthResult:
        """
        Local auth → LDAP fallback → auto-provision shadow users.
        Always returns a rich AuthResult.
        """

        local_result = self.local.authenticate(identifier, password)

        if local_result.success:
            local_result.auth_source = "local"
            return local_result

        if self.ldap:
            ldap_result = self.ldap.authenticate(identifier, password)

            if ldap_result.success:

                if local_result.user_id:
                    local_result.success = True
                    local_result.message = "Login Successful."
                    return local_result
                
                new_user_id = self.local.create_user(
                    username=ldap_result.username,
                    email=ldap_result.email,
                    auth_source="ldap",
                    password="__ldap__",     # never used
                    first_name=ldap_result.first_name or "",
                    last_name=ldap_result.last_name or "",
                    role="user",
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