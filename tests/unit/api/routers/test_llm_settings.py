from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from hestia.api.dependencies import get_handler
from hestia.api.routers.llm_settings import router
from hestia.api.security import get_current_user
from hestia.domain.exceptions import ProviderError
from tests.unit.conftest import _make_user


def _app(user=None, handler=None):
    app = FastAPI()
    app.include_router(router)
    app.dependency_overrides[get_current_user] = lambda: (user or _make_user(is_admin=True))
    app.dependency_overrides[get_handler] = lambda: (handler or MagicMock())
    return app


# ---------------------------------------------------------------------------
# GET /llm/connections
# ---------------------------------------------------------------------------

class TestListConnections:

    def test_admin_gets_connection_list(self):
        handler = MagicMock()
        handler.container.services = {"llm_settings": MagicMock(list_connections=MagicMock(
            return_value=[{"id": 1, "purpose": "generation"}]
        ))}
        client = TestClient(_app(handler=handler))
        resp = client.get("/llm/connections")
        assert resp.status_code == 200
        assert resp.json()["connections"] == [{"id": 1, "purpose": "generation"}]

    def test_non_admin_gets_403(self):
        client = TestClient(_app(user=_make_user(is_admin=False)))
        resp = client.get("/llm/connections")
        assert resp.status_code == 403


# ---------------------------------------------------------------------------
# POST /llm/connections
# ---------------------------------------------------------------------------

class TestCreateConnection:

    def test_creates_and_returns_id(self):
        handler = MagicMock()
        handler.container.services = {"llm_settings": MagicMock(create_connection=MagicMock(return_value=5))}
        client = TestClient(_app(handler=handler))
        resp = client.post("/llm/connections", json={
            "purpose": "generation", "backend_type": "openai", "base_url": "http://x", "api_key": "k",
        })
        assert resp.status_code == 200
        assert resp.json() == {"ok": True, "id": 5}

    def test_creation_is_audited_without_leaking_api_key(self):
        # Regression test: LLM connection CRUD used to have no audit trail
        # at all -- and the key itself must never be logged.
        handler = MagicMock()
        handler.container.services = {"llm_settings": MagicMock(create_connection=MagicMock(return_value=5))}
        with patch("hestia.api.routers.llm_settings.audit") as mock_audit:
            client = TestClient(_app(handler=handler))
            resp = client.post("/llm/connections", json={
                "purpose": "generation", "backend_type": "openai", "base_url": "http://x", "api_key": "super-secret",
            })
        assert resp.status_code == 200
        _, kwargs = mock_audit.connection_action.call_args
        assert kwargs["action"] == "connection_create"
        assert kwargs["target"] == "5"
        assert "super-secret" not in str(kwargs)

    def test_blank_base_url_rejected(self):
        handler = MagicMock()
        client = TestClient(_app(handler=handler))
        resp = client.post("/llm/connections", json={
            "purpose": "generation", "backend_type": "openai", "base_url": "   ",
        })
        assert resp.status_code == 400

    def test_failure_is_audited_with_purpose_as_target(self):
        # Regression test: connection CRUD used to audit only the success
        # path, since connection_action couldn't record a failure.
        handler = MagicMock()
        handler.container.services = {"llm_settings": MagicMock(
            create_connection=MagicMock(side_effect=RuntimeError("boom"))
        )}
        client = TestClient(_app(handler=handler), raise_server_exceptions=False)
        with patch("hestia.api.routers.llm_settings.audit") as mock_audit:
            resp = client.post("/llm/connections", json={
                "purpose": "generation", "backend_type": "openai", "base_url": "http://x", "api_key": "k",
            })
        assert resp.status_code == 500
        _, kwargs = mock_audit.connection_action.call_args
        assert kwargs["action"] == "connection_create"
        assert kwargs["target"] == "generation"
        assert kwargs["success"] is False

    def test_non_admin_gets_403(self):
        client = TestClient(_app(user=_make_user(is_admin=False)))
        resp = client.post("/llm/connections", json={
            "purpose": "generation", "backend_type": "openai", "base_url": "http://x",
        })
        assert resp.status_code == 403


# ---------------------------------------------------------------------------
# POST /llm/connections/test
# ---------------------------------------------------------------------------

