from __future__ import annotations

from types import SimpleNamespace

import pytest

from hestia.container import _bootstrap_admin_user
from hestia.domain.auth.users import UserService
from hestia.domain.exceptions import ConfigurationError
from hestia.infrastructure.db.user_repository import UserRepository, create_sqlite_connection


# ---------------------------------------------------------------------------
# Fixtures — in-memory SQLite
# ---------------------------------------------------------------------------

@pytest.fixture
def repo():
    get_conn, close, lock = create_sqlite_connection(":memory:")
    r = UserRepository(get_conn=get_conn, db_lock=lock)
    r.initialize()
    return r


@pytest.fixture
def user_service(repo):
    return UserService(repo, password_min_length=15)


def _settings(username=None, password=None, email=None):
    return SimpleNamespace(
        bootstrap_admin_username=username,
        bootstrap_admin_password=password,
        bootstrap_admin_email=email,
        bootstrap_admin_first_name="Admin",
        bootstrap_admin_last_name="User",
    )


# ---------------------------------------------------------------------------
# _bootstrap_admin_user
# ---------------------------------------------------------------------------

class TestBootstrapAdminUser:

    def test_creates_admin_when_empty_and_configured(self, repo, user_service):
        settings = _settings("admin", "a" * 20, "admin@example.com")
        _bootstrap_admin_user(settings, repo, user_service)

        users = repo.list_users()
        assert len(users) == 1
        assert users[0]["username"] == "admin"
        assert users[0]["must_change_pw"] == 1

        roles = user_service.list_user_roles(
            __import__("uuid").UUID(bytes=bytes(users[0]["id"]))
        )
        assert {r["name"] for r in roles} == {"admin"}

    def test_raises_when_empty_and_not_configured(self, repo, user_service):
        settings = _settings(None, None, None)
        with pytest.raises(ConfigurationError, match="DEFAULT_ADMIN"):
            _bootstrap_admin_user(settings, repo, user_service)
        assert repo.list_users() == []

    def test_raises_when_only_partially_configured(self, repo, user_service):
        settings = _settings("admin", "a" * 20, None)
        with pytest.raises(ConfigurationError, match="DEFAULT_ADMIN"):
            _bootstrap_admin_user(settings, repo, user_service)
        assert repo.list_users() == []

    def test_noop_when_users_already_exist(self, repo, user_service):
        user_service.create_user(
            username="existing", email="existing@example.com", password="b" * 20,
            first_name="Existing", last_name="User", roles=["user"],
        )
        settings = _settings(None, None, None)
        _bootstrap_admin_user(settings, repo, user_service)  # should not raise
        assert len(repo.list_users()) == 1
