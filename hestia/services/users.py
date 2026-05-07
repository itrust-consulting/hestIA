import secrets
import hashlib
import uuid
import time
import json
import ssl
from ldap3 import Server, Connection, ALL, SIMPLE, SUBTREE, Tls

from hestia.schemas.api import User, AuthResult
from hestia.utils.user_db import UserRepository

"""
TODO:
- output type annotations.
- proper input validations.
- setters shall return ack/nack - msg
"""

PBKDF2_ITERATIONS = 210_000
SALT_BYTES = 16

def new_uuid() -> uuid.UUID:
    return uuid.uuid4().bytes 

def now_epoch() -> int:
    return int(time.time() * 1000) #ms precision


class PermissionResolver:
    """
    Computes effective permissions for a user:
      - Role inheritance
      - Role permissions (child overrides parent)
      - User-specific overrides (override role)
      - Time-window filtering
    """

    def __init__(self, repo: UserRepository):
        self.repo = repo

    def _parse_value(self, value: str | None):
        if value is None:
            return None

        # bool
        if value.lower() == "true":
            return True
        if value.lower() == "false":
            return False

        # int
        try:
            return int(value)
        except:
            pass

        # JSON object or list
        try:
            return json.loads(value)
        except:
            pass

        # fallback string
        return value

    def _time_valid(self, starts: int, expires: int | None) -> bool:
        now = now_epoch()
        if starts is not None and now < starts:
            return False
        if expires is not None and now > expires:
            return False
        return True

    def _collect_role_tree(self, role_id: int, visited: set[int]):
        """DFS: return role + all ancestor roles."""
        if role_id in visited:
            return []

        visited.add(role_id)
        chain = [role_id]

        parents = self.repo.get_parent_roles(role_id)
        for row in parents:
            chain.extend(self._collect_role_tree(row["parent_id"], visited))

        return chain

    def _resolve_roles(self, role_ids: list[int]) -> list[int]:
        visited = set()
        ordered = []
        for rid in role_ids:
            ordered.extend(self._collect_role_tree(rid, visited))
        return ordered

    def _merge_map_permission(self, base: dict, incoming: dict) -> dict:
        """
        Merge map permissions without overwriting existing keys.
        Child role keys override parent keys.
        """
        result = dict(base)

        for key, value in incoming.items():
            # value is expected to be an object like:
            # { "access": bool, "max_classification": int | None }
            result[key] = value

        return result

    def compute_user_permissions(self, user_id: bytes) -> dict:
        effective: dict = {}

        role_rows = self.repo.get_user_roles(user_id)
        direct_role_ids = [
            r["id"]
            for r in role_rows
            if self._time_valid(r["starts_at"], r["expires_at"])
        ]

        resolved_roles = self._resolve_roles(direct_role_ids)

        for rid in resolved_roles:
            for rp in self.repo.get_role_permissions(rid):
                perm_name = rp["name"]
                perm_value = self._parse_value(rp["value"])

                perm_def = self.repo.get_permission_by_name(perm_name)
                value_type = perm_def["value_type"]

                if value_type == "map":
                    existing = effective.get(perm_name, {})
                    if not isinstance(existing, dict):
                        existing = {}

                    if isinstance(perm_value, dict):
                        effective[perm_name] = self._merge_map_permission(
                            existing,
                            perm_value
                        )
                    else:
                        effective[perm_name] = existing
                else:
                    effective[perm_name] = perm_value

        for up in self.repo.get_user_permissions(user_id):
            if not self._time_valid(up["starts_at"], up["expires_at"]):
                continue

            perm_name = up["name"]
            perm_value = self._parse_value(up["value"])

            effective[perm_name] = perm_value

        return effective