class TestTestConnection:

    def test_qdrant_success(self):
        handler = MagicMock()
        db = MagicMock(collections={"collections": []})
        with patch("hestia.api.routers.llm_settings.build_db_provider", return_value=db) as mock_build:
            client = TestClient(_app(handler=handler))
            resp = client.post("/llm/connections/test", json={
                "backend_type": "qdrant", "base_url": "http://q", "api_key": "k",
            })
        assert resp.status_code == 200
        assert resp.json() == {"ok": True}
        mock_build.assert_called_once_with("qdrant", "http://q", "k")

    def test_llm_backend_success(self):
        handler = MagicMock()
        handler.container.settings.request_timeout = (10.0, 800.0)
        provider = MagicMock(models={"models": []})
        with patch("hestia.api.routers.llm_settings.build_llm_provider", return_value=provider) as mock_build:
            client = TestClient(_app(handler=handler))
            resp = client.post("/llm/connections/test", json={
                "backend_type": "openai", "base_url": "http://l", "api_key": "k",
            })
        assert resp.status_code == 200
        assert resp.json() == {"ok": True}
        mock_build.assert_called_once_with("openai", "http://l", "k", (10.0, 800.0))

    def test_reuses_existing_api_key_when_blank_and_editing(self):
        handler = MagicMock()
        handler.container.settings.request_timeout = (10.0, 800.0)
        handler.container.services = {"llm_settings": MagicMock(
            get_connection=MagicMock(return_value={"api_key": "stored-key"})
        )}
        provider = MagicMock(models={"models": []})
        with patch("hestia.api.routers.llm_settings.build_llm_provider", return_value=provider) as mock_build:
            client = TestClient(_app(handler=handler))
            resp = client.post("/llm/connections/test", json={
                "backend_type": "openai", "base_url": "http://l", "connection_id": 3,
            })
        assert resp.status_code == 200
        mock_build.assert_called_once_with("openai", "http://l", "stored-key", (10.0, 800.0))

    def test_provider_error_returns_ok_false(self):
        handler = MagicMock()
        with patch("hestia.api.routers.llm_settings.build_db_provider", side_effect=ProviderError("unreachable")):
            client = TestClient(_app(handler=handler))
            resp = client.post("/llm/connections/test", json={
                "backend_type": "qdrant", "base_url": "http://q",
            })
        assert resp.status_code == 200
        assert resp.json() == {"ok": False, "error": "unreachable"}

    def test_unexpected_error_returns_ok_false(self):
        handler = MagicMock()
        with patch("hestia.api.routers.llm_settings.build_db_provider", side_effect=RuntimeError("boom")):
            client = TestClient(_app(handler=handler))
            resp = client.post("/llm/connections/test", json={
                "backend_type": "qdrant", "base_url": "http://q",
            })
        assert resp.status_code == 200
        assert resp.json()["ok"] is False
        assert "boom" in resp.json()["error"]

    def test_blank_base_url_rejected(self):
        handler = MagicMock()
        client = TestClient(_app(handler=handler))
        resp = client.post("/llm/connections/test", json={"backend_type": "qdrant", "base_url": " "})
        assert resp.status_code == 400

    def test_no_connection_id_and_no_api_key_does_not_look_up_existing(self):
        handler = MagicMock()
        db = MagicMock(collections={"collections": []})
        with patch("hestia.api.routers.llm_settings.build_db_provider", return_value=db):
            client = TestClient(_app(handler=handler))
            resp = client.post("/llm/connections/test", json={"backend_type": "qdrant", "base_url": "http://q"})
        assert resp.status_code == 200
        handler.container.services.__getitem__.assert_not_called()

    def test_non_admin_gets_403(self):
        client = TestClient(_app(user=_make_user(is_admin=False)))
        resp = client.post("/llm/connections/test", json={"backend_type": "qdrant", "base_url": "http://q"})
        assert resp.status_code == 403


# ---------------------------------------------------------------------------
# PUT /llm/connections/{id}
# ---------------------------------------------------------------------------

