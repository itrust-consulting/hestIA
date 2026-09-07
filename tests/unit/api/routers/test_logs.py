from __future__ import annotations

from unittest.mock import MagicMock, patch

from fastapi import FastAPI
from fastapi.testclient import TestClient

from hestia.api.routers.logs import router
from hestia.api.security import get_current_user
from hestia.api.dependencies import get_handler
from tests.unit.conftest import _make_user

import pytest


def _app(user=None, handler=None):
    app = FastAPI()
    app.include_router(router)
    app.dependency_overrides[get_current_user] = lambda: (user or _make_user(is_admin=True))
    app.dependency_overrides[get_handler] = lambda: (handler or MagicMock())
    return app


def _handler(log_dir="/var/log/hestia", log_level="INFO", log_to_console=False):
    h = MagicMock()
    h.container.settings.log_dir = log_dir
    h.container.settings.log_level = log_level
    h.container.settings.log_to_console = log_to_console
    return h


# ---------------------------------------------------------------------------
# GET /logs
# ---------------------------------------------------------------------------

class TestListLogs:

    def test_admin_gets_wired_results(self):
        handler = _handler(log_dir="/logs")
        entries = [{"ts": "2024-01-01T00:00:00.000Z", "level": "INFO", "msg": "hi"}]
        client = TestClient(_app(handler=handler))

        with patch("hestia.api.routers.logs.query_logs", return_value=(entries, 1)) as mock_query:
            resp = client.get("/logs")

        assert resp.status_code == 200
        data = resp.json()
        assert data["entries"] == entries
        assert data["total"] == 1
        mock_query.assert_called_once_with(
            "/logs", "system", level=None, search=None, since=None, until=None, limit=100, offset=0,
        )

    def test_query_params_forwarded(self):
        handler = _handler(log_dir="/logs")
        client = TestClient(_app(handler=handler))

        with patch("hestia.api.routers.logs.query_logs", return_value=([], 0)) as mock_query:
            resp = client.get("/logs", params={
                "log_type": "audit", "level": "WARNING", "search": "boom",
                "since": "2024-01-01T00:00:00Z", "until": "2024-02-01T00:00:00Z",
                "limit": 10, "offset": 5,
            })

        assert resp.status_code == 200
        mock_query.assert_called_once_with(
            "/logs", "audit", level="WARNING", search="boom",
            since="2024-01-01T00:00:00Z", until="2024-02-01T00:00:00Z",
            limit=10, offset=5,
        )

    def test_limit_out_of_range_rejected(self):
        client = TestClient(_app(handler=_handler()))
        resp = client.get("/logs", params={"limit": 1000})
        assert resp.status_code == 422

    def test_non_admin_gets_403(self):
        user = _make_user(is_admin=False)
        client = TestClient(_app(user=user, handler=_handler()))

        with patch("hestia.api.routers.logs.query_logs") as mock_query:
            resp = client.get("/logs")

        assert resp.status_code == 403
        mock_query.assert_not_called()


# ---------------------------------------------------------------------------
# GET /logs/export
# ---------------------------------------------------------------------------

