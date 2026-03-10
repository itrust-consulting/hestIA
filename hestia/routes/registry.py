
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Sequence, Dict

from fastapi import FastAPI, APIRouter

from hestia.routes.health import router as health_router
from hestia.routes.embed import router as embed_router
from hestia.routes.generate import router as generate_router
from hestia.routes.chat import router as chat_router
from hestia.routes.search import router as search_router

def include_routers(app: FastAPI, enabled_services: set[str]) -> None:
    """
    Include:
    - all always_on routers
    - any router whose `service` is in enabled_services
    """
    for _, spec in ROUTER_REGISTRY.items():
        if spec.always_on or (spec.service and spec.service in enabled_services):
            app.include_router(spec.router, prefix=spec.prefix, tags=list(spec.tags))

        print(f"Service {spec.service} was initialised with endpoint {spec.prefix}/{spec.tags}")


@dataclass(frozen=True)
class RouterSpec:
    router: APIRouter
    prefix: str = ""
    tags: Sequence[str] = ()
    # If set, router is only included when that service is started
    service: Optional[str] = None
    # Always include regardless of started services
    always_on: bool = False


ROUTER_REGISTRY: Dict[str, RouterSpec] = {
    # --- always-on routers ---
    "health": RouterSpec(router=health_router, prefix="", tags=("health", "ready"), always_on=True),

    # --- service routers (conditional) ---
    "embed": RouterSpec(router=embed_router, prefix="/api", tags=("embed"), service="embed",),
    "generate": RouterSpec(router=generate_router, prefix="/api",tags=("generate"), service="generate"),
    "chat": RouterSpec(router=chat_router, prefix="/api", tags=("chat"), service="generate"),
    "search": RouterSpec(router=search_router, prefix="/api", tags=("search"), service="search"),
    "rag": RouterSpec(router=search_router, prefix="/api", tags=("rag"), service="rag")
}
