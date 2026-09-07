from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from hestia.api.routers.workflow_settings import router, _STARTER_YAML
from hestia.api.security import get_current_user
from hestia.api.dependencies import get_handler
from tests.unit.conftest import _make_user

# A minimal but structurally realistic workflow, mirroring the shape of
# hestia/templates/workflows/chat.yaml (single Chat node, no retrieval).
_VALID_YAML = """entrypoint: Chat1
exitpoints: [Chat1]
nodes:
  - id: Chat1
    type: Chat
    inputs:
      history: ${history}
      last_user_message: ${last_user_message}
      model: ${model}
      options: ${model_kwargs}
    outputs:
      response: response
"""

# Same node id twice -> validate_workflow_graph raises ValidationError
# ("Duplicate node id"), exercising the invalid-graph rejection path.
_INVALID_GRAPH_YAML = """entrypoint: Chat1
nodes:
  - id: Chat1
    type: Chat
    inputs: {}
    outputs: {}
  - id: Chat1
    type: Chat
    inputs: {}
    outputs: {}
"""

_MALFORMED_YAML = "entrypoint: [unclosed"

_NON_MAPPING_YAML = "- a\n- b\n"


def _app(user=None, handler=None):
    app = FastAPI()
    app.include_router(router)
    app.dependency_overrides[get_current_user] = lambda: (user or _make_user(is_admin=True))
    app.dependency_overrides[get_handler] = lambda: (handler or MagicMock())
    return app


def _handler(tmp_path):
    """A MagicMock handler whose container.settings.project_root/app_data
    point at real directories under tmp_path, so the router's Path.glob /
    read_text / write_text / mkdir / unlink calls hit a real (temporary)
    filesystem instead of MagicMock stand-ins."""
    h = MagicMock()
    project_root = tmp_path / "project"
    app_data = tmp_path / "app_data"
    (project_root / "hestia" / "templates" / "workflows").mkdir(parents=True)
    (app_data / "templates" / "workflows").mkdir(parents=True)
    h.container.settings.project_root = project_root
    h.container.settings.app_data = app_data
    return h


def _source_dir(h):
    return h.container.settings.project_root / "hestia" / "templates" / "workflows"


def _live_dir(h):
    return h.container.settings.app_data / "templates" / "workflows"


# ---------------------------------------------------------------------------
# GET /workflows
# ---------------------------------------------------------------------------

class TestListWorkflows:

    def test_lists_builtin_unmodified_custom_and_admin_created(self, tmp_path):
        h = _handler(tmp_path)
        # builtin, untouched (source == live)
        (_source_dir(h) / "chat.yaml").write_text(_VALID_YAML, encoding="utf-8")
        (_live_dir(h) / "chat.yaml").write_text(_VALID_YAML, encoding="utf-8")
        # builtin, admin-edited (source exists but differs from live)
        (_source_dir(h) / "rag_chat.yaml").write_text(_VALID_YAML, encoding="utf-8")
        (_live_dir(h) / "rag_chat.yaml").write_text(_VALID_YAML + "\n# edited\n", encoding="utf-8")
        # admin-created, no source at all
        (_live_dir(h) / "custom1.yaml").write_text(_VALID_YAML, encoding="utf-8")

        client = TestClient(_app(handler=h))
        resp = client.get("/workflows")

        assert resp.status_code == 200
        workflows = {w["exec_type"]: w for w in resp.json()["workflows"]}
        assert set(workflows) == {"chat", "rag_chat", "custom1"}

        assert workflows["chat"]["is_builtin"] is True
        assert workflows["chat"]["is_custom"] is False

        assert workflows["rag_chat"]["is_builtin"] is True
        assert workflows["rag_chat"]["is_custom"] is True

        assert workflows["custom1"]["is_builtin"] is False
        assert workflows["custom1"]["is_custom"] is True
        assert workflows["custom1"]["yaml_text"] == _VALID_YAML

    def test_empty_when_no_live_workflows(self, tmp_path):
        h = _handler(tmp_path)
        client = TestClient(_app(handler=h))
        resp = client.get("/workflows")
        assert resp.status_code == 200
        assert resp.json()["workflows"] == []

    def test_non_admin_gets_403(self, tmp_path):
        h = _handler(tmp_path)
        client = TestClient(_app(user=_make_user(is_admin=False), handler=h))
        resp = client.get("/workflows")
        assert resp.status_code == 403


