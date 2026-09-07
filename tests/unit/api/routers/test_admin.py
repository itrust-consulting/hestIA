from __future__ import annotations

import uuid
from unittest.mock import MagicMock, patch

from fastapi import FastAPI
from fastapi.testclient import TestClient

from hestia.api.routers.admin import router
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


def _client(user=None, handler=None):
    return TestClient(_app(user=user, handler=handler))


def _handler(services: dict | None = None, providers: dict | None = None):
    """Build a MagicMock handler whose container.services.get(name) and
    container.providers[...]/.get(...) resolve from plain dicts (so both
    subscript and .get access patterns used by admin.py work naturally)."""
    h = MagicMock()
    services = dict(services or {})
    h.container.services.get.side_effect = lambda name, _s=services: _s.get(name)
    h.container.providers = dict(providers or {})
    return h


# We patch count_failed_logins everywhere it's used (get_user_profile) so no
# real filesystem log scan happens and results are deterministic.
FAILED_LOGINS_PATCH = "hestia.api.routers.admin.count_failed_logins"


# ---------------------------------------------------------------------------
# GET /users
# ---------------------------------------------------------------------------

class TestGetUsers:
    def test_admin_lists_all_users(self):
        users_svc = MagicMock()
        users_svc.list_users.return_value = [
            {"id": uuid.uuid4(), "username": "a", "last_seen_at": None},
        ]
        h = _handler({"users": users_svc})
        resp = _client(user=_make_user(is_admin=True), handler=h).get("/users")
        assert resp.status_code == 200
        data = resp.json()["users"]
        assert len(data) == 1
        assert data[0]["is_online"] is False

    def test_moderator_gets_deduped_org_users(self):
        users_svc = MagicMock()
        uid = uuid.uuid4()
        users_svc.get_org_users.side_effect = lambda org_id: [{"id": uid, "username": "shared", "last_seen_at": None}]
        h = _handler({"users": users_svc})
        user = _make_user(moderated_tenants=[1, 2])
        resp = _client(user=user, handler=h).get("/users")
        assert resp.status_code == 200
        data = resp.json()["users"]
        # deduplicated across the two moderated tenants
        assert len(data) == 1
        assert users_svc.get_org_users.call_count == 2

    def test_online_flag_true_for_recent_last_seen(self):
        import time
        now_ms = int(time.time() * 1000)
        users_svc = MagicMock()
        users_svc.list_users.return_value = [{"id": uuid.uuid4(), "username": "a", "last_seen_at": now_ms}]
        h = _handler({"users": users_svc})
        resp = _client(user=_make_user(is_admin=True), handler=h).get("/users")
        assert resp.json()["users"][0]["is_online"] is True

    def test_plain_user_forbidden(self):
        h = _handler({"users": MagicMock()})
        resp = _client(user=_make_user(), handler=h).get("/users")
        assert resp.status_code == 403


# ---------------------------------------------------------------------------
# GET /users/user/{uid}
# ---------------------------------------------------------------------------

class TestGetUserProfile:
    def test_returns_profile_with_activity_and_failed_logins(self):
        uid = uuid.uuid4()
        profile = MagicMock()
        profile.model_dump.return_value = {"id": str(uid), "username": "bob"}
        profile.username = "bob"
        users_svc = MagicMock()
        users_svc.load_user_profile.return_value = profile
        users_svc.get_user_activity.return_value = {"conversations": 3}
        h = _handler({"users": users_svc})
        with patch(FAILED_LOGINS_PATCH, return_value={"bob": 2}):
            resp = _client(user=_make_user(is_admin=True), handler=h).get(f"/users/user/{uid}")
        assert resp.status_code == 200
        data = resp.json()
        assert data["username"] == "bob"
        assert data["conversations"] == 3
        assert data["failed_logins_7d"] == 2

    def test_not_found_returns_404(self):
        users_svc = MagicMock()
        users_svc.load_user_profile.return_value = None
        h = _handler({"users": users_svc})
        with patch(FAILED_LOGINS_PATCH, return_value={}):
            resp = _client(user=_make_user(is_admin=True), handler=h).get(f"/users/user/{uuid.uuid4()}")
        assert resp.status_code == 404

    def test_non_admin_forbidden(self):
        h = _handler({"users": MagicMock()})
        resp = _client(user=_make_user(), handler=h).get(f"/users/user/{uuid.uuid4()}")
        assert resp.status_code == 403


# ---------------------------------------------------------------------------
# PATCH /users/user/{uid}
# ---------------------------------------------------------------------------

class TestUpdateUser:
    def test_admin_updates_user(self):
        users_svc = MagicMock()
        h = _handler({"users": users_svc})
        uid = uuid.uuid4()
        resp = _client(user=_make_user(is_admin=True), handler=h).patch(
            f"/users/user/{uid}",
            json={"username": "new", "email": "e@x.com", "first_name": "F", "last_name": "L",
                  "expires_at": None, "role_ids": [1], "new_password": "pw"},
        )
        assert resp.status_code == 200
        assert resp.json() == {"ok": True}
        users_svc.update_user.assert_called_once_with(
            uid, username="new", email="e@x.com", first_name="F", last_name="L",
            expires_at=None, role_ids=[1], new_password="pw",
        )

    def test_empty_new_password_passed_as_none(self):
        users_svc = MagicMock()
        h = _handler({"users": users_svc})
        uid = uuid.uuid4()
        resp = _client(user=_make_user(is_admin=True), handler=h).patch(
            f"/users/user/{uid}", json={"new_password": ""},
        )
        assert resp.status_code == 200
        _, kwargs = users_svc.update_user.call_args
        assert kwargs["new_password"] is None

    def test_non_admin_forbidden(self):
        h = _handler({"users": MagicMock()})
        resp = _client(user=_make_user(), handler=h).patch(f"/users/user/{uuid.uuid4()}", json={})
        assert resp.status_code == 403


