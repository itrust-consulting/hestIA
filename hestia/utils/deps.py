from fastapi import Request, HTTPException
from hestia.container import Container

def get_container(request: Request) -> Container:
    c = getattr(request.app.state, "container", None)
    if c is None:
        raise HTTPException(status_code=503, detail="Container not initialized yet")
    return c