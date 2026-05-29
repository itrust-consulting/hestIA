from __future__ import annotations

import hashlib
import json
import secrets
import ssl
import time
import uuid

from ldap3 import ALL, SIMPLE, SUBTREE, Connection, Server, Tls

from hestia.domain.auth.models import AuthResult, CollectionPermission, Permissions, User
from hestia.domain.exceptions import NotFoundError, ValidationError
from hestia.infrastructure.db.user_repository import UserRepository

PBKDF2_ITERATIONS = 210_000
SALT_BYTES = 16


def new_uuid() -> uuid.UUID:
    return uuid.uuid4()


def now_epoch() -> int:
    return int(time.time() * 1000)


class UserService:

    def __init__(self, repo: UserRepository):
        self.repo = repo

    def _generate_salt(self) -> bytes:
        return secrets.token_bytes(SALT_BYTES)

    def _hash_password(self, password: str, salt: bytes) -> bytes:
        return hashlib.pbkdf2_hmac("sha256", password.encode(), salt, PBKDF2_ITERATIONS, dklen=32)

    def _verify_password(self, password: str, salt: bytes, pwd_hash: bytes) -> bool:
        return secrets.compare_digest(pwd_hash, self._hash_password(password, salt))

    # ---- auth ----

    def authenticate(self, identifier: str, password: str) -> AuthResult:
        user = self.repo.get_user_for_login(identifier)
        if not user:
            return AuthResult.nack()

        if user["auth_source"] == "ldap":
            return AuthResult(
                success=False,
                message="LDAP authentication required",
                user_id=uuid.UUID(bytes=user["id"]),
                username=user["username"],
                email=user["email"],
                first_name=user["first_name"],
                last_name=user["last_name"],
                must_change_pw=user["must_change_pw"],
                auth_source="ldap",
            )

        if not self._verify_password(password, user["salt"], user["password_hash"]):
            return AuthResult.nack()

        if user["expires_at"] and user["expires_at"] < now_epoch():
            return AuthResult.nack(message="Account expired")

        return AuthResult(
            success=True,
            message="Login successful.",
            user_id=uuid.UUID(bytes=user["id"]),
            username=user["username"],
            email=user["email"],
            first_name=user["first_name"],
            last_name=user["last_name"],
            must_change_pw=user["must_change_pw"],
            auth_source="local",
        )

    # ---- permissions ----

    def compute_user_permissions(self, user_id: uuid.UUID) -> Permissions:
        # Check admin
        admin_role = self.repo.get_role_by_name("admin")
        user_role_ids = [r["id"] for r in self.repo.get_user_roles(user_id)]
        is_admin = bool(admin_role and admin_role["id"] in user_role_ids)

        # Tenant memberships
        memberships = self.repo.get_user_org_memberships(user_id)
        moderated = [m["org_id"] for m in memberships if m["tenant_role"] in ("moderator", "co-moderator")]
        role_assignable = [m["org_id"] for m in memberships if m["tenant_role"] == "moderator"]

        # Derive allowed_collections from tenant_collections + classification_level per tenant
        allowed: dict[str, CollectionPermission] = {}
        for m in memberships:
            for row in self.repo.get_tenant_collections(m["org_id"]):
                col_id = row["collection_id"]
                user_lvl = m["classification_level"]
                grant_cap = row["max_classification"]
                # Effective level = user's own level, capped by the grant's max_classification if set
                lvl = min(user_lvl, grant_cap) if (grant_cap is not None and user_lvl is not None) else user_lvl
                if col_id not in allowed:
                    allowed[col_id] = CollectionPermission(access=True, max_classification=lvl)
                else:
                    existing = allowed[col_id].max_classification
                    if existing is None or (lvl is not None and lvl > existing):
                        allowed[col_id] = CollectionPermission(access=True, max_classification=lvl)

        return Permissions(
            is_admin=is_admin,
            allowed_collections=allowed,
            moderated_tenants=moderated,
            role_assignable_tenants=role_assignable,
        )

    # ---- profile ----

    def load_user_profile(self, user_id: uuid.UUID) -> User | None:
        row = self.repo.get_user_by_id(user_id)
        if not row:
            return None
        perms = self.compute_user_permissions(user_id)
        return User(
            id=uuid.UUID(bytes=row["id"]),
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

    # ---- admin: users ----

    def list_users(self) -> list[dict]:
        return [
            {
                "id": uuid.UUID(bytes=r["id"]),
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
        roles: list[str] | list[int] = None,
        organization: str | int | None = None,
        must_change_pw: int = 1,
        auth_source: str = "local",
        expires_at: int | None = None,
    ) -> uuid.UUID:
        if roles is None:
            roles = ["user"]
        if len(username) < 3:
            raise ValidationError("Username too short")
        if len(password) < 6:
            raise ValidationError("Password too short")

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
            auth_source=auth_source,
            password_hash=pwd_hash,
            salt=salt,
            must_change_pw=must_change_pw,
            created_ts=ts,
            expires_ts=expires_at,
        )

        for role in roles:
            if isinstance(role, str):
                role_row = self.repo.get_role_by_name(role)
                if not role_row:
                    raise NotFoundError(f"Role '{role}' does not exist")
                role_id = role_row["id"]
            else:
                role_id = role
            self.repo.add_role_to_user(user_id=user_id, role_id=role_id, starts_ts=ts, expires_ts=expires_at)

        if organization is not None:
            if isinstance(organization, str):
                org_row = self.repo.get_organization_by_name(organization)
                if org_row:
                    self.repo.add_user_to_organization(user_id=user_id, org_id=org_row["id"])
            else:
                self.repo.add_user_to_organization(user_id=user_id, org_id=organization)

        return user_id

    def update_user(
        self,
        user_id: uuid.UUID,
        *,
        username: str,
        email: str,
        first_name: str,
        last_name: str,
        expires_at: int | None,
        role_ids: list[int] | None = None,
        new_password: str | None = None,
    ):
        now = now_epoch()
        self.repo.update_user_profile(
            id=user_id, username=username, email=email,
            first_name=first_name, last_name=last_name,
            expires_ts=expires_at, updated_ts=now,
        )
        if role_ids is not None:
            current = {r["id"] for r in self.list_user_roles(user_id)}
            desired = set(role_ids)
            for rid in current - desired:
                self.repo.remove_role_from_user(user_id=user_id, role_id=rid)
            for rid in desired - current:
                self.repo.add_role_to_user(user_id=user_id, role_id=rid, starts_ts=now, expires_ts=None)
        if new_password:
            self.reset_user_password(user_id, new_password)

    def delete_user(self, user_id: uuid.UUID):
        self.repo.delete_user(id=user_id)

    def set_user_expiration(self, user_id: uuid.UUID, expires_at: int):
        self.repo.set_user_expiration(id=user_id, expires_ts=expires_at, updated_ts=now_epoch())

    def reset_user_password(self, user_id: uuid.UUID, temp_password: str):
        salt = self._generate_salt()
        pwd_hash = self._hash_password(temp_password, salt)
        now = now_epoch()
        self.repo.update_user_password(id=user_id, new_hash=pwd_hash, new_salt=salt, updated_ts=now)
        self.repo.set_must_change_pw(change=1, id=user_id, updated_ts=now)

    # ---- admin: roles ----

    def list_roles(self) -> list[dict]:
        return [{"id": r["id"], "name": r["name"], "description": r["description"]}
                for r in self.repo.list_roles()]

    def list_user_roles(self, user_id: uuid.UUID) -> list[dict]:
        return [{"id": r["id"], "name": r["name"]} for r in self.repo.get_user_roles(user_id)]

    # ---- admin: organizations ----

    def list_orgs(self) -> list[dict]:
        orgs = [{"id": r["id"], "name": r["name"], "abbreviation": r["abbreviation"], "created_at": r["created_at"]}
                for r in self.repo.list_organizations()]
        for org in orgs:
            org["member_count"] = len(self.repo.get_organization_users(org["id"]))
        return orgs

    def create_org(self, name: str, abbreviation: str):
        self.repo.insert_organization(name=name, abbreviation=abbreviation, created_ts=now_epoch())

    def update_org(self, org_id: int, name: str, abbreviation: str):
        self.repo.update_organization(id=org_id, name=name, abbreviation=abbreviation)

    def delete_org(self, org_id: int):
        self.repo.delete_organization(id=org_id)

    def add_user_to_org(self, user_id: uuid.UUID, org_id: int):
        self.repo.add_user_to_organization(user_id=user_id, org_id=org_id)

    def remove_user_from_org(self, user_id: uuid.UUID, org_id: int):
        self.repo.remove_user_from_organization(user_id=user_id, org_id=org_id)

    def list_user_organizations(self, user_id: uuid.UUID) -> list[dict]:
        return [{"id": o["id"], "name": o["name"], "abbr": o["abbreviation"], "created_at": o["created_at"]}
                for o in self.repo.get_user_organizations(user_id)]

    def get_org_users(self, org_id: int) -> list[dict]:
        return [
            {
                "id": str(uuid.UUID(bytes=r["id"])),
                "username": r["username"],
                "email": r["email"],
                "first_name": r["first_name"],
                "last_name": r["last_name"],
                "classification_level": r["classification_level"],
                "tenant_role": r["tenant_role"],
            }
            for r in self.repo.get_organization_users(org_id)
        ]

    # ---- admin: tenant membership management ----

    def set_member_classification(self, user_id: uuid.UUID, org_id: int, level: int):
        self.repo.set_member_classification(user_id=user_id, org_id=org_id, level=level)

    def set_member_tenant_role(self, user_id: uuid.UUID, org_id: int, role: str | None):
        # Enforce one-moderator-per-tenant constraint
        if role == "moderator":
            existing = self.repo.get_org_tenant_moderator(org_id)
            if existing and bytes(existing["user_id"]) != user_id.bytes:
                raise ValidationError("Tenant already has a moderator.")
        self.repo.set_member_tenant_role(user_id=user_id, org_id=org_id, role=role)

    def get_tenant_collection_info(self, org_id: int) -> dict:
        rows = self.repo.get_tenant_collections(org_id)
        owned = []
        accessible = []
        for r in rows:
            col_id = r["collection_id"]
            if r["role"] == "owner":
                access_tenants = self.repo.get_collection_access_tenants(col_id)
                owned.append({
                    "id": col_id,
                    "access": [
                        {"id": t["id"], "name": t["name"], "abbreviation": t["abbreviation"],
                         "max_classification": t["max_classification"]}
                        for t in access_tenants
                    ],
                })
            else:
                owner = self.repo.get_collection_owner(col_id)
                accessible.append({
                    "id": col_id,
                    "owner": {"id": owner["id"], "name": owner["name"], "abbreviation": owner["abbreviation"]}
                             if owner else None,
                })
        return {"owned": owned, "accessible": accessible}

    def get_collection_grants(self, collection_id: str) -> dict:
        """Return SQL-persisted owner and access tenants for a collection."""
        owner = self.repo.get_collection_owner(collection_id)
        access = self.repo.get_collection_access_tenants(collection_id)
        return {
            "owner": {"id": owner["id"], "name": owner["name"], "abbreviation": owner["abbreviation"]} if owner else None,
            "access": [{"id": t["id"], "name": t["name"], "abbreviation": t["abbreviation"],
                        "max_classification": t["max_classification"]} for t in access],
        }

    def add_tenant_collection(self, org_id: int, collection_id: str, role: str = "access",
                              max_classification: int | None = None):
        self.repo.add_tenant_collection(org_id=org_id, collection_id=collection_id, role=role,
                                        max_classification=max_classification)

    def remove_tenant_collection(self, org_id: int, collection_id: str):
        self.repo.remove_tenant_collection(org_id=org_id, collection_id=collection_id)

    def remove_collection_grants(self, collection_id: str):
        self.repo.remove_collection_grants(collection_id=collection_id)

    # ---- self-service ----

    def change_password(self, user_id: uuid.UUID, current_pw: str, new_pw: str) -> tuple[bool, str]:
        row = self.repo.get_user_by_id(user_id)
        if not row:
            return False, "Invalid user."
        if row["auth_source"] == "ldap":
            return False, "LDAP account — password cannot be changed here."
        if not self._verify_password(current_pw, row["salt"], row["password_hash"]):
            return False, "Incorrect current password."
        if len(new_pw) < 6:
            raise ValidationError("New password must be at least 6 characters.")
        new_salt = self._generate_salt()
        new_hash = self._hash_password(new_pw, new_salt)
        now = now_epoch()
        self.repo.update_user_password(id=user_id, new_hash=new_hash, new_salt=new_salt, updated_ts=now)
        self.repo.set_must_change_pw(change=0, id=user_id, updated_ts=now)
        return True, "Password successfully changed."

    def change_username(self, user_id: uuid.UUID, new_name: str):
        if len(new_name) < 3:
            raise ValidationError("Username too short.")
        self.repo.update_username(id=user_id, new_username=new_name, updated_ts=now_epoch())

    def change_email(self, user_id: uuid.UUID, new_email: str):
        if "@" not in new_email:
            raise ValidationError("Invalid email.")
        self.repo.update_user_email(id=user_id, new_email=new_email, updated_ts=now_epoch())

    def deactivate_user_account(self, user_id: uuid.UUID):
        self.repo.set_user_expiration(id=user_id, expires_ts=now_epoch(), updated_ts=now_epoch())

    # ---- conversations ----

    def get_user_conversations(self, user_id: uuid.UUID) -> list[dict]:
        return [
            {
                "id": uuid.UUID(bytes=c["id"]),
                "title": c["title"],
                "metadata": c["metadata_json"],
                "created_at": c["created_at"],
                "updated_at": c["updated_at"],
            }
            for c in self.repo.get_conversation(user_id, limit=20, offset=0)
        ]

    def get_conversation_messages(self, c_id: uuid.UUID) -> list[dict]:
        rows = self.repo.get_messages(c_id, limit=100)
        return [
            {
                "id": uuid.UUID(bytes=m["id"]),
                "role": m["role"],
                "metadata": m["metadata"],
                "content": m["content"],
                "options": m["options"],
                "created_at": m["created_at"],
            }
            for m in reversed(rows)
        ]

    def append_conversation_message(
        self,
        c_id: uuid.UUID,
        role: str,
        content: str,
        metadata: dict | None = None,
        options: dict | None = None,
        ts: int | None = None,
    ) -> uuid.UUID:
        msg_id = new_uuid()
        now = ts if ts is not None else now_epoch()
        self.repo.insert_message(
            msg_id=msg_id,
            c_id=c_id,
            role=role,
            metadata=json.dumps(metadata or {}),
            content=content,
            options=json.dumps(options or {}),
            ts=now,
        )
        self.repo.update_conversation_updated_at(c_id=c_id, ts=now)
        return msg_id

    def create_user_conversation(self, user_id: uuid.UUID, title: str) -> uuid.UUID:
        conv_id = new_uuid()
        now = now_epoch()
        self.repo.insert_conversation(conv_id=conv_id, user_id=user_id, title=title, metadata_json="{}", ts=now)
        return conv_id

    def rename_user_conversation(self, user_id: uuid.UUID, c_id: uuid.UUID, title: str):
        self.repo.update_conversation_title(user_id=user_id, c_id=c_id, title=title)

    def delete_user_conversation(self, user_id: uuid.UUID, c_id: uuid.UUID):
        self.repo.delete_conversation(user_id=user_id, c_id=c_id)

    def delete_conversation_message(self, user_id: uuid.UUID, c_id: uuid.UUID, msg_id: uuid.UUID):
        self.repo.delete_message(c_id=c_id, msg_id=msg_id)


class LDAPService:

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
        mode: str = "auto",
    ):
        self.host = host
        self.port = port
        self.search_base = search_base
        self.user_attribute = user_attribute
        self.mail_attribute = mail_attribute
        self.user_dn_template = user_dn_template
        self.allowed_groups = allowed_groups
        self.bind_dn = bind_dn
        self.bind_password = bind_password
        self.mode = mode.lower()
        self.use_ssl = use_ssl
        self.tls = Tls(validate=ssl.CERT_REQUIRED if validate_cert else ssl.CERT_NONE) if use_ssl else None

    def _server(self):
        return Server(self.host, port=self.port, use_ssl=self.use_ssl, tls=self.tls, get_info=ALL)

    def _service_bind(self) -> Connection | None:
        if not (self.bind_dn and self.bind_password):
            return None
        try:
            return Connection(self._server(), user=self.bind_dn, password=self.bind_password,
                              authentication=SIMPLE, auto_bind=True)
        except Exception:
            return None

    def _search_user(self, conn: Connection, identifier: str) -> tuple[str | None, dict | None]:
        for filt in [f"({self.user_attribute}={identifier})", f"({self.mail_attribute}={identifier})"]:
            try:
                conn.search(search_base=self.search_base, search_filter=filt,
                            search_scope=SUBTREE, attributes=["uid", "sAMAccountName", "mail", "givenName", "sn", "memberOf"])
            except Exception:
                continue
            if conn.entries:
                entry = conn.entries[0]
                return entry.entry_dn, entry.entry_attributes_as_dict
        return None, None

    def _build_direct_dn(self, identifier: str) -> str:
        if self.user_dn_template:
            return self.user_dn_template.format(username=identifier)
        return f"{self.user_attribute}={identifier},{self.search_base}"

    def _lookup_user_dn(self, identifier: str) -> tuple[str, dict | None]:
        svc = self._service_bind()
        if svc:
            dn, attrs = self._search_user(svc, identifier)
            if dn:
                return dn, attrs
        return self._build_direct_dn(identifier), None

    def _bind_user(self, dn: str, password: str) -> bool:
        try:
            Connection(self._server(), user=dn, password=password, authentication=SIMPLE, auto_bind=True)
            return True
        except Exception:
            return False

    def _normalize_ldap_groups(self, member_of: list[str]) -> set[str]:
        groups: set[str] = set()
        for dn in member_of:
            if dn.lower().startswith("cn="):
                groups.add(dn.split(",", 1)[0][3:].lower())
        return groups

    def authenticate(self, identifier: str, password: str) -> AuthResult:
        user_dn, attrs = self._lookup_user_dn(identifier)
        if not self._bind_user(user_dn, password):
            return AuthResult.nack()

        if attrs is None:
            try:
                conn = Connection(self._server(), auto_bind=True)
                conn.search(
                    search_base=self.search_base,
                    search_filter=f"(|({self.user_attribute}={identifier})({self.mail_attribute}={identifier}))",
                    search_scope=SUBTREE,
                    attributes=["uid", "mail", "givenName", "sn", "memberOf"],
                )
                if conn.entries:
                    attrs = conn.entries[0].entry_attributes_as_dict
            except Exception:
                pass
            attrs = attrs or {}

        groups = self._normalize_ldap_groups(attrs.get("memberOf") or [])
        if self.allowed_groups is not None:
            groups &= self.allowed_groups

        return AuthResult(
            success=True,
            message="Login successful.",
            username=(attrs.get("uid") or attrs.get("sAMAccountName") or [None])[0],
            email=(attrs.get("mail") or [None])[0],
            first_name=(attrs.get("givenName") or [None])[0],
            last_name=(attrs.get("sn") or [None])[0],
            groups=list(groups),
        )