class UserService:

    def __init__(self, repo: UserRepository):
        self.repo = repo
        self.permissions = PermissionResolver(repo)

    # --------------------------------------
    # Helpers
    # --------------------------------------
    def _generate_salt(self):
        return secrets.token_bytes(SALT_BYTES)

    def _hash_password(self, password: str, salt: bytes):
        return hashlib.pbkdf2_hmac(
            "sha256", password.encode(), salt, PBKDF2_ITERATIONS, dklen=32
        )

    def _verify_password(self, password: str, salt: bytes, pwd_hash: bytes):
        return secrets.compare_digest(
            pwd_hash, 
            self._hash_password(password, salt)
        )
    
    def _serialize_permission_value(self, value) -> str:
        """
        Convert a permission value into a DB-safe string.
        """
        if isinstance(value, bool):
            return "true" if value else "false"

        if isinstance(value, (dict, list)):
            return json.dumps(value, separators=(",", ":"))

        if value is None:
            return "null"

        return str(value)

    # --------------------------------------
    # Auth
    # --------------------------------------
    def authenticate(self, identifier: str, password: str) -> AuthResult:
        
        user = self.repo.get_user_for_login(identifier)
        if not user:
            return AuthResult.nack()
        
        if user["auth_source"] == "ldap":
            fwd_auth = AuthResult(
                    success=False,
                    message="LDAP authentication required",
                    user_id=user["id"],
                    username=user["username"],
                    email=user["email"],
                    first_name=user["first_name"],
                    last_name=user["last_name"],
                    must_change_pw=user["must_change_pw"],
                    auth_source="ldap",
                )
            return fwd_auth

        if not self._verify_password(password, user["salt"], user["password_hash"]):
            return AuthResult.nack()

        if user["expires_at"] and user["expires_at"] < now_epoch():
            return AuthResult.nack(message="Account expired")
        
        # row["id"] returns bytes, must convert to string
        result = AuthResult(
            success=True,
            message="Login successful.",
            user_id=user["id"],
            username=user["username"],
            email=user["email"],
            first_name=user["first_name"],
            last_name=user["last_name"],
            must_change_pw=user["must_change_pw"],
            auth_source="local",
        )
        return result


    # --------------------------------------
    # Admin: Users
    # --------------------------------------
    def list_users(self):
        return [
            {
                "id": r["id"].hex(),
                "username": r["username"],
                "email": r["email"],
                "first_name": r["first_name"],
                "last_name": r["last_name"],
                "auth_source": r["auth_source"],
                "must_change_pw": r["must_change_pw"],
                "created_at": r["created_at"],
                "updated_at": r["updated_at"],
                "expires_at": r["expires_at"],
            }
            for r in self.repo.list_users()
        ]

    def create_user(
            self, 
            *,
            username: str, 
            email: str, 
            password: str,
            first_name: str, 
            last_name: str,
            roles: list[str] | list[int] = ["guest"],
            organization: str | int | None = None,
            must_change_pw: int = 1,        # default requires user to change pw upon first login.
            auth_source: str = "local",
            expires_at: int | None = None,
            permissions: dict | None = None):

        if len(username) < 3:
            raise ValueError("Username too short")

        if len(password) < 6:
            raise ValueError("Password too short")

        user_id = new_uuid()
        salt = self._generate_salt()
        pwd_hash = self._hash_password(password, salt)
        ts = now_epoch()

        self.repo.insert_user(
            user_id=user_id,
            username=username,
            email=email,
            first_name=first_name,
            last_name=last_name,
            auth_source=auth_source,        # always 'local' user must be created
            password_hash=pwd_hash,
            salt=salt,
            must_change_pw=must_change_pw,
            created_ts=ts,
            expires_ts=expires_at,
        )

        # Assign role
        for role in roles:
            role_id = role
            if isinstance(role, str):
                role_row = self.repo.get_role_by_name(role)
                if not role_row:
                    raise ValueError(f"Role '{role}' does not exist")
                role_id = role_row["id"]

            self.repo.add_role_to_user(
                user_id=user_id,
                role_id=role_id,
                starts_ts=ts,
                expires_ts=expires_at,
            )
        # assign org
        org_id = organization
        if isinstance(organization, str):
            org_row = self.repo.get_organization_by_name(organization)
            if not org_row:
                raise ValueError(f"Organization '{organization}' does not exist")
            org_id = org_row["id"]
        
        self.repo.add_user_to_organization(
            user_id=user_id,
            org_id=org_id
        )
        
        if permissions:
            # Fetch permission definitions once
            perm_defs = {
                p["name"]: p["id"]
                for p in self.repo.list_permissions()
            }

            for perm_name, perm_value in permissions.items():
                if perm_name not in perm_defs:
                    raise ValueError(f"Unknown permission '{perm_name}'")

                permission_row = self.repo.get_permission_by_name(perm_name)
                pid = permission_row["id"]
                value_str = self._serialize_permission_value(perm_value)

                self.set_user_permission(
                    user_id=user_id,
                    permission_id=pid,
                    value=value_str,
                    starts_ts=ts,
                    expires_ts=expires_at,
                )

        return user_id

    def delete_user(self, user_id: bytes):
        self.repo.delete_user(id=user_id)

    def set_user_expiration(self, user_id: bytes, expires_at: int):
        self.repo.set_user_expiration(id=user_id, expires_ts=expires_at, updated_ts=now_epoch())

    def reset_user_password(self, user_id: bytes, temp_password: str):
        salt = self._generate_salt()
        pwd_hash = self._hash_password(temp_password, salt)
        now = now_epoch()

        self.repo.update_user_password(id=user_id, new_hash=pwd_hash, new_salt=salt, updated_ts=now)
        self.repo.set_must_change_pw(change=1, id=user_id, updated_ts=now)

    # --------------------------------------
    # Admin: Roles & Permissions
    # --------------------------------------
    def list_roles(self) -> list[dict]:
        rows = self.repo.list_roles()
        return [
            {
                "id": r["id"],
                "name": r["name"],
                "description": r["description"],
            }
            for r in rows
        ]
    
    def list_permissions(self) -> list[dict]:
        perm_rows = self.repo.list_permissions()
        return [{
            "id": p["id"],
            "name": p["name"],
            "description": p["description"],
            "value_type": p["value_type"],
            "options": p["options"]
            }
            for p in perm_rows
        ]
    
    def create_permission(self, name: str, description: str, value_type: str):        
        self.repo.insert_permission(name=name, description=description, value_type=value_type)

    def assign_role_to_user(
            self, 
            user_id: bytes, 
            role_id: int, 
            starts_at: int | None = None, 
            expires_at: int | None = None):
        self.repo.add_role_to_user(
            user_id=user_id,
            role_id=role_id,
            starts_ts=starts_at or now_epoch(),
            expires_ts=expires_at,
        )

    def assign_multiple_roles_to_user(
            self,
            user_id: bytes,
            role_ids: list[int],
            starts_at: int | None = None,
            expires_at: int | None = None,
    ):
        for rid in role_ids:
            self.assign_role_to_user(
                user_id=user_id,
                role_id=rid,
                starts_at=starts_at,
                expires_at=expires_at
            )

    def revoke_role_from_user(self, user_id: bytes, role_id: int):
        self.repo.remove_role_from_user(user_id=user_id, role_id=role_id)

    def list_user_roles(self, user_id: bytes):
        return [
            {"id": r["id"], "name": r["name"]}
            for r in self.repo.get_user_roles(user_id)
        ]

    def list_role_permissions(self, role_id: int):
        return [
            {"id": p["id"], "name": p["name"], "value": p["value"]}
            for p in self.repo.get_role_permissions(role_id)
        ]

    def set_user_permission(self, user_id: bytes, permission_id: int, value: str, starts_ts: int, expires_ts: int):
        """Only sets user-specific permission rights that override user's role permissions."""
        self.repo.set_user_permission(
            user_id=user_id,
            permission_id=permission_id,
            value=value,
            starts_ts=starts_ts,
            expires_ts=expires_ts,
        )

    def list_user_permission(self, user_id: bytes):
        """only list user-specific permissions, ignoring default role permissions."""
        perm_rows = self.repo.get_user_permissions(user_id)
        return [{
            "id": p["id"],
            "name": p["name"],
            "value": p["value"],
            "starts_at": p["starts_at"],
            "expires_at": p["expires_at"]
            }
            for p in perm_rows
        ]
    

    # org mgmt
    def list_orgs(self) -> list[dict]:
        rows = self.repo.list_organizations()
        return [
            {
                "id": r["id"],
                "name": r["name"],
                "abbreviation": r["abbreviation"],
                "created_at": r["created_at"]
            }
            for r in rows
        ]

    def list_org_users(self, org_id: int) -> list[dict]:
        rows = self.repo.get_organization_users(org_id)
        return [
            {
                "id": r["id"].hex(),
                "username": r["username"],
                "email": r["email"],
                "first_name": r["first_name"],
                "last_name": r["last_name"]
            }
            for r in rows
        ]

    def create_org(self, name: str, abbreviation: str):
        self.repo.insert_organization(name=name, abbreviation=abbreviation, created_ts=now_epoch())

    def update_org(self, org_id: int, name: str, abbreviation: str):
        self.repo.update_organization(id=org_id, name=name, abbreviation=abbreviation)

    def delete_org(self, org_id: int):
        self.repo.delete_organization(org_id=org_id)

    def add_user_to_org(self, user_id: bytes, org_id: int):
        self.repo.add_user_to_organization(user_id=user_id, org_id=org_id)

    def remove_user_from_org(self, user_id: bytes, org_id: int):
        self.repo.remove_user_from_organization(user_id=user_id, org_id=org_id)

    def list_user_organizations(self, user_id: bytes):
        org_rows = self.repo.get_user_organizations(user_id)
        return [{
            "id": o["id"],
            "name": o["name"],
            "abbr": o["abbreviation"],
            }
            for o in org_rows
        ]
  
    def load_user_profile(self, user_id: bytes):
        row = self.repo.get_user_by_id(user_id)
        if not row:
            return None

        perms = self.permissions.compute_user_permissions(user_id)
        return User(
            id=row["id"].hex(),
            username=row["username"],
            email=row["email"],
            first_name=row["first_name"],
            last_name=row["last_name"],
            roles=self.list_user_roles(user_id),
            orgs=self.list_user_organizations(user_id),
            permissions=perms,
            must_change_pw=bool(row["must_change_pw"]),
            auth_source=row["auth_source"],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
            expires_at=row["expires_at"],
        )
    # --------------------------------------
    # Self-services
    # --------------------------------------
    def change_password(self, user_id: bytes, current_pw: str, new_pw: str):
        row = self.repo.get_user_by_id(user_id)
        if not row:
            return False, "Invalid user."
        
        if row["auth_source"] == "ldap":
            return False, "Logged in with LDAP account. Password cannot be changed."
        
        if not self._verify_password(current_pw, row["salt"], row["password_hash"]):
            return False, "Incorrect current password."

        if len(new_pw) < 6:
            raise ValueError("New password must be at least 6 characters.")

        new_salt = self._generate_salt()
        new_hash = self._hash_password(new_pw, new_salt)

        self.repo.update_user_password(
            id=user_id,
            new_hash=new_hash,
            new_salt=new_salt,
            updated_ts=now_epoch(),
        )
        self.repo.set_must_change_pw(change=0, id=user_id, updated_ts=now_epoch())
        return True, "Password successfully changed."
    
    def change_username(self, user_id: bytes, new_name: str):
        if len(new_name) < 3:
            raise ValueError("Username too short.")
        self.repo.update_username(id=user_id, new_username=new_name, updated_ts=now_epoch())

    def change_email(self, user_id: bytes, new_email: str):
        if "@" not in new_email:
            raise ValueError("Invalid email.")
        self.repo.update_user_email(id=user_id, new_email=new_email, updated_ts=now_epoch())

    def change_first_name(self, user_id: bytes, new_name: str):
        self.repo.update_user_first_name(id=user_id, new_name=new_name, updated_ts=now_epoch())

    def change_last_name(self, user_id: bytes, new_name: str):
        self.repo.update_user_last_name(id=user_id, new_name=new_name, updated_ts=now_epoch())

    def deactivate_user_account(self, user_id: bytes):
        self.repo.set_user_expiration(id=user_id, expires_ts=now_epoch(), updated_ts=now_epoch())


    def get_user_conversations(self, user_id: bytes):
        conversations = self.repo.get_conversation(user_id, limit=20, offset=0)
        return [{
            "id": conversation["id"].hex(),
            "title": conversation["title"],
            "metadata": conversation["metadata_json"],
            "created_at": conversation["created_at"],
            "updated_at": conversation["updated_at"]
        } for conversation in conversations]

    def get_conversation_messages(self, c_id: bytes):
        messages = self.repo.get_messages(c_id, limit=100)
        return [{
            "id": message["id"].hex(),
            "role": message["role"],
            "metadata": message["metadata"],
            "content": message["content"],
            "options": message["options"],
            "created_at": message["created_at"]
        } for message in reversed(messages)]

    def append_conversation_message(self, 
                                    c_id: bytes,
                                    role: str, 
                                    content: str, 
                                    metadata: dict | None = None, 
                                    options: dict | None = None):
        msg_id = new_uuid()
        now = now_epoch()

        self.repo.insert_message(
            msg_id=msg_id,
            c_id=c_id,
            role=role,
            metadata=json.dumps(metadata or {}),
            content=content,
            options=json.dumps(options or {}),
            ts=now
        )

        self.repo.update_conversation_updated_at(c_id=c_id, ts = now)
        return msg_id

    def delete_conversation_message(self, user_id: bytes, c_id: bytes, msg_id: bytes):
        # implement checks, for now just pass
        self.repo.delete_message(c_id=c_id, msg_id=msg_id)

    def create_user_conversation(self, user_id: bytes, title: str):
        conv_id = new_uuid()
        now = now_epoch()
        self.repo.insert_conversation(
            conv_id=conv_id, 
            user_id=user_id, 
            title=title,
            metadata_json="{}", 
            ts=now)
        return conv_id

    def rename_user_conversation(self, user_id: bytes, c_id: bytes,  title: str):
        self.repo.update_conversation_title(user_id=user_id, c_id=c_id, title=title)

    def delete_user_conversation(self, user_id: bytes, c_id: bytes):
        self.repo.delete_conversation(user_id=user_id, c_id=c_id)
    
    
