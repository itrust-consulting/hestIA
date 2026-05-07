from pydantic import BaseModel
import os
import json

class AuthConfig(BaseModel):
    enable_ldap: bool
    ldap_group_mapping: dict[str, list[str]] | None
    # pw login settings
    password_min_length: int
    max_failed_attempts: int
    lockout_duration_minutes: int
    # token settings
    token_secret_key: str
    token_encoding_alg: str
    token_lifetime_minutes: int
    
    audit_logs: bool

def parse_ldap_group_mapping(raw: str | None) -> dict[str, list[str]] | None:
    if not raw:
        return None

    try:
        data = json.loads(raw)
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid LDAP_GROUP_MAPPING JSON: {e}")

    if not isinstance(data, dict):
        raise ValueError("LDAP_GROUP_MAPPING must be a JSON object")

    parsed: dict[str, list[str]] = {}

    for group, roles in data.items():
        if not isinstance(group, str):
            raise ValueError("LDAP group names must be strings")
        if not isinstance(roles, list) or not all(isinstance(r, str) for r in roles):
            raise ValueError(f"Roles for group '{group}' must be a list of strings")

        parsed[group.lower()] = roles

    return parsed

def load_auth_config() -> AuthConfig:
    return AuthConfig(
        enable_ldap=os.getenv("ENABLE_LDAP", "false").lower() == "true",
        ldap_group_mapping=parse_ldap_group_mapping(os.getenv("LDAP_GROUP_MAPPING")),
        password_min_length=int(os.getenv("AUTH_PW_LENGTH", "15")),
        max_failed_attempts=int(os.getenv("AUTH_MAX_ATTEMPTS", "5")),
        lockout_duration_minutes=int(os.getenv("AUTH_LOCKOUT_DURATION", "5")),
        token_secret_key=os.getenv("AUTH_SECRET_KEY"),
        token_encoding_alg=os.getenv("AUTH_ENCODIGN_ALGORITHM", "HS256"),
        token_lifetime_minutes=int(os.getenv("AUTH_TOKEN_LIFETIME", "360")),
        audit_logs=os.getenv("AUTH_AUDIT_LOGS", "false").lower() == "true"
    )