# ---------------------------------------------------------------------------
# DELETE /users/user/{uid}
# ---------------------------------------------------------------------------

class TestDeleteUser:
    def test_admin_deletes_user(self):
        users_svc = MagicMock()
        h = _handler({"users": users_svc})
        uid = uuid.uuid4()
        resp = _client(user=_make_user(is_admin=True), handler=h).delete(f"/users/user/{uid}")
        assert resp.status_code == 200
        users_svc.delete_user.assert_called_once_with(uid)

    def test_non_admin_forbidden(self):
        h = _handler({"users": MagicMock()})
        resp = _client(user=_make_user(), handler=h).delete(f"/users/user/{uuid.uuid4()}")
        assert resp.status_code == 403


# ---------------------------------------------------------------------------
# POST /users/create
# ---------------------------------------------------------------------------

class TestCreateUser:
    def _payload(self, **overrides):
        payload = {
            "username": "newuser", "email": "n@x.com", "first_name": "N", "last_name": "U",
            "password": "secret", "roles": [0], "organization": None, "expires_at": None,
        }
        payload.update(overrides)
        return payload

    def test_admin_creates_user(self):
        users_svc = MagicMock()
        users_svc.create_user.return_value = uuid.uuid4()
        h = _handler({"users": users_svc})
        resp = _client(user=_make_user(is_admin=True), handler=h).post("/users/create", json=self._payload())
        assert resp.status_code == 200
        data = resp.json()
        assert data["ok"] is True
        assert "user_id" in data

    def test_missing_username_returns_400(self):
        h = _handler({"users": MagicMock()})
        resp = _client(user=_make_user(is_admin=True), handler=h).post(
            "/users/create", json=self._payload(username="")
        )
        assert resp.status_code == 400

    def test_missing_password_returns_400(self):
        h = _handler({"users": MagicMock()})
        resp = _client(user=_make_user(is_admin=True), handler=h).post(
            "/users/create", json=self._payload(password="")
        )
        assert resp.status_code == 400

    def test_non_admin_forbidden(self):
        h = _handler({"users": MagicMock()})
        resp = _client(user=_make_user(), handler=h).post("/users/create", json=self._payload())
        assert resp.status_code == 403


# ---------------------------------------------------------------------------
# GET /organizations, /organizations/list
# ---------------------------------------------------------------------------

class TestListOrganizations:
    def test_admin_lists_orgs(self):
        users_svc = MagicMock()
        users_svc.list_orgs.return_value = [{"id": 1, "name": "Org"}]
        h = _handler({"users": users_svc})
        resp = _client(user=_make_user(is_admin=True), handler=h).get("/organizations")
        assert resp.status_code == 200
        assert resp.json()["organizations"] == [{"id": 1, "name": "Org"}]

    def test_alias_route(self):
        users_svc = MagicMock()
        users_svc.list_orgs.return_value = []
        h = _handler({"users": users_svc})
        resp = _client(user=_make_user(is_admin=True), handler=h).get("/organizations/list")
        assert resp.status_code == 200
        assert resp.json()["organizations"] == []

    def test_no_users_service_returns_empty_list(self):
        h = _handler({})
        resp = _client(user=_make_user(is_admin=True), handler=h).get("/organizations")
        assert resp.status_code == 200
        assert resp.json()["organizations"] == []

    def test_alias_route_no_users_service_returns_empty_list(self):
        h = _handler({})
        resp = _client(user=_make_user(is_admin=True), handler=h).get("/organizations/list")
        assert resp.status_code == 200
        assert resp.json()["organizations"] == []

    def test_moderator_allowed(self):
        users_svc = MagicMock()
        users_svc.list_orgs.return_value = []
        h = _handler({"users": users_svc})
        resp = _client(user=_make_user(moderated_tenants=[1]), handler=h).get("/organizations")
        assert resp.status_code == 200

    def test_plain_user_forbidden(self):
        h = _handler({"users": MagicMock()})
        resp = _client(user=_make_user(), handler=h).get("/organizations")
        assert resp.status_code == 403


# ---------------------------------------------------------------------------
# POST /organizations/create
# ---------------------------------------------------------------------------

class TestCreateOrganization:
    def test_admin_creates_org(self):
        users_svc = MagicMock()
        h = _handler({"users": users_svc})
        resp = _client(user=_make_user(is_admin=True), handler=h).post(
            "/organizations/create", json={"name": "Acme", "abbreviation": "AC"}
        )
        assert resp.status_code == 200
        users_svc.create_org.assert_called_once_with(name="Acme", abbreviation="AC")

    def test_missing_name_returns_400(self):
        h = _handler({"users": MagicMock()})
        resp = _client(user=_make_user(is_admin=True), handler=h).post(
            "/organizations/create", json={"name": "", "abbreviation": "AC"}
        )
        assert resp.status_code == 400

    def test_missing_abbreviation_returns_400(self):
        h = _handler({"users": MagicMock()})
        resp = _client(user=_make_user(is_admin=True), handler=h).post(
            "/organizations/create", json={"name": "Acme", "abbreviation": ""}
        )
        assert resp.status_code == 400

    def test_name_or_abbreviation_collision_returns_409_not_a_false_ok(self):
        # create_org returning False means the INSERT OR IGNORE silently
        # no-op'd against an existing tenant of that name/abbreviation --
        # this must surface as a real conflict, not a misleading {"ok": true}.
        users_svc = MagicMock()
        users_svc.create_org.return_value = False
        h = _handler({"users": users_svc})
        resp = _client(user=_make_user(is_admin=True), handler=h).post(
            "/organizations/create", json={"name": "Acme", "abbreviation": "AC"}
        )
        assert resp.status_code == 409

    def test_non_admin_forbidden(self):
        h = _handler({"users": MagicMock()})
        resp = _client(user=_make_user(), handler=h).post(
            "/organizations/create", json={"name": "Acme", "abbreviation": "AC"}
        )
        assert resp.status_code == 403


