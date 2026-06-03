from __future__ import annotations

from unittest.mock import MagicMock

from fastapi import FastAPI
from fastapi.testclient import TestClient

from hestia.api.routers.search import router
from hestia.api.security import get_current_user
from hestia.api.dependencies import get_container
from hestia.domain.auth.models import CollectionPermission
from tests.unit.conftest import _make_user


def _app(user=None, container=None):
    app = FastAPI()
    app.include_router(router)
    app.dependency_overrides[get_current_user] = lambda: (user or _make_user(is_admin=True))
    app.dependency_overrides[get_container] = lambda: (container or MagicMock())
    return app


def _mock_retriever():
    r = MagicMock()
    r.retrieve.return_value = MagicMock(points=[])
    return r


class TestSearchRouter:

    def test_semantic_mode_accepted(self):
        container = MagicMock()
        container.services = {"search": _mock_retriever()}

        client = TestClient(_app(container=container))
        resp = client.post("/search", json={
            "mode": "semantic",
            "query": [0.1, 0.2, 0.3],
            "collection": "col",
        })
        assert resp.status_code == 200

    def test_keyword_mode_accepted(self):
        container = MagicMock()
        container.services = {"search": _mock_retriever()}

        client = TestClient(_app(container=container))
        resp = client.post("/search", json={
            "mode": "keyword",
            "query": {"indices": [0, 1], "values": [0.5, 0.3]},
            "collection": "col",
        })
        assert resp.status_code == 200

    def test_hybrid_mode_accepted(self):
        container = MagicMock()
        container.services = {"search": _mock_retriever()}

        client = TestClient(_app(container=container))
        resp = client.post("/search", json={
            "mode": "hybrid",
            "query": {
                "dense": [0.1, 0.2],
                "sparse": {"indices": [0], "values": [0.9]},
            },
            "collection": "col",
        })
        assert resp.status_code == 200

    def test_non_admin_without_permission_gets_403(self):
        user = _make_user()  # no collection permissions
        container = MagicMock()
        container.services = {"search": _mock_retriever()}

        client = TestClient(_app(user=user, container=container))
        resp = client.post("/search", json={
            "mode": "semantic",
            "query": [0.1],
            "collection": "secret-col",
        })
        assert resp.status_code == 403

    def test_user_with_collection_permission_can_search(self):
        user = _make_user(allowed_collections={
            "allowed-col": CollectionPermission(access=True)
        })
        container = MagicMock()
        container.services = {"search": _mock_retriever()}

        client = TestClient(_app(user=user, container=container))
        resp = client.post("/search", json={
            "mode": "semantic",
            "query": [0.1],
            "collection": "allowed-col",
        })
        assert resp.status_code == 200

    def test_wildcard_permission_grants_any_collection(self):
        user = _make_user(allowed_collections={
            "*": CollectionPermission(access=True)
        })
        container = MagicMock()
        container.services = {"search": _mock_retriever()}

        client = TestClient(_app(user=user, container=container))
        resp = client.post("/search", json={
            "mode": "semantic",
            "query": [0.1],
            "collection": "any-col",
        })
        assert resp.status_code == 200
