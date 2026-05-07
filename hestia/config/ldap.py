# hestia/config/ldap.py

from pydantic import BaseModel
import os

class LDAPConfig(BaseModel):
    host: str
    port: int
    search_base: str
    user_attribute: str
    mail_attribute: str
    use_ssl: bool
    validate_cert: bool
    bind_dn: str | None 
    bind_password: str | None
    user_dn_template: str | None
    allowed_groups: set[str] | None
    mode: str 

def parse_set(value: str | None) -> set[str] | None:
    if not value:
        return None
    return {v.strip().lower() for v in value.split(",") if v.strip()}

def load_ldap_config() -> LDAPConfig:
    return LDAPConfig(
        host=os.getenv(["LDAP_HOST"]),
        port=int(os.getenv("LDAP_PORT", "636")),
        search_base=os.getenv["LDAP_SEARCH_BASE"],
        user_attribute=os.getenv("LDAP_USER_ATTR", "uid"),
        mail_attribute=os.getenv("LDAP_MAIL_ATTR", "mail"),
        user_dn_template=os.getenv("LDAP_USER_DN_TEMPLATE", ""),
        allowed_groups=parse_set(os.getenv("LDAP_ALLOWED_GROUPS")),
        bind_dn=os.getenv("LDAP_APP_DN", ""),
        bind_password=os.getenv("LDAP_APP_PASSWORD", ""),
        use_ssl=os.getenv("LDAP_USE_SSL", "true").lower() == "true",
        validate_cert=os.getenv("LDAP_VALIDATE_CERT", "true").lower() == "true",
        mode=os.getenv("LDAP_MODE", "auto"),
    )