# ---------------------------------------------------------------------------
# PUT /organizations/{org_id}
# ---------------------------------------------------------------------------

class TestUpdateOrganization:
    def test_admin_updates_org(self):
        users_svc = MagicMock()
        h = _handler({"users": users_svc})
        resp = _client(user=_make_user(is_admin=True), handler=h).put(
            "/organizations/1", json={"name": "New", "abbreviation": "NW"}
        )
        assert resp.status_code == 200
        users_svc.update_org.assert_called_once_with(org_id=1, name="New", abbreviation="NW")

    def test_missing_fields_returns_400(self):
        h = _handler({"users": MagicMock()})
        resp = _client(user=_make_user(is_admin=True), handler=h).put(
            "/organizations/1", json={"name": "", "abbreviation": ""}
        )
        assert resp.status_code == 400

    def test_non_admin_forbidden(self):
        h = _handler({"users": MagicMock()})
        resp = _client(user=_make_user(), handler=h).put(
            "/organizations/1", json={"name": "New", "abbreviation": "NW"}
        )
        assert resp.status_code == 403


# ---------------------------------------------------------------------------
# DELETE /organizations/{org_id}
# ---------------------------------------------------------------------------

class TestDeleteOrganization:
    def test_admin_deletes_org(self):
        users_svc = MagicMock()
        h = _handler({"users": users_svc})
        resp = _client(user=_make_user(is_admin=True), handler=h).delete("/organizations/1")
        assert resp.status_code == 200
        users_svc.delete_org.assert_called_once_with(org_id=1)

    def test_non_admin_forbidden(self):
        h = _handler({"users": MagicMock()})
        resp = _client(user=_make_user(), handler=h).delete("/organizations/1")
        assert resp.status_code == 403


# ---------------------------------------------------------------------------
# GET/POST/DELETE /organizations/{org_id}/members[...]
# ---------------------------------------------------------------------------

class TestOrganizationMembers:
    def test_get_members_as_tenant_moderator(self):
        users_svc = MagicMock()
        users_svc.get_org_users.return_value = [{"id": uuid.uuid4()}]
        h = _handler({"users": users_svc})
        resp = _client(user=_make_user(moderated_tenants=[1]), handler=h).get("/organizations/1/members")
        assert resp.status_code == 200
        assert len(resp.json()["members"]) == 1

    def test_get_members_forbidden_for_non_moderator(self):
        h = _handler({"users": MagicMock()})
        resp = _client(user=_make_user(moderated_tenants=[2]), handler=h).get("/organizations/1/members")
        assert resp.status_code == 403

    def test_add_member(self):
        users_svc = MagicMock()
        h = _handler({"users": users_svc})
        uid = uuid.uuid4()
        resp = _client(user=_make_user(moderated_tenants=[1]), handler=h).post(f"/organizations/1/members/{uid}")
        assert resp.status_code == 200
        users_svc.add_user_to_org.assert_called_once_with(user_id=uid, org_id=1)

    def test_add_member_forbidden(self):
        h = _handler({"users": MagicMock()})
        resp = _client(user=_make_user(), handler=h).post(f"/organizations/1/members/{uuid.uuid4()}")
        assert resp.status_code == 403

    def test_remove_member(self):
        users_svc = MagicMock()
        h = _handler({"users": users_svc})
        uid = uuid.uuid4()
        resp = _client(user=_make_user(is_admin=True), handler=h).delete(f"/organizations/1/members/{uid}")
        assert resp.status_code == 200
        users_svc.remove_user_from_org.assert_called_once_with(user_id=uid, org_id=1)

    def test_remove_member_forbidden(self):
        h = _handler({"users": MagicMock()})
        resp = _client(user=_make_user(), handler=h).delete(f"/organizations/1/members/{uuid.uuid4()}")
        assert resp.status_code == 403


# ---------------------------------------------------------------------------
# GET /organizations/{org_id}/collections
# ---------------------------------------------------------------------------

class TestGetTenantCollections:
    def test_returns_owned_and_accessible_with_metadata(self):
        users_svc = MagicMock()
        users_svc.get_tenant_collection_info.return_value = {
            "owned": [{"id": "col1"}],
            "accessible": [{"id": "col2"}],
        }
        db = MagicMock()
        db.collections = {"collections": [
            {"name": "col1", "points_count": 10, "status": "green"},
            {"name": "col2", "points_count": 5, "status": "yellow"},
        ]}
        h = _handler({"users": users_svc}, providers={"db": db})
        resp = _client(user=_make_user(moderated_tenants=[1]), handler=h).get("/organizations/1/collections")
        assert resp.status_code == 200
        data = resp.json()
        assert data["owned"][0]["points_count"] == 10
        assert data["accessible"][0]["status"] == "yellow"

    def test_missing_db_meta_defaults_gracefully(self):
        users_svc = MagicMock()
        users_svc.get_tenant_collection_info.return_value = {"owned": [{"id": "colX"}], "accessible": []}
        h = _handler({"users": users_svc}, providers={})
        resp = _client(user=_make_user(is_admin=True), handler=h).get("/organizations/1/collections")
        assert resp.status_code == 200
        assert resp.json()["owned"][0]["points_count"] == 0
        assert resp.json()["owned"][0]["status"] == "unknown"

    def test_forbidden_for_non_moderator(self):
        h = _handler({"users": MagicMock()})
        resp = _client(user=_make_user(moderated_tenants=[2]), handler=h).get("/organizations/1/collections")
        assert resp.status_code == 403


