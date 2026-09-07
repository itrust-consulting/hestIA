from __future__ import annotations
import uuid
from enum import Enum
from pydantic import BaseModel, Field


class CollectionPermission(BaseModel):
    access: bool = False
    max_classification: int | None = None


class Permissions(BaseModel):
    is_admin: bool = False
    allowed_collections: dict[str, CollectionPermission] = Field(default_factory=dict)
    moderated_tenants: list[int] = Field(default_factory=list)
    role_assignable_tenants: list[int] = Field(default_factory=list)

    def can_read_collection(self, collection_id: str) -> bool:
        """Whether this user has (specific-or-wildcard) read access to a
        collection — the same wildcard-falls-back-to-specific lookup used by
        chat/search/collection-listing. A specific grant always wins over the
        wildcard, including an explicit deny (access=False)."""
        if self.is_admin:
            return True
        perm = self.allowed_collections.get(collection_id) or self.allowed_collections.get("*")
        return bool(perm and perm.access)


class Role(str, Enum):
    ADMIN = "admin"
    USER = "user"


class User(BaseModel):
    id: uuid.UUID
    username: str
    email: str
    first_name: str
    last_name: str
    roles: list[dict]
    orgs: list[dict]
    permissions: Permissions
    must_change_pw: bool
    auth_source: str
    created_at: int
    updated_at: int
    expires_at: int | None


class AuthResult(BaseModel):
    success: bool
    message: str
    user_id: uuid.UUID | None = None
    username: str | None = None
    email: str | None = None
    first_name: str | None = None
    last_name: str | None = None
    groups: list[str] | None = None
    auth_source: str | None = None
    must_change_pw: int | bool | None = None

    @staticmethod
    def ack(user_id: uuid.UUID, message: str = "Login successful.") -> "AuthResult":
        return AuthResult(success=True, message=message, user_id=user_id)

    @staticmethod
    def nack(message: str = "Invalid username or password.") -> "AuthResult":
        return AuthResult(success=False, message=message)
