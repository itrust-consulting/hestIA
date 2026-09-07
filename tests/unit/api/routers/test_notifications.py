from __future__ import annotations

import uuid
from unittest.mock import MagicMock

from fastapi import FastAPI
from fastapi.testclient import TestClient

from hestia.api.dependencies import get_handler
from hestia.api.error_handlers import register_error_handlers
from hestia.api.routers.notifications import router
from hestia.api.security import get_current_user
from tests.unit.conftest import _make_user


def _app(user=None, handler=None):
    app = FastAPI()
    app.include_router(router)
    app.dependency_overrides[get_current_user] = lambda: (user or _make_user(is_admin=True))
    app.dependency_overrides[get_handler] = lambda: (handler or MagicMock())
    # Mirrors hestia.main's real wiring -- some endpoints (e.g. invalid
    # uuid.UUID(...) parsing) let a bare ValueError propagate to the global
    # handler rather than catching it themselves.
    register_error_handlers(app)
    return app


def _handler_with_svc(svc):
    handler = MagicMock()
    handler.container.services.get.return_value = svc
    return handler


# ---------------------------------------------------------------------------
# _notification_svc helper (service-unavailable path), exercised through
# each endpoint that depends on it.
# ---------------------------------------------------------------------------

class TestNotificationServiceUnavailable:

    def test_list_notifications_returns_503_when_service_missing(self):
        handler = _handler_with_svc(None)
        client = TestClient(_app(handler=handler))

        resp = client.get("/notifications")

        assert resp.status_code == 503


# ---------------------------------------------------------------------------
# GET /notifications
# ---------------------------------------------------------------------------

class TestListNotifications:

    def test_returns_service_result_with_query_params(self):
        svc = MagicMock()
        svc.list_notifications.return_value = {"notifications": [], "has_more": False, "next_cursor": None}
        handler = _handler_with_svc(svc)
        user = _make_user()
        client = TestClient(_app(user=user, handler=handler))

        resp = client.get("/notifications", params={"limit": 5, "before_created_at": 100, "before_rowid": 2})

        assert resp.status_code == 200
        assert resp.json() == {"notifications": [], "has_more": False, "next_cursor": None}
        svc.list_notifications.assert_called_once_with(
            user.id, limit=5, before_created_at=100, before_rowid=2,
        )

    def test_default_query_params(self):
        svc = MagicMock()
        svc.list_notifications.return_value = {"notifications": [], "has_more": False, "next_cursor": None}
        handler = _handler_with_svc(svc)
        user = _make_user()
        client = TestClient(_app(user=user, handler=handler))

        resp = client.get("/notifications")

        assert resp.status_code == 200
        svc.list_notifications.assert_called_once_with(
            user.id, limit=20, before_created_at=None, before_rowid=None,
        )


# ---------------------------------------------------------------------------
# POST /notifications/{notification_id}/read
# ---------------------------------------------------------------------------

class TestMarkNotificationRead:

    def test_marks_read(self):
        svc = MagicMock()
        handler = _handler_with_svc(svc)
        user = _make_user()
        notif_id = uuid.uuid4()
        client = TestClient(_app(user=user, handler=handler))

        resp = client.post(f"/notifications/{notif_id}/read")

        assert resp.status_code == 200
        assert resp.json() == {"ok": True}
        svc.mark_read.assert_called_once_with(notif_id, user.id)

    def test_invalid_uuid_returns_error(self):
        svc = MagicMock()
        handler = _handler_with_svc(svc)
        client = TestClient(_app(handler=handler))

        resp = client.post("/notifications/not-a-uuid/read")

        assert resp.status_code == 400
        svc.mark_read.assert_not_called()


# ---------------------------------------------------------------------------
# POST /notifications/read-all
# ---------------------------------------------------------------------------

class TestMarkAllNotificationsRead:

    def test_marks_all_read(self):
        svc = MagicMock()
        handler = _handler_with_svc(svc)
        user = _make_user()
        client = TestClient(_app(user=user, handler=handler))

        resp = client.post("/notifications/read-all")

        assert resp.status_code == 200
        assert resp.json() == {"ok": True}
        svc.mark_all_read.assert_called_once_with(user.id)


# ---------------------------------------------------------------------------
# GET /organizations/browse
# ---------------------------------------------------------------------------

class TestBrowseOrganizations:

    def test_returns_organizations(self):
        svc = MagicMock()
        svc.browse_organizations.return_value = [{"id": 1, "name": "Acme", "abbreviation": "ACM"}]
        handler = _handler_with_svc(svc)
        client = TestClient(_app(handler=handler))

        resp = client.get("/organizations/browse")

        assert resp.status_code == 200
        assert resp.json() == {"organizations": [{"id": 1, "name": "Acme", "abbreviation": "ACM"}]}


# ---------------------------------------------------------------------------
# GET /organizations/{org_id}/summary
# ---------------------------------------------------------------------------

