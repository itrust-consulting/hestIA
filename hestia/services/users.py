import secrets
import hashlib
from typing import Optional
import uuid
import time
import json

from hestia.schemas.api import Permissions, User
from hestia.utils.user_db import UserRepository


def new_uuid() -> uuid.UUID:
    return uuid.uuid4().bytes 

def now_epoch() -> int:
    return int(time.time() * 1000) #ms precision


PBKDF2_ITERATIONS = 210_000
SALT_BYTES = 16


class UserService:

    def __init__(self, repo: UserRepository):
        self.repo = repo

    def _generate_salt(self) -> bytes:
        return secrets.token_bytes(SALT_BYTES)

    def _hash_password(self, password: str, salt: bytes) -> bytes:
        return hashlib.pbkdf2_hmac(
            "sha256",
            password.encode("utf-8"),
            salt,
            PBKDF2_ITERATIONS,
            dklen=32,
        )

    def _verify_password(self, password: str, salt: bytes, pwd_hash: bytes) -> bool:
        candidate = self._hash_password(password, salt)
        return secrets.compare_digest(candidate, pwd_hash)

    def _parse_permission_value(self, value: str | None):
        if value is None:
            return None

        v = value.strip().lower()

        if v == "true":
            return True
        if v == "false":
            return False

        try:
            return int(value)
        except:
            pass

        try:
            return json.loads(value)
        except:
            pass

        return value


    def create_user(self, username: str, password: str) -> bytes:
        username = username.strip()

        if len(username) < 3:
            raise ValueError("Username must be at least 3 characters.")
        if len(password) < 6:
            raise ValueError("Password must be at least 6 characters.")

        salt = self._generate_salt()
        pwd_hash = self._hash_password(password, salt)
        user_id = new_uuid()
        ts = now_epoch()

        self.repo.insert_user(
            user_id=user_id,
            username=username,
            password_hash=pwd_hash,
            salt=salt,
            created_ts=ts,
        )

        # Create default permissions
        self.repo.set_permissions(
            user_id=user_id,
            allow_ret=0,          # retrieval disabled
            allowed_col="[]",     # JSON string
            max_cls=0,
        )

        return user_id
    
    def load_user(self, user_id: bytes) -> Optional[User]:
        row = self.repo.get_user_by_id(user_id)
        if not row:
            return None
        roles = self.repo.get_user_roles(user_id)
        role_names = [r["name"] for r in roles]

        permissions = self.compute_user_permissions(user_id)

        return User(
            id=row["id"].hex(),
            username=row["username"],
            roles=role_names,
            permissions=permissions,
            must_change_pw=bool(row["must_change_pw"]),
            created_at=int(row["created_at"])
        )
    
    def list_users(self):
        rows = self.repo.list_users()
        return [
            {
                "id": row["id"].hex(),
                "username": row["username"],
                "roles": row["roles"].split(",") if row["roles"] else [],
                "created_at": row["created_at"],
                "updated_at": row["updated_at"]
            }
            for row in rows
        ]


    def authenticate(self, username: str, password: str) -> tuple[bool, str, Optional[bytes]]:

        NACK_MSG = "Invalid username or password."
        ACK_MSG = "Login successful."

        if not username or not password:
            return False, NACK_MSG, None

        row = self.repo.get_user_by_username(username)
        if not row:
            return False, NACK_MSG, None

        if not self._verify_password(password, row["salt"], row["password_hash"]):
            return False, NACK_MSG, None
        
        return True, ACK_MSG, row

    def change_password(self, user_id: bytes, current_pw: str, new_pw: str) -> bool:
        row = self.repo.get_user_by_id(user_id)
        if not row:
            return False

        if not self._verify_password(current_pw, row["salt"], row["password_hash"]):
            return False

        if len(new_pw) < 6:
            raise ValueError("New password must be at least 6 characters.")

        new_salt = self._generate_salt()
        new_hash = self._hash_password(new_pw, new_salt)

        self.repo.update_password(
            user_id=user_id,
            new_hash=new_hash,
            new_salt=new_salt,
            updated_ts=now_epoch(),
        )
        self.repo.clear_must_change_pw(user_id=user_id, updated_ts=now_epoch())
        return True


    def _resolve_role_permissions(self, role_id: int, visited=None):
        """
        Recursively resolve permissions for a role, including its parent roles.
        Later (child) permissions override inherited ones.
        """
        if visited is None:
            visited = set()

        # Prevent infinite loops
        if role_id in visited:
            return {}

        visited.add(role_id)

        perms = {}

        # ---- 1. Load direct permissions for this role ----
        direct_rows = self.repo.get_role_permissions(role_id)
        for r in direct_rows:
            perms[r["name"]] = self._parse_permission_value(r["value"])

        # ---- 2. Load inherited permissions from parent roles ----
        parent_rows = self.repo.get_parent_roles(role_id)
        for p in parent_rows:
            parent_id = p["parent_id"]

            inherited = self._resolve_role_permissions(parent_id, visited)

            # Parent permissions apply FIRST
            # Child (this role) overrides
            perms = {**inherited, **perms}

        return perms


    def compute_user_permissions(self, user_id: bytes) -> Permissions:
        """
        Aggregate permissions from all roles (and their ancestors) assigned to the user.
        """
        role_rows = self.repo.get_user_roles(user_id)
        role_ids = [r["id"] for r in role_rows]

        if not role_rows:
            return Permissions.default()

        effective = {}

        # Resolve each role’s full inherited permission set
        for rid in role_ids:
            role_perms = self._resolve_role_permissions(rid)
            effective = {**effective, **role_perms}  # later roles override earlier

        # Build Permissions model
        p = Permissions()
        known_fields = set(Permissions.model_fields.keys())

        for key, val in effective.items():
            if key in known_fields:
                setattr(p, key, val)
            else:
                p.extra[key] = val

        return p

    def update_permissions(self, user_id: bytes, permissions: Permissions):
        self.repo.set_permissions(
            user_id=user_id,
            allow_ret=1 if permissions.allow_retrieval else 0,
            allowed_col=permissions.allowed_collections_json(),
            max_cls=permissions.max_classification,
        )

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

        self.repo.update_conversation_updated_at(c_id, ts = now)
        return msg_id

        
    def delete_conversation_message(self, user_id: bytes, c_id: bytes, msg_id: bytes):
        # implement checks, for now just pass
        self.repo.delete_message(c_id, msg_id)

    def create_user_conversation(self, user_id: bytes, title: str):
        conv_id = new_uuid()
        now = now_epoch()
        self.repo.insert_conversation(conv_id, user_id, title, "{}", now)
        return conv_id

    def rename_user_conversation(self, user_id: bytes, c_id: bytes,  title: str):
        self.repo.update_conversation_title(user_id, c_id, title)

    def delete_user_conversation(self, user_id: bytes, c_id: bytes):
        self.repo.delete_conversation(user_id, c_id)