from __future__ import annotations

import logging

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from hestia.domain.exceptions import HestiaError

_log = logging.getLogger("hestia.system")

# Primary path: all domain/application code raises HestiaError subclasses.
# The built-in exception handlers below are safety nets for anything that
# escapes untyped (e.g. third-party libraries, unexpected code paths).


async def _hestia_error_handler(request: Request, exc: HestiaError) -> JSONResponse:
    extra = {"method": request.method, "path": request.url.path,
             "detail": exc.message, "status_code": exc.status_code}
    if exc.status_code >= 500:
        _log.error("server_error", extra=extra, exc_info=exc)
    else:
        _log.warning("client_error", extra=extra)
    return JSONResponse(status_code=exc.status_code, content={"detail": exc.message})


async def _permission_error_handler(request: Request, exc: PermissionError) -> JSONResponse:
    detail = str(exc) or "Forbidden"
    _log.warning("client_error", extra={"method": request.method, "path": request.url.path,
                                        "detail": detail, "status_code": 403})
    return JSONResponse(status_code=403, content={"detail": detail})


async def _value_error_handler(request: Request, exc: ValueError) -> JSONResponse:
    _log.warning("client_error", extra={"method": request.method, "path": request.url.path,
                                        "detail": str(exc), "status_code": 400})
    return JSONResponse(status_code=400, content={"detail": str(exc)})


async def _key_error_handler(request: Request, exc: KeyError) -> JSONResponse:
    _log.error("unhandled_error", extra={"method": request.method, "path": request.url.path,
                                         "status_code": 500}, exc_info=exc)
    return JSONResponse(status_code=500, content={"detail": "Internal server error"})


async def _validation_error_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    _log.warning("validation_error", extra={"method": request.method, "path": request.url.path,
                                            "errors": exc.errors(), "status_code": 422})
    return JSONResponse(status_code=422, content={"detail": exc.errors()})


async def _unhandled_error_handler(request: Request, exc: Exception) -> JSONResponse:
    _log.error("unhandled_error", extra={"method": request.method, "path": request.url.path,
                                         "status_code": 500}, exc_info=exc)
    return JSONResponse(status_code=500, content={"detail": "Internal server error"})


def register_error_handlers(app: FastAPI) -> None:
    app.add_exception_handler(HestiaError, _hestia_error_handler)
    app.add_exception_handler(PermissionError, _permission_error_handler)
    app.add_exception_handler(ValueError, _value_error_handler)
    app.add_exception_handler(KeyError, _key_error_handler)
    app.add_exception_handler(RequestValidationError, _validation_error_handler)
    app.add_exception_handler(Exception, _unhandled_error_handler)