class TestUpdateConnection:

    def _payload(self, **overrides):
        base = {"base_url": "http://new", "api_key": "k", "model": "m", "params": {}}
        base.update(overrides)
        return base

    def test_updates_and_applies_connection_update(self):
        handler = MagicMock()
        repo = MagicMock(get_connection=MagicMock(return_value={"id": 1}))
        handler.container.services = {"llm_settings": repo}
        client = TestClient(_app(handler=handler))

        resp = client.put("/llm/connections/1", json=self._payload())

        assert resp.status_code == 200
        repo.update_connection.assert_called_once()
        handler.container.apply_connection_update.assert_called_once_with(1)

    def test_404_when_connection_missing(self):
        handler = MagicMock()
        handler.container.services = {"llm_settings": MagicMock(get_connection=MagicMock(return_value=None))}
        client = TestClient(_app(handler=handler))
        resp = client.put("/llm/connections/1", json=self._payload())
        assert resp.status_code == 404

    def test_blank_base_url_rejected(self):
        handler = MagicMock()
        client = TestClient(_app(handler=handler))
        resp = client.put("/llm/connections/1", json=self._payload(base_url="  "))
        assert resp.status_code == 400

    def test_compaction_summary_must_be_less_than_context_window(self):
        handler = MagicMock()
        client = TestClient(_app(handler=handler))
        resp = client.put("/llm/connections/1", json=self._payload(
            compaction_enabled=True, compaction_context_window=100, compaction_summary_length=200,
        ))
        assert resp.status_code == 400

    def test_failure_is_audited(self):
        handler = MagicMock()
        repo = MagicMock(get_connection=MagicMock(return_value={"id": 1}))
        repo.update_connection.side_effect = RuntimeError("boom")
        handler.container.services = {"llm_settings": repo}
        client = TestClient(_app(handler=handler), raise_server_exceptions=False)
        with patch("hestia.api.routers.llm_settings.audit") as mock_audit:
            resp = client.put("/llm/connections/1", json=self._payload())
        assert resp.status_code == 500
        _, kwargs = mock_audit.connection_action.call_args
        assert kwargs["action"] == "connection_update"
        assert kwargs["target"] == "1"
        assert kwargs["success"] is False

    def test_non_admin_gets_403(self):
        client = TestClient(_app(user=_make_user(is_admin=False)))
        resp = client.put("/llm/connections/1", json=self._payload())
        assert resp.status_code == 403


# ---------------------------------------------------------------------------
# DELETE /llm/connections/{id}
# ---------------------------------------------------------------------------

class TestDeleteConnection:

    def test_deletes_and_applies_delete(self):
        handler = MagicMock()
        repo = MagicMock(get_connection=MagicMock(return_value={"purpose": "generation"}))
        handler.container.services = {"llm_settings": repo}
        client = TestClient(_app(handler=handler))

        resp = client.delete("/llm/connections/1")

        assert resp.status_code == 200
        repo.delete_connection.assert_called_once_with(connection_id=1)
        handler.container.apply_connection_delete.assert_called_once_with(1, "generation")

    def test_purpose_none_when_row_already_missing(self):
        handler = MagicMock()
        repo = MagicMock(get_connection=MagicMock(return_value=None))
        handler.container.services = {"llm_settings": repo}
        client = TestClient(_app(handler=handler))

        client.delete("/llm/connections/1")

        handler.container.apply_connection_delete.assert_called_once_with(1, None)

    def test_failure_is_audited(self):
        handler = MagicMock()
        repo = MagicMock(get_connection=MagicMock(return_value={"purpose": "generation"}))
        repo.delete_connection.side_effect = RuntimeError("boom")
        handler.container.services = {"llm_settings": repo}
        client = TestClient(_app(handler=handler), raise_server_exceptions=False)
        with patch("hestia.api.routers.llm_settings.audit") as mock_audit:
            resp = client.delete("/llm/connections/1")
        assert resp.status_code == 500
        _, kwargs = mock_audit.connection_action.call_args
        assert kwargs["action"] == "connection_delete"
        assert kwargs["success"] is False

    def test_non_admin_gets_403(self):
        client = TestClient(_app(user=_make_user(is_admin=False)))
        resp = client.delete("/llm/connections/1")
        assert resp.status_code == 403


# ---------------------------------------------------------------------------
# POST /llm/connections/{id}/activate
# ---------------------------------------------------------------------------

