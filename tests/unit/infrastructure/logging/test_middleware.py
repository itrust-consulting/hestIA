from __future__ import annotations

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from starlette.responses import Response

from hestia.infrastructure.logging.middleware import CorrelationMiddleware


def _app_with_middleware():
    app = FastAPI()
    app.add_middleware(CorrelationMiddleware)

    @app.get("/ping")
    def ping():
        return Response(content="pong", media_type="text/plain")

    return app


class TestCorrelationMiddleware:

    def test_injects_request_id_header_in_response(self):
        client = TestClient(_app_with_middleware())
        resp = client.get("/ping")
        assert "X-Request-ID" in resp.headers

    def test_propagates_existing_request_id(self):
        client = TestClient(_app_with_middleware())
        resp = client.get("/ping", headers={"X-Request-ID": "my-req-id"})
        assert resp.headers["X-Request-ID"] == "my-req-id"

    def test_generates_new_uuid_when_no_id_in_request(self):
        client = TestClient(_app_with_middleware())
        resp = client.get("/ping")
        rid = resp.headers.get("X-Request-ID", "")
        # Should be a valid UUID (36 chars with dashes)
        assert len(rid) == 36

    def test_response_is_200(self):
        client = TestClient(_app_with_middleware())
        resp = client.get("/ping")
        assert resp.status_code == 200
