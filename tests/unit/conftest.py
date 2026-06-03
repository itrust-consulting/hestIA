"""Shared fixtures for the unit test suite."""
from __future__ import annotations

import uuid
from unittest.mock import MagicMock

import pytest

from hestia.domain.auth.models import CollectionPermission, Permissions, User


# ---------------------------------------------------------------------------
# Canonical user factories
# ---------------------------------------------------------------------------

def _make_user(
    *,
    is_admin: bool = False,
    allowed_collections: dict | None = None,
    moderated_tenants: list | None = None,
    role_assignable_tenants: list | None = None,
) -> User:
    return User(
        id=uuid.uuid4(),
        username="testuser",
        email="test@example.com",
        first_name="Test",
        last_name="User",
        roles=[],
        orgs=[],
        permissions=Permissions(
            is_admin=is_admin,
            allowed_collections=allowed_collections or {},
            moderated_tenants=moderated_tenants or [],
            role_assignable_tenants=role_assignable_tenants or [],
        ),
        must_change_pw=False,
        auth_source="local",
        created_at=0,
        updated_at=0,
        expires_at=None,
    )


@pytest.fixture
def admin_user() -> User:
    return _make_user(is_admin=True)


@pytest.fixture
def plain_user() -> User:
    return _make_user()


@pytest.fixture
def moderator_user() -> User:
    return _make_user(moderated_tenants=[1, 2])


@pytest.fixture
def user_with_collection() -> User:
    return _make_user(
        allowed_collections={"my-col": CollectionPermission(access=True, max_classification=2)}
    )
