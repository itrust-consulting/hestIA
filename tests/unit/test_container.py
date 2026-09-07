from __future__ import annotations

import pathlib
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from hestia.config.settings import AuthSettings, Settings
from hestia.container import Container, _bootstrap_admin_user, build_container
from hestia.domain.auth.users import UserService
from hestia.domain.exceptions import ConfigurationError
from hestia.infrastructure.db.auth_settings_repository import AuthSettingsRepository
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


# ---------------------------------------------------------------------------
# Container.apply_auth_update
# ---------------------------------------------------------------------------

class _SpyServices(dict):
    """Records every mutation so tests can distinguish a single atomic
    dict.update() from a sequence of individual __setitem__ calls."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setitem_keys: list = []
        self.update_calls: list = []

    def __setitem__(self, key, value):
        self.setitem_keys.append(key)
        super().__setitem__(key, value)

    def update(self, *args, **kwargs):
        merged = dict(*args, **kwargs)
        self.update_calls.append(set(merged.keys()))
        super().update(*args, **kwargs)


class TestApplyAuthUpdate:

    def _container(self):
        get_conn, _, lock = create_sqlite_connection(":memory:")
        user_repo = UserRepository(get_conn=get_conn, db_lock=lock)
        user_repo.initialize()

        settings = SimpleNamespace(auth=AuthSettings(token_secret_key="x" * 32), oidc=None, ldap=None)
        auth_settings_repo = AuthSettingsRepository(get_conn, lock)
        auth_settings_repo.initialize(settings)

        container = Container(settings=settings)
        container.services = _SpyServices({
            "auth_settings": auth_settings_repo,
            "user_repository": user_repo,
            "notification_settings": MagicMock(get_settings=MagicMock(return_value=None)),
        })
        return container

    def test_swaps_auth_users_notifications_in_one_update_not_sequential_assignment(self):
        # Regression test: these three used to be assigned one at a time
        # (self.services["auth"] = ..., then ["users"], then
        # ["notifications"]) -- a request reading self.services between two
        # of those assignments could observe a new auth service paired with
        # a stale users/notifications service.
        container = self._container()

        container.apply_auth_update()

        assert container.services.update_calls == [{"auth", "users", "notifications"}]
        assert "auth" not in container.services.setitem_keys
        assert "users" not in container.services.setitem_keys
        assert "notifications" not in container.services.setitem_keys

    def test_new_user_service_is_wired_to_the_new_notifications_service(self):
        container = self._container()
        container.apply_auth_update()

        users = container.services["users"]
        notifications = container.services["notifications"]
        assert users.on_user_created == notifications.send_welcome_notification

    def test_noop_when_auth_settings_row_missing(self):
        container = self._container()
        container.services["auth_settings"] = MagicMock(get_settings=MagicMock(return_value=None))

        container.apply_auth_update()

        assert container.services.update_calls == []


# ---------------------------------------------------------------------------
# Container.require_service / require_db_provider
# ---------------------------------------------------------------------------

class TestRequireServiceAndDbProvider:

    def test_require_service_returns_present_service(self):
        c = Container(settings=MagicMock())
        c.services["foo"] = "bar"
        assert c.require_service("foo") == "bar"

    def test_require_service_raises_configuration_error_when_missing(self):
        c = Container(settings=MagicMock())
        with pytest.raises(ConfigurationError, match="foo"):
            c.require_service("foo")

    def test_require_db_provider_returns_present_provider(self):
        c = Container(settings=MagicMock())
        c.providers["db"] = "dbobj"
        assert c.require_db_provider() == "dbobj"

    def test_require_db_provider_raises_configuration_error_when_missing(self):
        c = Container(settings=MagicMock())
        with pytest.raises(ConfigurationError):
            c.require_db_provider()


# ---------------------------------------------------------------------------
# Container.get_or_build_provider
# ---------------------------------------------------------------------------

class TestGetOrBuildProvider:

    def test_returns_cached_provider_without_touching_repo(self):
        c = Container(settings=MagicMock())
        sentinel = MagicMock()
        c.providers_by_connection[1] = sentinel
        c.services["llm_settings"] = MagicMock()

        result = c.get_or_build_provider(1)

        assert result is sentinel
        c.services["llm_settings"].get_connection.assert_not_called()

    def test_builds_and_caches_a_new_provider(self):
        # build_llm_provider is patched here (not just given a fake base_url)
        # because the real vLLMProvider/HttpClient construction path is slow
        # in this environment (each httpx.Client()/AsyncClient() ~1.4s) --
        # that construction cost is covered by test_vllm.py, not this file.
        c = Container(settings=MagicMock(request_timeout=(1.0, 2.0)))
        llm_settings = MagicMock()
        llm_settings.get_connection.return_value = {
            "backend_type": "openai", "base_url": "http://llm.example", "api_key": "k",
        }
        c.services["llm_settings"] = llm_settings
        sentinel = MagicMock()

        with patch("hestia.container.build_llm_provider", return_value=sentinel) as mock_build:
            provider = c.get_or_build_provider(5)

        mock_build.assert_called_once_with("openai", "http://llm.example", "k", (1.0, 2.0))
        assert provider is sentinel
        assert c.providers_by_connection[5] is sentinel


# ---------------------------------------------------------------------------
# Container.apply_connection_update / apply_connection_delete
# ---------------------------------------------------------------------------

class TestApplyConnectionUpdate:

    def test_noop_when_connection_row_missing(self):
        c = Container(settings=MagicMock())
        llm_settings = MagicMock()
        llm_settings.get_connection.return_value = None
        c.services["llm_settings"] = llm_settings

        c.apply_connection_update(1)  # must not raise

    def test_vector_db_purpose_rebuilds_client_in_place(self):
        c = Container(settings=MagicMock())
        llm_settings = MagicMock()
        llm_settings.get_connection.return_value = {
            "purpose": "vector_db", "backend_type": "qdrant",
            "base_url": "http://qdrant.example", "api_key": "k", "params": {"foo": "bar"},
        }
        c.services["llm_settings"] = llm_settings
        db = MagicMock()
        c.providers["db"] = db
        search_svc = MagicMock()
        c.services["search"] = search_svc

        with patch("hestia.container.build_db_provider") as mock_build:
            mock_build.return_value = MagicMock(client="new-client")
            c.apply_connection_update(1)

        assert db.client == "new-client"
        assert search_svc.default_options == {"foo": "bar"}

    def test_vector_db_purpose_noop_when_no_db_provider_yet(self):
        c = Container(settings=MagicMock())
        llm_settings = MagicMock()
        llm_settings.get_connection.return_value = {
            "purpose": "vector_db", "backend_type": "qdrant", "base_url": "http://x", "api_key": None, "params": None,
        }
        c.services["llm_settings"] = llm_settings

        c.apply_connection_update(1)  # must not raise even with no existing "db" provider

    def test_llm_purpose_rewires_url_api_key_and_backing_services(self):
        # build_llm_provider is patched to a MagicMock for the same reason as
        # TestGetOrBuildProvider above -- real vLLMProvider/HttpClient
        # construction is slow in this environment and isn't what this test
        # is checking (container.py's own rewiring logic is).
        c = Container(settings=MagicMock(request_timeout=(1.0, 2.0)))
        llm_settings = MagicMock()
        row = {
            "id": 1, "purpose": "generation", "backend_type": "openai",
            "base_url": "http://new.example", "api_key": "newkey", "model": "m2",
            "params": {"temperature": 0.5}, "compaction_enabled": True, "compaction_model": "cm",
            "compaction_context_window": 1000, "compaction_summary_length": 100,
        }
        llm_settings.get_connection.return_value = row
        c.services["llm_settings"] = llm_settings
        generate_svc = MagicMock()
        c.services["generate"] = generate_svc
        c.services["chat"] = generate_svc

        with patch("hestia.container.build_llm_provider", return_value=MagicMock()):
            c.apply_connection_update(1)

        provider = c.providers_by_connection[1]
        assert provider.http_chat.base_url == "http://new.example"
        assert provider.http_chat.api_key == "newkey"
        assert generate_svc.default_model == "m2"
        assert generate_svc.default_options == {"temperature": 0.5}
        assert generate_svc.compaction_enabled is True
        assert generate_svc.compaction_model == "cm"


class TestApplyConnectionDelete:

    def test_vector_db_purpose_drops_db_provider_and_cached_client(self):
        c = Container(settings=MagicMock())
        c.providers["db"] = MagicMock()
        c.providers_by_connection[1] = MagicMock()

        c.apply_connection_delete(1, purpose="vector_db")

        assert "db" not in c.providers
        assert 1 not in c.providers_by_connection

    def test_llm_purpose_drops_backing_services_and_cached_provider(self):
        c = Container(settings=MagicMock())
        c.services["generate"] = MagicMock()
        c.services["chat"] = MagicMock()
        c.providers_by_connection[2] = MagicMock()

        c.apply_connection_delete(2, purpose="generation")

        assert "generate" not in c.services
        assert "chat" not in c.services
        assert 2 not in c.providers_by_connection

    def test_unknown_purpose_only_drops_cached_provider(self):
        c = Container(settings=MagicMock())
        c.providers_by_connection[3] = MagicMock()

        c.apply_connection_delete(3, purpose="reranking")  # no backing service today

        assert 3 not in c.providers_by_connection


# ---------------------------------------------------------------------------
# build_container — end-to-end against a real in-memory sqlite DB
# ---------------------------------------------------------------------------

class TestBuildContainer:

    def _settings(self, tmp_path, services_to_start=None):
        # A real temp-file DB, not ":memory:" -- build_container closes its
        # setup-time connection partway through (see its own comment) and
        # reopens later for the RAG-services section; ":memory:" would lose
        # all data on that reopen since a fresh in-memory DB is empty, where
        # a real file naturally reconnects to the same data.
        kwargs = dict(
            auth=AuthSettings(token_secret_key="x" * 32),
            bootstrap_admin_username="admin",
            bootstrap_admin_password="a" * 20,
            bootstrap_admin_email="admin@example.com",
            udb_path=tmp_path / "users.db",
            corpus_stats=tmp_path / "corpus_stats",
        )
        if services_to_start is not None:
            kwargs["services_to_start"] = services_to_start
        return Settings(**kwargs)

    def _build(self, settings):
        # QdrantClient's real constructor makes a network call to check
        # server-version compatibility -- pointed at an unreachable default
        # URL, that just adds a slow timeout to every test here without
        # testing anything build_container itself is responsible for
        # (QdrantDB/QdrantClient behavior is covered by test_qdrant.py).
        # Likewise, real vLLMProvider/HttpClient construction is slow in
        # this environment (~1.4s per httpx.Client()) and isn't what these
        # tests check (covered by test_vllm.py) -- build_llm_provider is
        # patched to a fast stand-in for the same reason as the
        # get_or_build_provider/apply_connection_update tests above.
        with patch("hestia.infrastructure.db.qdrant.QdrantClient"), \
             patch("hestia.container.build_llm_provider", return_value=MagicMock()):
            return build_container(settings)

    def test_builds_all_default_services(self, tmp_path):
        c = self._build(self._settings(tmp_path))

        expected = {
            "llm_settings", "auth_settings", "sync_manifest", "user_repository", "notification_settings",
            "auth", "users", "notifications", "encDense", "encSparse", "generate", "chat", "search", "ingestion",
        }
        assert expected <= set(c.services.keys())
        assert "db" in c.providers

    def test_bootstrap_admin_created_on_fresh_install(self, tmp_path):
        c = self._build(self._settings(tmp_path))

        users = c.services["user_repository"].list_users()
        assert len(users) == 1
        assert users[0]["username"] == "admin"

    def test_notifications_wired_to_user_service_welcome_hook(self, tmp_path):
        c = self._build(self._settings(tmp_path))

        assert c.services["users"].on_user_created == c.services["notifications"].send_welcome_notification

    def test_services_to_start_gates_optional_services(self, tmp_path):
        c = self._build(self._settings(tmp_path, services_to_start=["generate"]))

        assert "generate" in c.services
        assert "encDense" not in c.services
        assert "encSparse" not in c.services
        assert "search" not in c.services
        assert "ingestion" not in c.services

    def test_always_on_services_present_regardless_of_services_to_start(self, tmp_path):
        c = self._build(self._settings(tmp_path, services_to_start=[]))

        # auth/users/notifications aren't gated by services_to_start at all
        assert "auth" in c.services
        assert "users" in c.services
        assert "notifications" in c.services