# ---------------------------------------------------------------------------
# PUT /organizations/{org_id}/collections/{collection_id}
# ---------------------------------------------------------------------------

class TestAddTenantCollection:
    def test_invalid_role_returns_400(self):
        h = _handler({"users": MagicMock()})
        resp = _client(user=_make_user(is_admin=True), handler=h).put(
            "/organizations/1/collections/col1", json={"role": "bogus"}
        )
        assert resp.status_code == 400

    def test_owner_role_requires_admin(self):
        h = _handler({"users": MagicMock()})
        resp = _client(user=_make_user(moderated_tenants=[1]), handler=h).put(
            "/organizations/1/collections/col1", json={"role": "owner"}
        )
        assert resp.status_code == 403

    def test_owner_role_as_admin_updates_db_owner(self):
        users_svc = MagicMock()
        db = MagicMock()
        h = _handler({"users": users_svc}, providers={"db": db})
        resp = _client(user=_make_user(is_admin=True), handler=h).put(
            "/organizations/1/collections/col1", json={"role": "owner", "max_classification": 2}
        )
        assert resp.status_code == 200
        users_svc.add_tenant_collection.assert_called_once_with(1, "col1", role="owner", max_classification=2)
        db.update_collection_owner.assert_called_once_with("col1", 1)

    def test_owner_role_as_admin_when_no_db_provider_skips_owner_update(self):
        users_svc = MagicMock()
        h = _handler({"users": users_svc}, providers={})
        resp = _client(user=_make_user(is_admin=True), handler=h).put(
            "/organizations/1/collections/col1", json={"role": "owner"}
        )
        assert resp.status_code == 200
        users_svc.add_tenant_collection.assert_called_once_with(1, "col1", role="owner", max_classification=None)

    def test_access_role_uses_collection_moderator_check(self):
        users_svc = MagicMock()
        users_svc.get_collection_grants.return_value = {"owner": {"id": 1}}
        h = _handler({"users": users_svc})
        resp = _client(user=_make_user(moderated_tenants=[1]), handler=h).put(
            "/organizations/1/collections/col1", json={"role": "access"}
        )
        assert resp.status_code == 200
        users_svc.add_tenant_collection.assert_called_once_with(1, "col1", role="access", max_classification=None)

    def test_access_role_forbidden_when_not_collection_moderator(self):
        users_svc = MagicMock()
        users_svc.get_collection_grants.return_value = {"owner": {"id": 99}}
        h = _handler({"users": users_svc})
        resp = _client(user=_make_user(moderated_tenants=[1]), handler=h).put(
            "/organizations/1/collections/col1", json={"role": "access"}
        )
        assert resp.status_code == 403

    def test_default_role_is_access(self):
        users_svc = MagicMock()
        users_svc.get_collection_grants.return_value = {"owner": {"id": 1}}
        h = _handler({"users": users_svc})
        resp = _client(user=_make_user(moderated_tenants=[1]), handler=h).put(
            "/organizations/1/collections/col1", json={}
        )
        assert resp.status_code == 200
        users_svc.add_tenant_collection.assert_called_once_with(1, "col1", role="access", max_classification=None)


# ---------------------------------------------------------------------------
# DELETE /organizations/{org_id}/collections/{collection_id}
# ---------------------------------------------------------------------------

class TestRemoveTenantCollection:
    def test_removes_when_collection_moderator(self):
        users_svc = MagicMock()
        users_svc.get_collection_grants.return_value = {"owner": {"id": 1}}
        h = _handler({"users": users_svc})
        resp = _client(user=_make_user(moderated_tenants=[1]), handler=h).delete("/organizations/1/collections/col1")
        assert resp.status_code == 200
        users_svc.remove_tenant_collection.assert_called_once_with(1, "col1")

    def test_forbidden_when_not_collection_moderator(self):
        users_svc = MagicMock()
        users_svc.get_collection_grants.return_value = {"owner": {"id": 99}}
        h = _handler({"users": users_svc})
        resp = _client(user=_make_user(moderated_tenants=[1]), handler=h).delete("/organizations/1/collections/col1")
        assert resp.status_code == 403

    def test_service_unavailable_returns_503(self):
        h = _handler({"users": None})
        resp = _client(user=_make_user(moderated_tenants=[1]), handler=h).delete("/organizations/1/collections/col1")
        assert resp.status_code == 503


# ---------------------------------------------------------------------------
# PATCH /organizations/{org_id}/members/{user_id}/classification
# ---------------------------------------------------------------------------

