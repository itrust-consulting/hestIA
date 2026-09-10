from __future__ import annotations

from unittest.mock import MagicMock, patch

from fastapi import FastAPI
from fastapi.testclient import TestClient

from hestia.api.dependencies import get_handler
from hestia.api.error_handlers import register_error_handlers
from hestia.api.routers.account import router
from hestia.api.security import get_current_user
from hestia.domain.exceptions import ForbiddenError, NotFoundError, ValidationError
from tests.unit.conftest import _make_user


def _app(user=None, handler=None):
    app = FastAPI()
    register_error_handlers(app)
    app.include_router(router)
    app.dependency_overrides[get_current_user] = lambda: (user or _make_user())
    app.dependency_overrides[get_handler] = lambda: (handler or MagicMock())
    return app


# ---------------------------------------------------------------------------
# GET /account
# ---------------------------------------------------------------------------

class TestGetAccount:

    def test_returns_profile_for_authenticated_user(self):
        user = _make_user()
        handler = MagicMock()
        users_svc = MagicMock()
        profile = _make_user()
        users_svc.load_user_profile.return_value = profile
        handler.container.services.get.return_value = users_svc

        client = TestClient(_app(user=user, handler=handler))
        resp = client.get("/account")

        assert resp.status_code == 200
        assert resp.json()["username"] == profile.username
        assert resp.json()["id"] == str(profile.id)
        handler.container.services.get.assert_called_once_with("users")
        users_svc.load_user_profile.assert_called_once_with(user.id)

    def test_ignores_any_client_supplied_user_id_and_only_loads_own_profile(self):
        # There is no request body/param the route reads a user id from --
        # it must always come from the auth dependency, never the client.
        user = _make_user()
        handler = MagicMock()
        users_svc = MagicMock()
        users_svc.load_user_profile.return_value = user
        handler.container.services.get.return_value = users_svc

        client = TestClient(_app(user=user, handler=handler))
        resp = client.get("/account", params={"user_id": "11111111-1111-1111-1111-111111111111"})

        assert resp.status_code == 200
        users_svc.load_user_profile.assert_called_once_with(user.id)

    def test_returns_null_body_when_profile_missing(self):
        user = _make_user()
        handler = MagicMock()
        users_svc = MagicMock()
        users_svc.load_user_profile.return_value = None
        handler.container.services.get.return_value = users_svc

        client = TestClient(_app(user=user, handler=handler))
        resp = client.get("/account")

        assert resp.status_code == 200
        assert resp.json() is None


# ---------------------------------------------------------------------------
# PATCH /account/password
# ---------------------------------------------------------------------------

