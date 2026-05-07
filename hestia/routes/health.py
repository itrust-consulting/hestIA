import json
from fastapi import APIRouter, Depends
from fastapi.responses import Response
from typing import Any, Dict

from hestia.container import Container
from hestia.utils.deps import get_container
from hestia.utils.security import get_current_user

router = APIRouter()

@router.get("/health")
def health() -> Dict[str, Any]:
    # Liveness probe: process is running
    resp = json.dumps({"ok": True, "status": "up"})
    return Response(resp, media_type="application/json")

@router.get("/ready")
def ready(container = Depends(get_container)) -> Dict[str, Any]:
    # Readiness probe: container initialized + show enabled services/providers
    resp = json.dumps({
        "ok": True,
        "status": "ready",
        "services": sorted(container.services.keys()),
        "providers": sorted(container.providers.keys()),
    })
    return Response(resp, media_type="application/json")

@router.get("/models")
def models(c: Container = Depends(get_container)) -> Dict[str, Any]:
    llm = c.providers["llm"]
    resp = json.dumps(llm.models)
    return Response(resp, media_type="application/json")


@router.get("/collections")
def collections(c: Container = Depends(get_container)) -> Dict[str, Any]:
    db = c.providers["db"]
    resp = json.dumps(db.collections)
    return Response(resp, media_type="application/json")