class TestActivateConnection:

    def test_activates_and_applies_update(self):
        handler = MagicMock()
        repo = MagicMock(get_connection=MagicMock(return_value={"id": 1}))
        handler.container.services = {"llm_settings": repo}
        client = TestClient(_app(handler=handler))

        resp = client.post("/llm/connections/1/activate")

        assert resp.status_code == 200
        repo.activate_connection.assert_called_once_with(connection_id=1)
        handler.container.apply_connection_update.assert_called_once_with(1)

    def test_404_when_missing(self):
        handler = MagicMock()
        handler.container.services = {"llm_settings": MagicMock(get_connection=MagicMock(return_value=None))}
        client = TestClient(_app(handler=handler))
        resp = client.post("/llm/connections/1/activate")
        assert resp.status_code == 404

    def test_failure_is_audited(self):
        handler = MagicMock()
        repo = MagicMock(get_connection=MagicMock(return_value={"id": 1}))
        repo.activate_connection.side_effect = RuntimeError("boom")
        handler.container.services = {"llm_settings": repo}
        client = TestClient(_app(handler=handler), raise_server_exceptions=False)
        with patch("hestia.api.routers.llm_settings.audit") as mock_audit:
            resp = client.post("/llm/connections/1/activate")
        assert resp.status_code == 500
        _, kwargs = mock_audit.connection_action.call_args
        assert kwargs["action"] == "connection_activate"
        assert kwargs["success"] is False

    def test_non_admin_gets_403(self):
        client = TestClient(_app(user=_make_user(is_admin=False)))
        resp = client.post("/llm/connections/1/activate")
        assert resp.status_code == 403


# ---------------------------------------------------------------------------
# GET /llm/connections/{id}/models
# ---------------------------------------------------------------------------

class TestListConnectionModels:

    def test_returns_model_names(self):
        handler = MagicMock()
        handler.container.services = {"llm_settings": MagicMock(get_connection=MagicMock(
            return_value={"purpose": "generation"}
        ))}
        provider = MagicMock(models={"models": [{"model": "a"}, {"model": "b"}, {"model": None}]})
        handler.container.get_or_build_provider.return_value = provider
        client = TestClient(_app(handler=handler))

        resp = client.get("/llm/connections/1/models")

        assert resp.status_code == 200
        assert resp.json() == {"ok": True, "models": ["a", "b"]}

    def test_vector_db_purpose_not_applicable(self):
        handler = MagicMock()
        handler.container.services = {"llm_settings": MagicMock(get_connection=MagicMock(
            return_value={"purpose": "vector_db"}
        ))}
        client = TestClient(_app(handler=handler))
        resp = client.get("/llm/connections/1/models")
        assert resp.status_code == 200
        assert resp.json()["ok"] is False
        assert resp.json()["models"] == []

    def test_404_when_connection_missing(self):
        handler = MagicMock()
        handler.container.services = {"llm_settings": MagicMock(get_connection=MagicMock(return_value=None))}
        client = TestClient(_app(handler=handler))
        resp = client.get("/llm/connections/1/models")
        assert resp.status_code == 404

    def test_provider_error_returns_ok_false(self):
        handler = MagicMock()
        handler.container.services = {"llm_settings": MagicMock(get_connection=MagicMock(
            return_value={"purpose": "generation"}
        ))}
        handler.container.get_or_build_provider.side_effect = ProviderError("down")
        client = TestClient(_app(handler=handler))
        resp = client.get("/llm/connections/1/models")
        assert resp.status_code == 200
        assert resp.json() == {"ok": False, "error": "down", "models": []}

    def test_unexpected_error_returns_ok_false(self):
        handler = MagicMock()
        handler.container.services = {"llm_settings": MagicMock(get_connection=MagicMock(
            return_value={"purpose": "generation"}
        ))}
        handler.container.get_or_build_provider.side_effect = RuntimeError("boom")
        client = TestClient(_app(handler=handler))
        resp = client.get("/llm/connections/1/models")
        assert resp.status_code == 200
        assert resp.json()["ok"] is False
        assert "boom" in resp.json()["error"]

    def test_non_admin_gets_403(self):
        client = TestClient(_app(user=_make_user(is_admin=False)))
        resp = client.get("/llm/connections/1/models")
        assert resp.status_code == 403