class TestChangePassword:

    def test_missing_current_pw_returns_400(self):
        client = TestClient(_app())
        resp = client.patch("/account/password", json={"new_pw": "newpassword123"})
        assert resp.status_code == 400

    def test_missing_new_pw_returns_400(self):
        client = TestClient(_app())
        resp = client.patch("/account/password", json={"current_pw": "oldpassword123"})
        assert resp.status_code == 400

    def test_missing_both_fields_returns_400(self):
        client = TestClient(_app())
        resp = client.patch("/account/password", json={})
        assert resp.status_code == 400

    def test_empty_string_fields_are_treated_as_missing(self):
        client = TestClient(_app())
        resp = client.patch("/account/password", json={"current_pw": "", "new_pw": ""})
        assert resp.status_code == 400

    def test_happy_path_changes_own_password_and_audits(self):
        user = _make_user()
        handler = MagicMock()
        users_svc = MagicMock()
        handler.container.services.get.return_value = users_svc

        with patch("hestia.api.routers.account.audit") as mock_audit:
            client = TestClient(_app(user=user, handler=handler))
            resp = client.patch(
                "/account/password",
                json={"current_pw": "old-pass", "new_pw": "newpassword123"},
            )

        assert resp.status_code == 200
        assert resp.json() == {"status": "ok"}
        users_svc.change_password.assert_called_once_with(user.id, "old-pass", "newpassword123")
        mock_audit.user_action.assert_called_once_with(
            actor_id=str(user.id), action="password_change", success=True
        )

    def test_only_ever_changes_the_authenticated_users_own_password(self):
        # Even if a client smuggles a different user_id into the body, the
        # route has no field for it -- it always acts on user.id from auth.
        user = _make_user()
        handler = MagicMock()
        users_svc = MagicMock()
        handler.container.services.get.return_value = users_svc

        client = TestClient(_app(user=user, handler=handler))
        resp = client.patch(
            "/account/password",
            json={"current_pw": "old-pass", "new_pw": "newpassword123", "user_id": "someone-else"},
        )

        assert resp.status_code == 200
        users_svc.change_password.assert_called_once_with(user.id, "old-pass", "newpassword123")

    def test_incorrect_current_password_returns_400_from_validation_error(self):
        user = _make_user()
        handler = MagicMock()
        users_svc = MagicMock()
        users_svc.change_password.side_effect = ValidationError("Incorrect current password.")
        handler.container.services.get.return_value = users_svc

        client = TestClient(_app(user=user, handler=handler))
        resp = client.patch(
            "/account/password",
            json={"current_pw": "wrong", "new_pw": "newpassword123"},
        )

        assert resp.status_code == 400
        assert resp.json()["detail"] == "Incorrect current password."

    def test_new_password_too_short_returns_400_from_validation_error(self):
        user = _make_user()
        handler = MagicMock()
        users_svc = MagicMock()
        users_svc.change_password.side_effect = ValidationError(
            "New password must be at least 8 characters."
        )
        handler.container.services.get.return_value = users_svc

        client = TestClient(_app(user=user, handler=handler))
        resp = client.patch(
            "/account/password",
            json={"current_pw": "old-pass", "new_pw": "short"},
        )

        assert resp.status_code == 400

    def test_federated_account_returns_403_from_forbidden_error(self):
        user = _make_user()
        handler = MagicMock()
        users_svc = MagicMock()
        users_svc.change_password.side_effect = ForbiddenError(
            "Federated account — password cannot be changed here."
        )
        handler.container.services.get.return_value = users_svc

        client = TestClient(_app(user=user, handler=handler))
        resp = client.patch(
            "/account/password",
            json={"current_pw": "old-pass", "new_pw": "newpassword123"},
        )

        assert resp.status_code == 403

    def test_user_not_found_returns_404_from_not_found_error(self):
        user = _make_user()
        handler = MagicMock()
        users_svc = MagicMock()
        users_svc.change_password.side_effect = NotFoundError("User not found.")
        handler.container.services.get.return_value = users_svc

        client = TestClient(_app(user=user, handler=handler))
        resp = client.patch(
            "/account/password",
            json={"current_pw": "old-pass", "new_pw": "newpassword123"},
        )

        assert resp.status_code == 404

    def test_failure_emits_audit_log_with_success_false(self):
        user = _make_user()
        handler = MagicMock()
        users_svc = MagicMock()
        users_svc.change_password.side_effect = ValidationError("Incorrect current password.")
        handler.container.services.get.return_value = users_svc

        with patch("hestia.api.routers.account.audit") as mock_audit:
            client = TestClient(_app(user=user, handler=handler))
            client.patch(
                "/account/password",
                json={"current_pw": "wrong", "new_pw": "newpassword123"},
            )

        mock_audit.user_action.assert_called_once_with(
            actor_id=str(user.id), action="password_change", success=False, reason="Incorrect current password."
        )

    def test_unexpected_exception_is_also_audited_and_reraised(self):
        # Regression test: change_password used to only audit failures that
        # were a HestiaError -- an unexpected exception (bad connection,
        # bug) left no audit trail at all, unlike every other mutation's
        # audited() wrapper (admin.py, ingestion.py).
        user = _make_user()
        handler = MagicMock()
        users_svc = MagicMock()
        users_svc.change_password.side_effect = RuntimeError("boom")
        handler.container.services.get.return_value = users_svc

        with patch("hestia.api.routers.account.audit") as mock_audit:
            client = TestClient(_app(user=user, handler=handler), raise_server_exceptions=False)
            resp = client.patch(
                "/account/password",
                json={"current_pw": "old-pass", "new_pw": "newpassword123"},
            )

        assert resp.status_code == 500
        mock_audit.user_action.assert_called_once_with(
            actor_id=str(user.id), action="password_change", success=False, reason="boom"
        )


# ---------------------------------------------------------------------------
# POST /account/heartbeat
# ---------------------------------------------------------------------------

class TestHeartbeat:

    def _handler_with(self, users_svc, notif_svc):
        handler = MagicMock()
        services = {"users": users_svc, "notifications": notif_svc}
        handler.container.services.get.side_effect = lambda name: services.get(name)
        return handler

    def test_touches_last_seen_and_returns_unread_count(self):
        user = _make_user()
        users_svc = MagicMock()
        notif_svc = MagicMock()
        notif_svc.unread_count.return_value = 3
        handler = self._handler_with(users_svc, notif_svc)

        client = TestClient(_app(user=user, handler=handler))
        resp = client.post("/account/heartbeat")

        assert resp.status_code == 200
        assert resp.json() == {"ok": True, "unread_notifications": 3}
        users_svc.repo.touch_last_seen.assert_called_once()
        _, kwargs = users_svc.repo.touch_last_seen.call_args
        assert kwargs["id"] == user.id
        assert isinstance(kwargs["ts"], int)
        notif_svc.unread_count.assert_called_once_with(user.id)

    def test_returns_zero_unread_when_notifications_service_unavailable(self):
        user = _make_user()
        users_svc = MagicMock()
        handler = self._handler_with(users_svc, None)

        client = TestClient(_app(user=user, handler=handler))
        resp = client.post("/account/heartbeat")

        assert resp.status_code == 200
        assert resp.json() == {"ok": True, "unread_notifications": 0}

    def test_only_ever_touches_the_authenticated_users_own_last_seen(self):
        user = _make_user()
        users_svc = MagicMock()
        notif_svc = MagicMock()
        notif_svc.unread_count.return_value = 0
        handler = self._handler_with(users_svc, notif_svc)

        client = TestClient(_app(user=user, handler=handler))
        client.post("/account/heartbeat")

        _, kwargs = users_svc.repo.touch_last_seen.call_args
        assert kwargs["id"] == user.id
        notif_svc.unread_count.assert_called_once_with(user.id)