class TestSetMemberClassification:
    def test_sets_level(self):
        users_svc = MagicMock()
        h = _handler({"users": users_svc})
        uid = uuid.uuid4()
        resp = _client(user=_make_user(moderated_tenants=[1]), handler=h).patch(
            f"/organizations/1/members/{uid}/classification", json={"level": 3}
        )
        assert resp.status_code == 200
        users_svc.set_member_classification.assert_called_once_with(uid, 1, 3)

    def test_defaults_to_zero_when_absent(self):
        users_svc = MagicMock()
        h = _handler({"users": users_svc})
        uid = uuid.uuid4()
        resp = _client(user=_make_user(moderated_tenants=[1]), handler=h).patch(
            f"/organizations/1/members/{uid}/classification", json={}
        )
        assert resp.status_code == 200
        users_svc.set_member_classification.assert_called_once_with(uid, 1, 0)

    def test_forbidden_for_non_moderator(self):
        h = _handler({"users": MagicMock()})
        resp = _client(user=_make_user(), handler=h).patch(
            f"/organizations/1/members/{uuid.uuid4()}/classification", json={"level": 1}
        )
        assert resp.status_code == 403


# ---------------------------------------------------------------------------
# PATCH /organizations/{org_id}/members/{user_id}/role
# ---------------------------------------------------------------------------

class TestSetMemberTenantRole:
    def test_role_assigner_sets_role(self):
        users_svc = MagicMock()
        h = _handler({"users": users_svc})
        uid = uuid.uuid4()
        resp = _client(user=_make_user(role_assignable_tenants=[1]), handler=h).patch(
            f"/organizations/1/members/{uid}/role", json={"role": "moderator"}
        )
        assert resp.status_code == 200
        users_svc.set_member_tenant_role.assert_called_once_with(uid, 1, "moderator")

    def test_forbidden_when_not_role_assigner(self):
        h = _handler({"users": MagicMock()})
        resp = _client(user=_make_user(moderated_tenants=[1]), handler=h).patch(
            f"/organizations/1/members/{uuid.uuid4()}/role", json={"role": "moderator"}
        )
        assert resp.status_code == 403

    def test_role_none_clears_role(self):
        users_svc = MagicMock()
        h = _handler({"users": users_svc})
        uid = uuid.uuid4()
        resp = _client(user=_make_user(role_assignable_tenants=[1]), handler=h).patch(
            f"/organizations/1/members/{uid}/role", json={}
        )
        assert resp.status_code == 200
        users_svc.set_member_tenant_role.assert_called_once_with(uid, 1, None)


# ---------------------------------------------------------------------------
# POST /collections/create
# ---------------------------------------------------------------------------

class TestCreateCollection:
    def _pipeline(self, dim=768):
        pipeline = MagicMock()
        pipeline.dense_encoder.vector_dim = dim
        return pipeline

    def test_creates_collection_without_org(self):
        db = MagicMock()
        pipeline = self._pipeline()
        h = _handler({"ingestion": pipeline, "users": MagicMock()}, providers={"db": db})
        resp = _client(user=_make_user(is_admin=True), handler=h).post(
            "/collections/create", json={"name": "newcol"}
        )
        assert resp.status_code == 200
        assert resp.json() == {"ok": True, "name": "newcol"}
        db.initialize.assert_called_once_with("newcol", {"dense_dim": 768, "create_indexes": True, "owner_org_id": None})

    def test_creates_collection_with_owner_org_as_admin(self):
        db = MagicMock()
        pipeline = self._pipeline()
        users_svc = MagicMock()
        h = _handler({"ingestion": pipeline, "users": users_svc}, providers={"db": db})
        resp = _client(user=_make_user(is_admin=True), handler=h).post(
            "/collections/create", json={"name": "newcol", "owner_org_id": 5}
        )
        assert resp.status_code == 200
        users_svc.add_tenant_collection.assert_called_once_with(5, "newcol", role="owner")

    def test_owner_org_set_but_no_users_service_skips_grant(self):
        db = MagicMock()
        pipeline = self._pipeline()
        h = _handler({"ingestion": pipeline, "users": None}, providers={"db": db})
        resp = _client(user=_make_user(is_admin=True), handler=h).post(
            "/collections/create", json={"name": "newcol", "owner_org_id": 5}
        )
        assert resp.status_code == 200
        db.initialize.assert_called_once()

    def test_moderator_can_assign_own_moderated_org(self):
        db = MagicMock()
        pipeline = self._pipeline()
        h = _handler({"ingestion": pipeline, "users": MagicMock()}, providers={"db": db})
        resp = _client(user=_make_user(moderated_tenants=[5]), handler=h).post(
            "/collections/create", json={"name": "newcol", "owner_org_id": 5}
        )
        assert resp.status_code == 200

    def test_moderator_forbidden_for_other_org(self):
        db = MagicMock()
        pipeline = self._pipeline()
        h = _handler({"ingestion": pipeline, "users": MagicMock()}, providers={"db": db})
        resp = _client(user=_make_user(moderated_tenants=[1]), handler=h).post(
            "/collections/create", json={"name": "newcol", "owner_org_id": 5}
        )
        assert resp.status_code == 403
        db.initialize.assert_not_called()

    def test_missing_name_returns_400(self):
        h = _handler({"ingestion": self._pipeline()}, providers={"db": MagicMock()})
        resp = _client(user=_make_user(is_admin=True), handler=h).post("/collections/create", json={"name": "  "})
        assert resp.status_code == 400

    def test_no_db_returns_503(self):
        h = _handler({"ingestion": self._pipeline()}, providers={})
        resp = _client(user=_make_user(is_admin=True), handler=h).post("/collections/create", json={"name": "x"})
        assert resp.status_code == 503

    def test_no_ingestion_service_returns_503(self):
        h = _handler({"ingestion": None}, providers={"db": MagicMock()})
        resp = _client(user=_make_user(is_admin=True), handler=h).post("/collections/create", json={"name": "x"})
        assert resp.status_code == 503

    def test_db_initialize_failure_returns_500(self):
        db = MagicMock()
        db.initialize.side_effect = RuntimeError("boom")
        h = _handler({"ingestion": self._pipeline()}, providers={"db": db})
        resp = _client(user=_make_user(is_admin=True), handler=h).post("/collections/create", json={"name": "x"})
        assert resp.status_code == 500

    def test_plain_user_forbidden(self):
        h = _handler({})
        resp = _client(user=_make_user(), handler=h).post("/collections/create", json={"name": "x"})
        assert resp.status_code == 403