class TestExportLogsEndpoint:

    def test_ndjson_export_streams_body_and_headers(self):
        handler = _handler(log_dir="/logs")
        client = TestClient(_app(handler=handler))
        lines = ['{"msg": "a"}\n', '{"msg": "b"}\n']

        with patch("hestia.api.routers.logs.export_logs", return_value=iter(lines)) as mock_export, \
             patch("hestia.api.routers.logs.audit") as mock_audit:
            resp = client.get("/logs/export")

        assert resp.status_code == 200
        assert resp.headers["content-type"].startswith("application/x-ndjson")
        assert 'filename="system-logs.ndjson"' in resp.headers["content-disposition"]
        assert resp.text == "".join(lines)
        mock_export.assert_called_once_with(
            "/logs", "system", level=None, search=None, since=None, until=None, format="ndjson",
        )
        mock_audit.admin_action.assert_called_once()

    def test_csv_export_uses_csv_media_type_and_filename(self):
        handler = _handler(log_dir="/logs")
        client = TestClient(_app(handler=handler))

        with patch("hestia.api.routers.logs.export_logs", return_value=iter(["a,b\n"])), \
             patch("hestia.api.routers.logs.audit"):
            resp = client.get("/logs/export", params={"log_type": "audit", "format": "csv"})

        assert resp.status_code == 200
        assert resp.headers["content-type"].startswith("text/csv")
        assert 'filename="audit-logs.csv"' in resp.headers["content-disposition"]

    def test_audit_action_records_filters(self):
        handler = _handler(log_dir="/logs")
        user = _make_user(is_admin=True)
        client = TestClient(_app(user=user, handler=handler))

        with patch("hestia.api.routers.logs.export_logs", return_value=iter([])), \
             patch("hestia.api.routers.logs.audit") as mock_audit:
            client.get("/logs/export", params={"level": "ERROR", "search": "x"})

        _, kwargs = mock_audit.admin_action.call_args
        assert kwargs["actor_id"] == str(user.id)
        assert kwargs["action"] == "logs_export"
        assert kwargs["target"] == "system"
        assert kwargs["detail"]["level"] == "ERROR"
        assert kwargs["detail"]["search"] == "x"

    def test_non_admin_gets_403(self):
        user = _make_user(is_admin=False)
        client = TestClient(_app(user=user, handler=_handler()))

        with patch("hestia.api.routers.logs.export_logs") as mock_export:
            resp = client.get("/logs/export")

        assert resp.status_code == 403
        mock_export.assert_not_called()


# ---------------------------------------------------------------------------
# GET /logs/settings
# ---------------------------------------------------------------------------

class TestGetLogSettings:

    def test_returns_current_settings(self):
        handler = _handler(log_dir="/var/log/hestia", log_level="DEBUG", log_to_console=True)
        client = TestClient(_app(handler=handler))

        resp = client.get("/logs/settings")

        assert resp.status_code == 200
        assert resp.json() == {
            "log_level": "DEBUG", "log_dir": "/var/log/hestia", "log_to_console": True,
        }

    def test_non_admin_gets_403(self):
        user = _make_user(is_admin=False)
        client = TestClient(_app(user=user, handler=_handler()))
        resp = client.get("/logs/settings")
        assert resp.status_code == 403


# ---------------------------------------------------------------------------
# PUT /logs/settings
# ---------------------------------------------------------------------------

class TestUpdateLogSettings:

    def test_updates_level_and_audits(self):
        handler = _handler(log_level="INFO")

        def _set_level(settings, level_name):
            settings.log_level = level_name.upper()

        user = _make_user(is_admin=True)
        client = TestClient(_app(user=user, handler=handler))

        with patch("hestia.api.routers.logs.set_log_level", side_effect=_set_level) as mock_set, \
             patch("hestia.api.routers.logs.audit") as mock_audit:
            resp = client.put("/logs/settings", json={"log_level": "debug"})

        assert resp.status_code == 200
        data = resp.json()
        assert data["ok"] is True
        assert data["log_level"] == "DEBUG"
        mock_set.assert_called_once_with(handler.container.settings, "debug")
        mock_audit.admin_action.assert_called_once_with(
            actor_id=str(user.id), action="log_level_change", target="logging",
            detail={"log_level": "debug"},
        )

    def test_invalid_level_returns_400(self):
        handler = _handler()
        client = TestClient(_app(handler=handler))

        with patch("hestia.api.routers.logs.set_log_level", side_effect=ValueError("Unknown log level: 'BOGUS'")):
            resp = client.put("/logs/settings", json={"log_level": "BOGUS"})

        assert resp.status_code == 400
        assert "BOGUS" in resp.json()["detail"]

    def test_non_admin_gets_403(self):
        user = _make_user(is_admin=False)
        client = TestClient(_app(user=user, handler=_handler()))

        with patch("hestia.api.routers.logs.set_log_level") as mock_set:
            resp = client.put("/logs/settings", json={"log_level": "DEBUG"})

        assert resp.status_code == 403
        mock_set.assert_not_called()