# ---------------------------------------------------------------------------
# POST /workflows (create)
# ---------------------------------------------------------------------------

class TestCreateWorkflow:

    def test_create_with_explicit_yaml_writes_live_file(self, tmp_path):
        h = _handler(tmp_path)
        client = TestClient(_app(handler=h))

        with patch("hestia.api.routers.workflow_settings.audit") as mock_audit:
            resp = client.post("/workflows", json={"name": "my_flow", "yaml_text": _VALID_YAML})

        assert resp.status_code == 200
        assert resp.json() == {"ok": True}
        written = _live_dir(h) / "my_flow.yaml"
        assert written.exists()
        # Request.str_strip_whitespace=True strips the trailing newline off
        # yaml_text before it ever reaches the handler.
        assert written.read_text(encoding="utf-8") == _VALID_YAML.strip()
        h.builder.repo.invalidate.assert_called_once()
        mock_audit.admin_action.assert_called_once()
        _, kwargs = mock_audit.admin_action.call_args
        assert kwargs["action"] == "workflow_create"
        assert kwargs["target"] == "my_flow"

    def test_create_without_yaml_uses_starter_template(self, tmp_path):
        h = _handler(tmp_path)
        client = TestClient(_app(handler=h))

        resp = client.post("/workflows", json={"name": "blank_flow"})

        assert resp.status_code == 200
        written = _live_dir(h) / "blank_flow.yaml"
        assert written.read_text(encoding="utf-8") == _STARTER_YAML

    def test_create_duplicate_name_rejected(self, tmp_path):
        h = _handler(tmp_path)
        (_live_dir(h) / "dup.yaml").write_text(_VALID_YAML, encoding="utf-8")
        client = TestClient(_app(handler=h))

        resp = client.post("/workflows", json={"name": "dup", "yaml_text": _VALID_YAML})

        assert resp.status_code == 400
        assert "already exists" in resp.json()["detail"]

    def test_create_invalid_name_rejected(self, tmp_path):
        h = _handler(tmp_path)
        client = TestClient(_app(handler=h))

        resp = client.post("/workflows", json={"name": "bad name!", "yaml_text": _VALID_YAML})

        assert resp.status_code == 400
        assert not (_live_dir(h) / "bad name!.yaml").exists()

    def test_create_malformed_yaml_rejected(self, tmp_path):
        h = _handler(tmp_path)
        client = TestClient(_app(handler=h))

        resp = client.post("/workflows", json={"name": "bad_yaml", "yaml_text": _MALFORMED_YAML})

        assert resp.status_code == 400
        assert "Invalid YAML" in resp.json()["detail"]
        assert not (_live_dir(h) / "bad_yaml.yaml").exists()

    def test_create_non_mapping_yaml_rejected(self, tmp_path):
        h = _handler(tmp_path)
        client = TestClient(_app(handler=h))

        resp = client.post("/workflows", json={"name": "list_yaml", "yaml_text": _NON_MAPPING_YAML})

        assert resp.status_code == 400
        assert "mapping" in resp.json()["detail"]

    def test_create_invalid_graph_rejected(self, tmp_path):
        h = _handler(tmp_path)
        client = TestClient(_app(handler=h))

        resp = client.post("/workflows", json={"name": "bad_graph", "yaml_text": _INVALID_GRAPH_YAML})

        assert resp.status_code == 400
        assert "Duplicate node id" in resp.json()["detail"]
        assert not (_live_dir(h) / "bad_graph.yaml").exists()
        h.builder.repo.invalidate.assert_not_called()

    def test_non_admin_gets_403(self, tmp_path):
        h = _handler(tmp_path)
        client = TestClient(_app(user=_make_user(is_admin=False), handler=h))

        resp = client.post("/workflows", json={"name": "nope", "yaml_text": _VALID_YAML})

        assert resp.status_code == 403
        assert not (_live_dir(h) / "nope.yaml").exists()


# ---------------------------------------------------------------------------
# PUT /workflows/{exec_type} (update)
# ---------------------------------------------------------------------------