# ---------------------------------------------------------------------------
# POST /notifications/broadcast, GET /notifications/history
# ---------------------------------------------------------------------------

class TestNotificationsBroadcast:
    def test_admin_broadcasts(self):
        notif_svc = MagicMock()
        notif_svc.broadcast.return_value = uuid.uuid4()
        h = _handler({"notifications": notif_svc})
        resp = _client(user=_make_user(is_admin=True), handler=h).post(
            "/notifications/broadcast", json={"title": "Hi", "body": "Body", "link": "http://x"}
        )
        assert resp.status_code == 200
        assert "notification_id" in resp.json()
        notif_svc.broadcast.assert_called_once_with("Hi", body="Body", link="http://x")

    def test_service_unavailable_returns_503(self):
        h = _handler({"notifications": None})
        resp = _client(user=_make_user(is_admin=True), handler=h).post(
            "/notifications/broadcast", json={"title": "Hi"}
        )
        assert resp.status_code == 503

    def test_non_admin_forbidden(self):
        h = _handler({"notifications": MagicMock()})
        resp = _client(user=_make_user(), handler=h).post("/notifications/broadcast", json={"title": "Hi"})
        assert resp.status_code == 403


class TestNotificationHistory:
    def test_admin_gets_history(self):
        notif_svc = MagicMock()
        notif_svc.list_broadcasts.return_value = {"items": [], "has_more": False}
        h = _handler({"notifications": notif_svc})
        resp = _client(user=_make_user(is_admin=True), handler=h).get("/notifications/history?limit=5")
        assert resp.status_code == 200
        notif_svc.list_broadcasts.assert_called_once_with(limit=5, before_created_at=None, before_rowid=None)

    def test_service_unavailable_returns_503(self):
        h = _handler({"notifications": None})
        resp = _client(user=_make_user(is_admin=True), handler=h).get("/notifications/history")
        assert resp.status_code == 503

    def test_non_admin_forbidden(self):
        h = _handler({"notifications": MagicMock()})
        resp = _client(user=_make_user(), handler=h).get("/notifications/history")
        assert resp.status_code == 403


# ---------------------------------------------------------------------------
# Tenant join requests
# ---------------------------------------------------------------------------

class TestTenantJoinRequests:
    def test_list_as_moderator(self):
        notif_svc = MagicMock()
        notif_svc.list_org_join_requests.return_value = [{"id": "r1"}]
        h = _handler({"notifications": notif_svc})
        resp = _client(user=_make_user(moderated_tenants=[1]), handler=h).get("/organizations/1/join-requests")
        assert resp.status_code == 200
        assert resp.json()["requests"] == [{"id": "r1"}]

    def test_list_forbidden_for_non_moderator(self):
        h = _handler({"notifications": MagicMock()})
        resp = _client(user=_make_user(), handler=h).get("/organizations/1/join-requests")
        assert resp.status_code == 403

    def test_list_service_unavailable(self):
        h = _handler({"notifications": None})
        resp = _client(user=_make_user(moderated_tenants=[1]), handler=h).get("/organizations/1/join-requests")
        assert resp.status_code == 503

    def test_approve_without_tenant_role(self):
        notif_svc = MagicMock()
        h = _handler({"notifications": notif_svc})
        req_id = str(uuid.uuid4())
        user = _make_user(moderated_tenants=[1])
        resp = _client(user=user, handler=h).post(
            f"/organizations/1/join-requests/{req_id}/approve", json={"classification_level": 2}
        )
        assert resp.status_code == 200
        notif_svc.approve_join_request.assert_called_once_with(
            uuid.UUID(req_id), user.id, tenant_role=None, classification_level=2
        )

    def test_approve_with_tenant_role_requires_role_assigner(self):
        notif_svc = MagicMock()
        h = _handler({"notifications": notif_svc})
        req_id = str(uuid.uuid4())
        # moderator but not role-assigner -- should be forbidden since tenant_role given
        resp = _client(user=_make_user(moderated_tenants=[1]), handler=h).post(
            f"/organizations/1/join-requests/{req_id}/approve", json={"tenant_role": "moderator"}
        )
        assert resp.status_code == 403

    def test_approve_with_tenant_role_as_role_assigner_succeeds(self):
        notif_svc = MagicMock()
        h = _handler({"notifications": notif_svc})
        req_id = str(uuid.uuid4())
        user = _make_user(moderated_tenants=[1], role_assignable_tenants=[1])
        resp = _client(user=user, handler=h).post(
            f"/organizations/1/join-requests/{req_id}/approve", json={"tenant_role": "co-moderator"}
        )
        assert resp.status_code == 200
        notif_svc.approve_join_request.assert_called_once_with(
            uuid.UUID(req_id), user.id, tenant_role="co-moderator", classification_level=0
        )

    def test_approve_forbidden_for_non_moderator(self):
        h = _handler({"notifications": MagicMock()})
        resp = _client(user=_make_user(), handler=h).post(
            f"/organizations/1/join-requests/{uuid.uuid4()}/approve", json={}
        )
        assert resp.status_code == 403

    def test_approve_service_unavailable(self):
        h = _handler({"notifications": None})
        resp = _client(user=_make_user(moderated_tenants=[1]), handler=h).post(
            f"/organizations/1/join-requests/{uuid.uuid4()}/approve", json={}
        )
        assert resp.status_code == 503

    def test_reject(self):
        notif_svc = MagicMock()
        h = _handler({"notifications": notif_svc})
        req_id = str(uuid.uuid4())
        user = _make_user(moderated_tenants=[1])
        resp = _client(user=user, handler=h).post(
            f"/organizations/1/join-requests/{req_id}/reject", json={"reason": "no"}
        )
        assert resp.status_code == 200
        notif_svc.reject_join_request.assert_called_once_with(uuid.UUID(req_id), user.id, reason="no")

    def test_reject_forbidden(self):
        h = _handler({"notifications": MagicMock()})
        resp = _client(user=_make_user(), handler=h).post(
            f"/organizations/1/join-requests/{uuid.uuid4()}/reject", json={}
        )
        assert resp.status_code == 403

    def test_reject_service_unavailable(self):
        h = _handler({"notifications": None})
        resp = _client(user=_make_user(moderated_tenants=[1]), handler=h).post(
            f"/organizations/1/join-requests/{uuid.uuid4()}/reject", json={}
        )
        assert resp.status_code == 503


