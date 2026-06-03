from __future__ import annotations

import asyncio
from unittest.mock import MagicMock

import pytest
from fastapi.responses import JSONResponse
from starlette.requests import Request

from hestia.api.error_handlers import (
    _hestia_error_handler,
    _key_error_handler,
    _permission_error_handler,
    _unhandled_error_handler,
    _validation_error_handler,
    _value_error_handler,
    register_error_handlers,
)
from hestia.domain.exceptions import HestiaError, NotFoundError, ValidationError


def _request():
    req = MagicMock(spec=Request)
    req.method = "GET"
    req.url.path = "/test"
    return req


def _run(coro):
    return asyncio.run(coro)


class TestHestiaErrorHandler:

    def test_returns_json_response(self):
        resp = _run(_hestia_error_handler(_request(), NotFoundError("not found")))
        assert isinstance(resp, JSONResponse)

    def test_uses_exception_status_code(self):
        resp = _run(_hestia_error_handler(_request(), NotFoundError("missing")))
        assert resp.status_code == 404

    def test_500_for_base_hestia_error(self):
        resp = _run(_hestia_error_handler(_request(), HestiaError("boom")))
        assert resp.status_code == 500

    def test_400_for_validation_error(self):
        resp = _run(_hestia_error_handler(_request(), ValidationError("bad input")))
        assert resp.status_code == 400


class TestPermissionErrorHandler:

    def test_returns_403(self):
        resp = _run(_permission_error_handler(_request(), PermissionError("no")))
        assert resp.status_code == 403


class TestValueErrorHandler:

    def test_returns_400(self):
        resp = _run(_value_error_handler(_request(), ValueError("bad")))
        assert resp.status_code == 400


class TestKeyErrorHandler:

    def test_returns_500(self):
        resp = _run(_key_error_handler(_request(), KeyError("missing_key")))
        assert resp.status_code == 500


class TestUnhandledErrorHandler:

    def test_returns_500(self):
        resp = _run(_unhandled_error_handler(_request(), RuntimeError("unexpected")))
        assert resp.status_code == 500


class TestValidationErrorHandler:

    def test_returns_422(self):
        from hestia.api.error_handlers import _validation_error_handler
        from fastapi.exceptions import RequestValidationError
        exc = RequestValidationError(errors=[{"loc": ["body", "field"], "msg": "required", "type": "missing"}])
        resp = _run(_validation_error_handler(_request(), exc))
        assert resp.status_code == 422


class TestRegisterErrorHandlers:

    def test_registers_handlers_on_app(self):
        from fastapi import FastAPI
        app = FastAPI()
        register_error_handlers(app)
        assert HestiaError in app.exception_handlers
        assert PermissionError in app.exception_handlers
        assert ValueError in app.exception_handlers
