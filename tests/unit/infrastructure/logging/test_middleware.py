from __future__ import annotations

import logging

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

    @app.get("/boom")
    def boom():
        raise ValueError("kaboom")

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

    def test_happy_path_logs_http_request_at_info(self, caplog):
        client = TestClient(_app_with_middleware())
        with caplog.at_level(logging.INFO, logger="hestia.system"):
            client.get("/ping")

        records = [r for r in caplog.records if r.name == "hestia.system"]
        assert len(records) == 1
        assert records[0].getMessage() == "http_request"
        assert records[0].levelname == "INFO"
        assert records[0].status_code == 200
        assert records[0].method == "GET"
        assert records[0].path == "/ping"

    def test_downstream_exception_propagates_and_is_not_swallowed(self):
        # raise_server_exceptions defaults to True, so TestClient re-raises the
        # route's exception into the test rather than turning it into a 500 --
        # this is the strongest proof the middleware's `raise` actually
        # re-raises instead of swallowing it.
        client = TestClient(_app_with_middleware())
        with pytest.raises(ValueError, match="kaboom"):
            client.get("/boom")

    def test_downstream_exception_logs_http_request_error_with_exc_info(self, caplog):
        client = TestClient(_app_with_middleware(), raise_server_exceptions=False)
        with caplog.at_level(logging.INFO, logger="hestia.system"):
            resp = client.get("/boom")

        assert resp.status_code == 500

        records = [r for r in caplog.records if r.name == "hestia.system"]
        assert len(records) == 1
        error_record = records[0]
        assert error_record.getMessage() == "http_request_error"
        assert error_record.levelname == "ERROR"
        assert error_record.method == "GET"
        assert error_record.path == "/boom"
        assert error_record.exc_info is not None
        assert error_record.exc_info[0] is ValueError

    def test_downstream_exception_response_has_no_request_id_header(self):
        # The X-Request-ID header is only ever set in dispatch()'s success
        # branch, after call_next() returns a real Response. When call_next()
        # raises instead, dispatch() logs and re-raises without ever
        # constructing/touching a Response, so the header can't be set here --
        # documenting that rather than assuming it's added some other way.
        client = TestClient(_app_with_middleware(), raise_server_exceptions=False)
        resp = client.get("/boom")
        assert "X-Request-ID" not in resp.headers