# ---------------------------------------------------------------------------
# Tenant invitations
# ---------------------------------------------------------------------------

class TestTenantInvitations:
    def test_invite_user(self):
        notif_svc = MagicMock()
        notif_svc.invite_user.return_value = uuid.uuid4()
        h = _handler({"notifications": notif_svc})
        user = _make_user(moderated_tenants=[1])
        resp = _client(user=user, handler=h).post(
            "/organizations/1/invitations", json={"identifier": "bob@x.com", "message": "join us"}
        )
        assert resp.status_code == 200
        assert "invitation_id" in resp.json()
        notif_svc.invite_user.assert_called_once_with(1, "bob@x.com", user.id, message="join us")

    def test_invite_forbidden(self):
        h = _handler({"notifications": MagicMock()})
        resp = _client(user=_make_user(), handler=h).post("/organizations/1/invitations", json={})
        assert resp.status_code == 403

    def test_invite_service_unavailable(self):
        h = _handler({"notifications": None})
        resp = _client(user=_make_user(moderated_tenants=[1]), handler=h).post(
            "/organizations/1/invitations", json={"identifier": "x"}
        )
        assert resp.status_code == 503

    def test_list_invitations(self):
        notif_svc = MagicMock()
        notif_svc.list_org_invitations.return_value = [{"id": "i1"}]
        h = _handler({"notifications": notif_svc})
        resp = _client(user=_make_user(moderated_tenants=[1]), handler=h).get("/organizations/1/invitations")
        assert resp.status_code == 200
        assert resp.json()["invitations"] == [{"id": "i1"}]

    def test_list_invitations_forbidden(self):
        h = _handler({"notifications": MagicMock()})
        resp = _client(user=_make_user(), handler=h).get("/organizations/1/invitations")
        assert resp.status_code == 403

    def test_list_invitations_service_unavailable(self):
        h = _handler({"notifications": None})
        resp = _client(user=_make_user(moderated_tenants=[1]), handler=h).get("/organizations/1/invitations")
        assert resp.status_code == 503

    def test_cancel_invitation(self):
        notif_svc = MagicMock()
        h = _handler({"notifications": notif_svc})
        inv_id = str(uuid.uuid4())
        resp = _client(user=_make_user(moderated_tenants=[1]), handler=h).post(
            f"/organizations/1/invitations/{inv_id}/cancel"
        )
        assert resp.status_code == 200
        notif_svc.cancel_invitation.assert_called_once_with(uuid.UUID(inv_id), 1)

    def test_cancel_invitation_forbidden(self):
        h = _handler({"notifications": MagicMock()})
        resp = _client(user=_make_user(), handler=h).post(f"/organizations/1/invitations/{uuid.uuid4()}/cancel")
        assert resp.status_code == 403

    def test_cancel_invitation_service_unavailable(self):
        h = _handler({"notifications": None})
        resp = _client(user=_make_user(moderated_tenants=[1]), handler=h).post(
            f"/organizations/1/invitations/{uuid.uuid4()}/cancel"
        )
        assert resp.status_code == 503


# ---------------------------------------------------------------------------
# Tenant share requests
# ---------------------------------------------------------------------------

