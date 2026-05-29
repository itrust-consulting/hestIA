from fastapi import HTTPException, Request

from hestia.container import Container
from hestia.handler import RequestHandler


def get_container(request: Request) -> Container:
    c = getattr(request.app.state, "container", None)
    if c is None:
        raise HTTPException(503, "Container not initialized")
    return c


def get_handler(request: Request) -> RequestHandler:
    h = getattr(request.app.state, "handler", None)
    if h is None:
        raise HTTPException(503, "Handler not initialized")
    return h
