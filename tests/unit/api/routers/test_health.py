from __future__ import annotations

import json
from unittest.mock import MagicMock

from fastapi import FastAPI
from fastapi.testclient import TestClient

from hestia.api.dependencies import get_container
from hestia.api.routers.health import router


def _app(container=None):
    app = FastAPI()
    app.include_router(router)
    app.dependency_overrides[get_container] = lambda: (container or MagicMock())
    return app


class TestHealth:

    def test_returns_ok(self):
        client = TestClient(_app())
        resp = client.get("/health")
        assert resp.status_code == 200
        assert json.loads(resp.text) == {"ok": True, "status": "up"}


class TestReady:

    def test_lists_services_and_providers(self):
        container = MagicMock()
        container.services = {"chat": MagicMock(), "auth": MagicMock()}
        container.providers = {"db": MagicMock()}
        client = TestClient(_app(container))

        resp = client.get("/ready")

        assert resp.status_code == 200
        body = json.loads(resp.text)
        assert body["services"] == ["auth", "chat"]
        assert body["providers"] == ["db"]


class TestCollections:

    def test_no_longer_exposes_an_unauthenticated_collections_route(self):
        # Regression test for an unauthenticated full-catalogue-disclosure
        # bug: this router used to define its own "/collections" with no
        # auth dependency at all, colliding by name with the properly
        # authenticated, permission-filtered "/collections" already served
        # by ingestion.py at "/api/collections". Confirms it's gone.
        client = TestClient(_app())

        resp = client.get("/collections")

        assert resp.status_code == 404


class TestModels:

    def test_endpoint_is_currently_broken_no_llm_provider_key_exists(self):
        # Regression-documenting test, not a happy-path test: build_container
        # (hestia/container.py) never populates providers["llm"] -- the only
        # provider key it ever sets is "db" (QdrantDB). This route as
        # written always KeyErrors in real use. Documented here rather than
        # silently "fixed" as a side effect of a coverage pass -- flagged
        # separately for a real decision on what this endpoint should do.
        container = MagicMock()
        container.providers = {"db": MagicMock()}  # no "llm" key, matching real build_container output
        client = TestClient(_app(container), raise_server_exceptions=False)

        resp = client.get("/models")

        assert resp.status_code == 500