class TestTenantShareRequests:
    def test_file_share_request(self):
        notif_svc = MagicMock()
        notif_svc.file_share_request.return_value = uuid.uuid4()
        h = _handler({"notifications": notif_svc})
        user = _make_user(moderated_tenants=[1])
        resp = _client(user=user, handler=h).post(
            "/organizations/1/share-requests", json={"target_org_id": 2, "message": "please"}
        )
        assert resp.status_code == 200
        assert "request_id" in resp.json()
        notif_svc.file_share_request.assert_called_once_with(1, 2, user.id, message="please")

    def test_file_share_request_missing_target_org_returns_400(self):
        h = _handler({"notifications": MagicMock()})
        resp = _client(user=_make_user(moderated_tenants=[1]), handler=h).post(
            "/organizations/1/share-requests", json={}
        )
        assert resp.status_code == 400

    def test_file_share_request_forbidden(self):
        h = _handler({"notifications": MagicMock()})
        resp = _client(user=_make_user(), handler=h).post(
            "/organizations/1/share-requests", json={"target_org_id": 2}
        )
        assert resp.status_code == 403

    def test_file_share_request_service_unavailable(self):
        h = _handler({"notifications": None})
        resp = _client(user=_make_user(moderated_tenants=[1]), handler=h).post(
            "/organizations/1/share-requests", json={"target_org_id": 2}
        )
        assert resp.status_code == 503

    def test_list_share_requests(self):
        notif_svc = MagicMock()
        notif_svc.list_org_share_requests.return_value = [{"id": "s1"}]
        h = _handler({"notifications": notif_svc})
        resp = _client(user=_make_user(moderated_tenants=[1]), handler=h).get(
            "/organizations/1/share-requests?direction=outgoing"
        )
        assert resp.status_code == 200
        notif_svc.list_org_share_requests.assert_called_once_with(1, "outgoing", status=None)

    def test_list_share_requests_forbidden(self):
        h = _handler({"notifications": MagicMock()})
        resp = _client(user=_make_user(), handler=h).get("/organizations/1/share-requests")
        assert resp.status_code == 403

    def test_list_share_requests_service_unavailable(self):
        h = _handler({"notifications": None})
        resp = _client(user=_make_user(moderated_tenants=[1]), handler=h).get("/organizations/1/share-requests")
        assert resp.status_code == 503

    def test_approve_share_request(self):
        notif_svc = MagicMock()
        req_id = uuid.uuid4()
        notif_svc.repo.get_share_request.return_value = {"target_org_id": 1}
        h = _handler({"notifications": notif_svc})
        resp = _client(user=_make_user(moderated_tenants=[1]), handler=h).post(
            f"/organizations/1/share-requests/{req_id}/approve", json={"collections": ["c1"]}
        )
        assert resp.status_code == 200
        notif_svc.approve_share_request.assert_called_once()

    def test_approve_share_request_not_found_for_tenant(self):
        notif_svc = MagicMock()
        notif_svc.repo.get_share_request.return_value = {"target_org_id": 999}
        h = _handler({"notifications": notif_svc})
        resp = _client(user=_make_user(moderated_tenants=[1]), handler=h).post(
            f"/organizations/1/share-requests/{uuid.uuid4()}/approve", json={}
        )
        assert resp.status_code == 404

    def test_approve_share_request_missing_returns_404(self):
        notif_svc = MagicMock()
        notif_svc.repo.get_share_request.return_value = None
        h = _handler({"notifications": notif_svc})
        resp = _client(user=_make_user(moderated_tenants=[1]), handler=h).post(
            f"/organizations/1/share-requests/{uuid.uuid4()}/approve", json={}
        )
        assert resp.status_code == 404

    def test_approve_share_request_forbidden(self):
        h = _handler({"notifications": MagicMock()})
        resp = _client(user=_make_user(), handler=h).post(
            f"/organizations/1/share-requests/{uuid.uuid4()}/approve", json={}
        )
        assert resp.status_code == 403

    def test_approve_share_request_service_unavailable(self):
        h = _handler({"notifications": None})
        resp = _client(user=_make_user(moderated_tenants=[1]), handler=h).post(
            f"/organizations/1/share-requests/{uuid.uuid4()}/approve", json={}
        )
        assert resp.status_code == 503

    def test_reject_share_request(self):
        notif_svc = MagicMock()
        notif_svc.repo.get_share_request.return_value = {"target_org_id": 1}
        h = _handler({"notifications": notif_svc})
        resp = _client(user=_make_user(moderated_tenants=[1]), handler=h).post(
            f"/organizations/1/share-requests/{uuid.uuid4()}/reject", json={"reason": "no"}
        )
        assert resp.status_code == 200
        notif_svc.reject_share_request.assert_called_once()

    def test_reject_share_request_not_found(self):
        notif_svc = MagicMock()
        notif_svc.repo.get_share_request.return_value = {"target_org_id": 2}
        h = _handler({"notifications": notif_svc})
        resp = _client(user=_make_user(moderated_tenants=[1]), handler=h).post(
            f"/organizations/1/share-requests/{uuid.uuid4()}/reject", json={}
        )
        assert resp.status_code == 404

    def test_reject_share_request_forbidden(self):
        h = _handler({"notifications": MagicMock()})
        resp = _client(user=_make_user(), handler=h).post(
            f"/organizations/1/share-requests/{uuid.uuid4()}/reject", json={}
        )
        assert resp.status_code == 403

    def test_reject_share_request_service_unavailable(self):
        h = _handler({"notifications": None})
        resp = _client(user=_make_user(moderated_tenants=[1]), handler=h).post(
            f"/organizations/1/share-requests/{uuid.uuid4()}/reject", json={}
        )
        assert resp.status_code == 503


# ---------------------------------------------------------------------------
# GET /roles
# ---------------------------------------------------------------------------

class TestGetRoles:
    def test_admin_lists_roles(self):
        users_svc = MagicMock()
        users_svc.list_roles.return_value = [{"id": 1, "name": "admin"}]
        h = _handler({"users": users_svc})
        resp = _client(user=_make_user(is_admin=True), handler=h).get("/roles")
        assert resp.status_code == 200
        assert resp.json() == [{"id": 1, "name": "admin"}]

    def test_non_admin_forbidden(self):
        h = _handler({"users": MagicMock()})
        resp = _client(user=_make_user(), handler=h).get("/roles")
        assert resp.status_code == 403
