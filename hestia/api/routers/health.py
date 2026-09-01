import json
from typing import Any, Dict

from fastapi import APIRouter, Depends
from fastapi.responses import Response

from hestia.api.dependencies import get_container
from hestia.container import Container

router = APIRouter()


# @MRS-074
@router.get("/health")
def health() -> Dict[str, Any]:
    return Response(json.dumps({"ok": True, "status": "up"}), media_type="application/json")


@router.get("/ready")
def ready(c: Container = Depends(get_container)) -> Dict[str, Any]:
    return Response(
        json.dumps({
            "ok": True,
            "status": "ready",
            "services": sorted(c.services.keys()),
            "providers": sorted(c.providers.keys()),
        }),
        media_type="application/json",
    )


@router.get("/models")
def models(c: Container = Depends(get_container)) -> Dict[str, Any]:
    return Response(json.dumps(c.providers["llm"].models), media_type="application/json")


@router.get("/collections")
def collections(c: Container = Depends(get_container)) -> Dict[str, Any]:
    return Response(json.dumps(c.require_db_provider().collections), media_type="application/json")