class LDAPService:
    """
    Universal LDAP authentication service supporting:
      - Active Directory (service-bind → search → user-bind)
      - OpenLDAP (direct DN bind or service-bind lookup)
      - FreeIPA / 389 Directory Server
      - Samba AD
      - Generic LDAP servers
    """

    def __init__(
        self,
        host: str,
        search_base: str,
        user_attribute: str = "uid",
        mail_attribute: str = "mail",
        port: int = 636,
        bind_dn: str | None = None,
        bind_password: str | None = None,
        user_dn_template: str | None = None,
        allowed_groups: set[str] | None = None,
        use_ssl: bool = True,
        validate_cert: bool = True,
        mode: str = "auto",     # "auto" | "ad" | "openldap"
    ):
        self.host = host
        self.port = port
        self.search_base = search_base
        self.user_attribute = user_attribute    # e.g., "sAMAccountName" or "uid"
        self.mail_attribute = mail_attribute
        self.user_dn_template = user_dn_template
        self.allowed_groups = allowed_groups
        self.bind_dn = bind_dn
        self.bind_password = bind_password
        self.mode = mode.lower()
        self.use_ssl = use_ssl

        self.tls = None
        if use_ssl:
            self.tls = Tls(
                validate=ssl.CERT_REQUIRED if validate_cert else ssl.CERT_NONE
            )

    def _server(self):
        return Server(
            self.host,
            port=self.port,
            use_ssl=self.use_ssl,
            tls=self.tls,
            get_info=ALL,
        )

    def _service_bind(self):
        """Service bind, only used if credentials exist."""
        if not (self.bind_dn and self.bind_password):
            return None
        try:
            return Connection(
                self._server(),
                user=self.bind_dn,
                password=self.bind_password,
                authentication=SIMPLE,
                auto_bind=True,
            )
        except Exception:
            return None

    def _search_user(self, conn, identifier: str):
        """Search user via attribute or email."""
        filters = [
            f"({self.user_attribute}={identifier})",
            f"({self.mail_attribute}={identifier})",
        ]

        for filt in filters:
            try:
                conn.search(
                    search_base=self.search_base,
                    search_filter=filt,
                    search_scope=SUBTREE,
                    attributes=["uid", "sAMAccountName", "mail",
                                "givenName", "sn", "memberOf"],
                )
            except Exception:
                continue

            if conn.entries:
                entry = conn.entries[0]
                return entry.entry_dn, entry.entry_attributes_as_dict

        return None, None

    def _build_direct_dn(self, identifier: str):
        if self.user_dn_template:
            return self.user_dn_template.format(username=identifier)
        return f"{self.user_attribute}={identifier},{self.search_base}"

    def _lookup_user_dn(self, identifier: str):
        """
        Returns DN and attributes (if found), using:
          - AD/IPA: service-bind + search
          - OpenLDAP fallback: DN template
        """
        svc = self._service_bind()
        if svc:
            dn, attrs = self._search_user(svc, identifier)
            if dn:
                return dn, attrs

        # Template fallback
        return self._build_direct_dn(identifier), None

    def _bind_user(self, dn: str, password: str) -> bool:
        """Attempt to bind as user."""
        try:
            Connection(
                self._server(),
                user=dn,
                password=password,
                authentication=SIMPLE,
                auto_bind=True,
            )
            return True
        except Exception:
            return False

    def _fetch_user_attributes(self, identifier: str):
        """After binding, resolve complete attributes."""
        try:
            conn = Connection(self._server(), auto_bind=True)
            conn.search(
                search_base=self.search_base,
                search_filter=f"(|({self.user_attribute}={identifier})"
                              f"({self.mail_attribute}={identifier}))",
                search_scope=SUBTREE,
                attributes=["uid", "mail", "givenName", "sn", "memberOf"],
            )
            if conn.entries:
                return conn.entries[0].entry_attributes_as_dict
        except Exception:
            pass
        return None

    def _normalize_ldap_groups(self, member_of: list[str]) -> set[str]:
        groups = set()
        for dn in member_of:
            if dn.lower().startswith("cn="):
                cn = dn.split(",", 1)[0][3:]
                groups.add(cn.lower())
        return groups
    
    def _filter_groups(self, groups: set[str]) -> set[str]:
        if self.allowed_groups is None:
            return groups
        return groups & self.allowed_groups
    
    def authenticate(self, identifier: str, password: str) -> AuthResult:
        """
        Authenticate user and return normalized attributes.
        """
        # Determine user DN
        user_dn, attrs = self._lookup_user_dn(identifier)

        # Bind with that DN
        if not self._bind_user(user_dn, password):
            return AuthResult.nack()
        
        # Fetch attributes (unless AD search already gave us some)
        if attrs is None:
            attrs = self._fetch_user_attributes(identifier) or {}

        groups = self._normalize_ldap_groups(attrs.get("memberOf") or [])
        groups = self._filter_groups(groups)

        # Normalize output
        return AuthResult(
            success=True,
            message="Login successful.",
            username=(attrs.get("uid") or attrs.get("sAMAccountName") or [None])[0],
            email=(attrs.get("mail") or [None])[0],
            first_name=(attrs.get("givenName") or [None])[0],
            last_name=(attrs.get("sn") or [None])[0],
            groups = groups
        )