class TestGetOrganizationSummary:

    def test_org_member_gets_summary(self):
        user = _make_user()
        user.orgs = [{"id": 1}]
        users_svc = MagicMock()
        users_svc.get_tenant_summary.return_value = {"id": 1, "name": "Acme"}
        handler = MagicMock()
        handler.container.services.get.return_value = users_svc
        client = TestClient(_app(user=user, handler=handler))

        resp = client.get("/organizations/1/summary")

        assert resp.status_code == 200
        assert resp.json() == {"id": 1, "name": "Acme"}
        users_svc.get_tenant_summary.assert_called_once_with(1, user.id)

    def test_non_member_gets_403(self):
        user = _make_user()
        user.orgs = []
        handler = MagicMock()
        client = TestClient(_app(user=user, handler=handler))

        resp = client.get("/organizations/1/summary")

        assert resp.status_code == 403
        handler.container.services.get.assert_not_called()

    def test_admin_bypasses_membership_check(self):
        user = _make_user(is_admin=True)
        users_svc = MagicMock()
        users_svc.get_tenant_summary.return_value = {"id": 1}
        handler = MagicMock()
        handler.container.services.get.return_value = users_svc
        client = TestClient(_app(user=user, handler=handler))

        resp = client.get("/organizations/1/summary")

        assert resp.status_code == 200

    def test_users_service_unavailable_returns_503(self):
        user = _make_user(is_admin=True)
        handler = MagicMock()
        handler.container.services.get.return_value = None
        client = TestClient(_app(user=user, handler=handler))

        resp = client.get("/organizations/1/summary")

        assert resp.status_code == 503


# ---------------------------------------------------------------------------
# POST /organizations/{org_id}/join-requests
# ---------------------------------------------------------------------------

class TestFileJoinRequest:

    def test_files_request_with_message(self):
        svc = MagicMock()
        req_id = uuid.uuid4()
        svc.file_join_request.return_value = req_id
        handler = _handler_with_svc(svc)
        user = _make_user()
        client = TestClient(_app(user=user, handler=handler))

        resp = client.post("/organizations/1/join-requests", json={"message": "let me in"})

        assert resp.status_code == 200
        assert resp.json() == {"ok": True, "request_id": str(req_id)}
        svc.file_join_request.assert_called_once_with(user.id, 1, message="let me in")

    def test_blank_message_becomes_none(self):
        svc = MagicMock()
        svc.file_join_request.return_value = uuid.uuid4()
        handler = _handler_with_svc(svc)
        user = _make_user()
        client = TestClient(_app(user=user, handler=handler))

        resp = client.post("/organizations/1/join-requests", json={"message": ""})

        assert resp.status_code == 200
        svc.file_join_request.assert_called_once_with(user.id, 1, message=None)


# ---------------------------------------------------------------------------
# GET /account/join-requests
# ---------------------------------------------------------------------------

class TestGetMyJoinRequests:

    def test_returns_requests(self):
        svc = MagicMock()
        svc.list_user_join_requests.return_value = [{"id": "1"}]
        handler = _handler_with_svc(svc)
        user = _make_user()
        client = TestClient(_app(user=user, handler=handler))

        resp = client.get("/account/join-requests")

        assert resp.status_code == 200
        assert resp.json() == {"requests": [{"id": "1"}]}
        svc.list_user_join_requests.assert_called_once_with(user.id)


# ---------------------------------------------------------------------------
# GET /account/invitations
# ---------------------------------------------------------------------------

class TestGetMyInvitations:

    def test_returns_invitations_with_status_filter(self):
        svc = MagicMock()
        svc.list_user_invitations.return_value = [{"id": "1"}]
        handler = _handler_with_svc(svc)
        user = _make_user()
        client = TestClient(_app(user=user, handler=handler))

        resp = client.get("/account/invitations", params={"status": "pending"})

        assert resp.status_code == 200
        assert resp.json() == {"invitations": [{"id": "1"}]}
        svc.list_user_invitations.assert_called_once_with(user.id, status="pending")

    def test_default_status_is_none(self):
        svc = MagicMock()
        svc.list_user_invitations.return_value = []
        handler = _handler_with_svc(svc)
        user = _make_user()
        client = TestClient(_app(user=user, handler=handler))

        resp = client.get("/account/invitations")

        assert resp.status_code == 200
        svc.list_user_invitations.assert_called_once_with(user.id, status=None)


# ---------------------------------------------------------------------------
# POST /account/invitations/{inv_id}/accept
# ---------------------------------------------------------------------------

class TestAcceptInvitation:

    def test_accepts_invitation(self):
        svc = MagicMock()
        handler = _handler_with_svc(svc)
        user = _make_user()
        inv_id = uuid.uuid4()
        client = TestClient(_app(user=user, handler=handler))

        resp = client.post(f"/account/invitations/{inv_id}/accept")

        assert resp.status_code == 200
        assert resp.json() == {"ok": True}
        svc.accept_invitation.assert_called_once_with(inv_id, user.id)


# ---------------------------------------------------------------------------
# POST /account/invitations/{inv_id}/decline
# ---------------------------------------------------------------------------

class TestDeclineInvitation:

    def test_declines_invitation(self):
        svc = MagicMock()
        handler = _handler_with_svc(svc)
        user = _make_user()
        inv_id = uuid.uuid4()
        client = TestClient(_app(user=user, handler=handler))

        resp = client.post(f"/account/invitations/{inv_id}/decline")

        assert resp.status_code == 200
        assert resp.json() == {"ok": True}
        svc.decline_invitation.assert_called_once_with(inv_id, user.id)
