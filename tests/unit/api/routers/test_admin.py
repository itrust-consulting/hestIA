from __future__ import annotations

import uuid
from unittest.mock import MagicMock

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from hestia.api.routers.admin import router
from hestia.api.security import get_current_user
from hestia.api.dependencies import get_handler
from tests.unit.conftest import _make_user


def _app(user, handler):
    app = FastAPI()
    app.include_router(router)
    app.dependency_overrides[get_current_user] = lambda: user
    app.dependency_overrides[get_handler] = lambda: handler
    return app


# ---------------------------------------------------------------------------
# GET /users
# ---------------------------------------------------------------------------

class TestGetUsers:

    def test_admin_gets_all_users(self):
        user = _make_user(is_admin=True)
        handler = MagicMock()
        mock_svc = MagicMock()
        mock_svc.list_users.return_value = [{"id": str(uuid.uuid4()), "username": "alice"}]
        handler.container.services.get.return_value = mock_svc

        client = TestClient(_app(user, handler))
        resp = client.get("/users")
        assert resp.status_code == 200
        data = resp.json()
        assert "users" in data

    def test_moderator_gets_filtered_users(self):
        user = _make_user(moderated_tenants=[1])
        handler = MagicMock()
        uid = uuid.uuid4()
        mock_svc = MagicMock()
        mock_svc.get_org_users.return_value = [{"id": uid, "username": "bob"}]
        handler.container.services.get.return_value = mock_svc

        client = TestClient(_app(user, handler))
        resp = client.get("/users")
        assert resp.status_code == 200

    def test_plain_user_gets_403(self):
        user = _make_user()
        handler = MagicMock()
        client = TestClient(_app(user, handler))
        resp = client.get("/users")
        assert resp.status_code == 403

    def test_moderator_deduplicates_across_tenants(self):
        uid = uuid.uuid4()
        user = _make_user(moderated_tenants=[1, 2])
        handler = MagicMock()
        mock_svc = MagicMock()
        # Both tenants return the same user
        mock_svc.get_org_users.return_value = [{"id": uid, "username": "bob"}]
        handler.container.services.get.return_value = mock_svc

        client = TestClient(_app(user, handler))
        resp = client.get("/users")
        users = resp.json()["users"]
        # Should only appear once
        assert len(users) == 1


# ---------------------------------------------------------------------------
# POST /collections/create
# ---------------------------------------------------------------------------

class TestCreateCollection:

    def test_requires_name(self):
        user = _make_user(is_admin=True)
        handler = MagicMock()
        pipeline = MagicMock()
        pipeline.dense_encoder.encode.return_value = MagicMock(vector=[0.1, 0.2])
        handler.container.services.get.return_value = pipeline
        handler.container.providers.get.return_value = MagicMock()

        client = TestClient(_app(user, handler))
        resp = client.post("/collections/create", json={"name": ""})
        assert resp.status_code == 400

    def test_non_admin_moderator_can_create_for_own_org(self):
        user = _make_user(moderated_tenants=[5])
        handler = MagicMock()
        pipeline = MagicMock()
        pipeline.dense_encoder.encode.return_value = MagicMock(vector=[0.1] * 10)
        handler.container.services.get.return_value = pipeline
        mock_db = MagicMock()
        handler.container.providers.get.return_value = mock_db

        client = TestClient(_app(user, handler))
        resp = client.post("/collections/create", json={"name": "new-col", "owner_org_id": 5})
        assert resp.status_code == 200

    def test_non_admin_cannot_assign_to_unmoderated_org(self):
        user = _make_user(moderated_tenants=[5])
        handler = MagicMock()
        pipeline = MagicMock()
        pipeline.dense_encoder.encode.return_value = MagicMock(vector=[0.1] * 10)
        handler.container.services.get.return_value = pipeline
        handler.container.providers.get.return_value = MagicMock()

        client = TestClient(_app(user, handler))
        resp = client.post("/collections/create", json={"name": "col", "owner_org_id": 999})
        assert resp.status_code == 403
