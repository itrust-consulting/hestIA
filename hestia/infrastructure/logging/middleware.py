from __future__ import annotations

import logging
import time
import uuid

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from hestia.infrastructure.logging.config import request_id_var

_log = logging.getLogger("hestia.system")


class CorrelationMiddleware(BaseHTTPMiddleware):
    """
    Assigns a request_id to every request (reads X-Request-ID header or
    generates a UUID), stores it in a ContextVar so all loggers in the
    call-stack pick it up automatically, and emits one http_request record
    per request with method, path, status code, and latency.

    For streaming responses the logged latency is time-to-first-response,
    not total transfer time — the body is consumed after dispatch returns.
    """

    async def dispatch(self, request: Request, call_next) -> Response:
        rid = request.headers.get("X-Request-ID") or str(uuid.uuid4())
        token = request_id_var.set(rid)
        t0 = time.perf_counter()

        try:
            response = await call_next(request)
        except Exception:
            # Log while id is still set, then let finally reset it.
            _log.exception(
                "http_request_error",
                extra={
                    "method": request.method,
                    "path": request.url.path,
                    "latency_ms": round((time.perf_counter() - t0) * 1000, 1),
                },
            )
            raise
        else:
            # else runs before finally — request_id_var is still set here.
            _log.info(
                "http_request",
                extra={
                    "method": request.method,
                    "path": request.url.path,
                    "status_code": response.status_code,
                    "latency_ms": round((time.perf_counter() - t0) * 1000, 1),
                },
            )
            response.headers["X-Request-ID"] = rid
            return response
        finally:
            request_id_var.reset(token)
