from fastapi import Request, HTTPException
from hestia.container import Container
from hestia.handler import RequestHandler

def get_container(request: Request) -> Container:
    c = getattr(request.app.state, "container", None)
    if c is None:
        raise HTTPException(status_code=503, detail="Container not initialized yet")
    return c

def get_handler(request: Request) -> RequestHandler:
    h = getattr(request.app.state, "handler", None)
    if h is None:
        raise HTTPException(status_code=503, detail="RequestHandler not initialized yet")
    return h