class TestUpdateWorkflow:

    def test_update_overwrites_existing_live_file(self, tmp_path):
        h = _handler(tmp_path)
        (_live_dir(h) / "chat.yaml").write_text(_VALID_YAML, encoding="utf-8")
        updated = _VALID_YAML + "\n# admin edit\n"
        client = TestClient(_app(handler=h))

        with patch("hestia.api.routers.workflow_settings.audit") as mock_audit:
            resp = client.put("/workflows/chat", json={"yaml_text": updated})

        assert resp.status_code == 200
        assert (_live_dir(h) / "chat.yaml").read_text(encoding="utf-8") == updated.strip()
        h.builder.repo.invalidate.assert_called_once()
        _, kwargs = mock_audit.admin_action.call_args
        assert kwargs["action"] == "workflow_update"
        assert kwargs["target"] == "chat"

    def test_update_invalid_graph_rejected_and_file_untouched(self, tmp_path):
        h = _handler(tmp_path)
        (_live_dir(h) / "chat.yaml").write_text(_VALID_YAML, encoding="utf-8")
        client = TestClient(_app(handler=h))

        resp = client.put("/workflows/chat", json={"yaml_text": _INVALID_GRAPH_YAML})

        assert resp.status_code == 400
        assert (_live_dir(h) / "chat.yaml").read_text(encoding="utf-8") == _VALID_YAML
        h.builder.repo.invalidate.assert_not_called()

    def test_update_invalid_name_rejected(self, tmp_path):
        h = _handler(tmp_path)
        client = TestClient(_app(handler=h))

        resp = client.put("/workflows/bad!name", json={"yaml_text": _VALID_YAML})

        assert resp.status_code == 400

    def test_non_admin_gets_403(self, tmp_path):
        h = _handler(tmp_path)
        (_live_dir(h) / "chat.yaml").write_text(_VALID_YAML, encoding="utf-8")
        client = TestClient(_app(user=_make_user(is_admin=False), handler=h))

        resp = client.put("/workflows/chat", json={"yaml_text": _VALID_YAML + "\nx"})

        assert resp.status_code == 403
        assert (_live_dir(h) / "chat.yaml").read_text(encoding="utf-8") == _VALID_YAML


# ---------------------------------------------------------------------------
# DELETE /workflows/{exec_type} (reset built-in / delete custom)
# ---------------------------------------------------------------------------

class TestResetOrDeleteWorkflow:

    def test_builtin_workflow_is_reset_to_source(self, tmp_path):
        h = _handler(tmp_path)
        (_source_dir(h) / "chat.yaml").write_text(_VALID_YAML, encoding="utf-8")
        (_live_dir(h) / "chat.yaml").write_text(_VALID_YAML + "\n# edited\n", encoding="utf-8")
        client = TestClient(_app(handler=h))

        with patch("hestia.api.routers.workflow_settings.audit") as mock_audit:
            resp = client.delete("/workflows/chat")

        assert resp.status_code == 200
        assert (_live_dir(h) / "chat.yaml").read_text(encoding="utf-8") == _VALID_YAML
        h.builder.repo.invalidate.assert_called_once()
        _, kwargs = mock_audit.admin_action.call_args
        assert kwargs["action"] == "workflow_reset"
        assert kwargs["target"] == "chat"

    def test_custom_workflow_is_deleted(self, tmp_path):
        h = _handler(tmp_path)
        (_live_dir(h) / "custom1.yaml").write_text(_VALID_YAML, encoding="utf-8")
        client = TestClient(_app(handler=h))

        with patch("hestia.api.routers.workflow_settings.audit") as mock_audit:
            resp = client.delete("/workflows/custom1")

        assert resp.status_code == 200
        assert not (_live_dir(h) / "custom1.yaml").exists()
        h.builder.repo.invalidate.assert_called_once()
        _, kwargs = mock_audit.admin_action.call_args
        assert kwargs["action"] == "workflow_delete"
        assert kwargs["target"] == "custom1"

    def test_nonexistent_workflow_returns_404(self, tmp_path):
        h = _handler(tmp_path)
        client = TestClient(_app(handler=h))

        resp = client.delete("/workflows/ghost")

        assert resp.status_code == 404
        h.builder.repo.invalidate.assert_not_called()

    def test_invalid_name_rejected(self, tmp_path):
        h = _handler(tmp_path)
        client = TestClient(_app(handler=h))

        resp = client.delete("/workflows/" + "x" * 65)

        assert resp.status_code == 400

    def test_non_admin_gets_403(self, tmp_path):
        h = _handler(tmp_path)
        (_live_dir(h) / "custom1.yaml").write_text(_VALID_YAML, encoding="utf-8")
        client = TestClient(_app(user=_make_user(is_admin=False), handler=h))

        resp = client.delete("/workflows/custom1")

        assert resp.status_code == 403
        assert (_live_dir(h) / "custom1.yaml").exists()
