from fastapi import APIRouter, Depends
from typing import Any, Dict
from hestia.utils.deps import get_container

router = APIRouter()

@router.get("/health")
def health() -> Dict[str, Any]:
    # Liveness probe: process is running
    return {"ok": True, "status": "up"}

@router.get("/ready")
def ready(container = Depends(get_container)) -> Dict[str, Any]:
    # Readiness probe: container initialized + show enabled services/providers
    return {
        "ok": True,
        "status": "ready",
        "services": sorted(container.services.keys()),
        "providers": sorted(container.providers.keys()),
    }