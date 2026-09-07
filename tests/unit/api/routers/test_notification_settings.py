from __future__ import annotations

from unittest.mock import MagicMock, patch

from fastapi import FastAPI
from fastapi.testclient import TestClient

from hestia.api.dependencies import get_handler
from hestia.api.error_handlers import register_error_handlers
from hestia.api.routers.notification_settings import router
from hestia.api.security import get_current_user
from hestia.domain.exceptions import ValidationError
from tests.unit.conftest import _make_user


def _app(user=None, handler=None, with_error_handlers=False):
    app = FastAPI()
    app.include_router(router)
    app.dependency_overrides[get_current_user] = lambda: (user or _make_user(is_admin=True))
    app.dependency_overrides[get_handler] = lambda: (handler or MagicMock())
    if with_error_handlers:
        # Mirrors hestia.main's real wiring -- needed only for the one test
        # that exercises the domain ValidationError -> HTTP 400 mapping,
        # since this endpoint lets that error propagate to the global handler
        # rather than catching it itself.
        register_error_handlers(app)
    return app


# ---------------------------------------------------------------------------
# GET /notification-settings
# ---------------------------------------------------------------------------

class TestGetNotificationSettings:

    def test_admin_gets_settings(self):
        handler = MagicMock()
        svc = MagicMock()
        svc.get_welcome_settings.return_value = {"welcome_title": "Hi", "welcome_body": "Body"}
        handler.container.services.get.return_value = svc

        client = TestClient(_app(handler=handler))
        resp = client.get("/notification-settings")

        assert resp.status_code == 200
        assert resp.json() == {"welcome_title": "Hi", "welcome_body": "Body"}
        handler.container.services.get.assert_called_once_with("notifications")
        svc.get_welcome_settings.assert_called_once_with()

    def test_non_admin_gets_403(self):
        user = _make_user(is_admin=False)
        handler = MagicMock()
        client = TestClient(_app(user=user, handler=handler))

        resp = client.get("/notification-settings")

        assert resp.status_code == 403
        handler.container.services.get.assert_not_called()

    def test_service_unavailable_returns_503(self):
        handler = MagicMock()
        handler.container.services.get.return_value = None
        client = TestClient(_app(handler=handler))

        resp = client.get("/notification-settings")

        assert resp.status_code == 503


# ---------------------------------------------------------------------------
# PUT /notification-settings
# ---------------------------------------------------------------------------

class TestUpdateNotificationSettings:

    def test_admin_updates_settings(self):
        handler = MagicMock()
        svc = MagicMock()
        handler.container.services.get.return_value = svc

        client = TestClient(_app(handler=handler))
        resp = client.put(
            "/notification-settings",
            json={"welcome_title": "New Title", "welcome_body": "New Body"},
        )

        assert resp.status_code == 200
        assert resp.json() == {"ok": True}
        svc.update_welcome_settings.assert_called_once_with(
            welcome_title="New Title", welcome_body="New Body",
        )

    def test_missing_fields_default_to_empty_string(self):
        handler = MagicMock()
        svc = MagicMock()
        handler.container.services.get.return_value = svc

        client = TestClient(_app(handler=handler))
        resp = client.put("/notification-settings", json={})

        assert resp.status_code == 200
        svc.update_welcome_settings.assert_called_once_with(welcome_title="", welcome_body="")

    def test_non_admin_gets_403(self):
        user = _make_user(is_admin=False)
        handler = MagicMock()
        client = TestClient(_app(user=user, handler=handler))

        resp = client.put(
            "/notification-settings",
            json={"welcome_title": "x", "welcome_body": "y"},
        )

        assert resp.status_code == 403
        handler.container.services.get.assert_not_called()

    def test_service_unavailable_returns_503(self):
        handler = MagicMock()
        handler.container.services.get.return_value = None
        client = TestClient(_app(handler=handler))

        resp = client.put(
            "/notification-settings",
            json={"welcome_title": "x", "welcome_body": "y"},
        )

        assert resp.status_code == 503

    def test_validation_error_from_service_becomes_400(self):
        # update_welcome_settings raises ValidationError for a blank title;
        # the router doesn't catch it itself, so the global error handler
        # (registered in the real app via hestia.main) is what turns it into
        # a 400 -- register it here to exercise that same real contract.
        handler = MagicMock()
        svc = MagicMock()
        svc.update_welcome_settings.side_effect = ValidationError("Welcome title required.")
        handler.container.services.get.return_value = svc

        client = TestClient(_app(handler=handler, with_error_handlers=True))
        resp = client.put(
            "/notification-settings",
            json={"welcome_title": "", "welcome_body": "y"},
        )

        assert resp.status_code == 400
        assert resp.json()["detail"] == "Welcome title required."

    def test_audit_action_recorded_on_success(self):
        handler = MagicMock()
        svc = MagicMock()
        handler.container.services.get.return_value = svc
        user = _make_user(is_admin=True)

        client = TestClient(_app(user=user, handler=handler))
        with patch("hestia.api.routers.notification_settings.audit") as mock_audit:
            resp = client.put(
                "/notification-settings",
                json={"welcome_title": "x", "welcome_body": "y"},
            )

        assert resp.status_code == 200
        mock_audit.admin_action.assert_called_once()
        kwargs = mock_audit.admin_action.call_args.kwargs
        assert kwargs["actor_id"] == str(user.id)
        assert kwargs["action"] == "notification_settings_update"
        assert kwargs["target"] == "welcome_message"

    def test_audit_not_recorded_when_update_fails(self):
        handler = MagicMock()
        svc = MagicMock()
        svc.update_welcome_settings.side_effect = ValidationError("Welcome body required.")
        handler.container.services.get.return_value = svc

        client = TestClient(_app(handler=handler, with_error_handlers=True))
        with patch("hestia.api.routers.notification_settings.audit") as mock_audit:
            resp = client.put(
                "/notification-settings",
                json={"welcome_title": "x", "welcome_body": ""},
            )

        assert resp.status_code == 400
        mock_audit.admin_action.assert_not_called()
