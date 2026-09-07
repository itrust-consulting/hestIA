from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional, Sequence, Dict

from fastapi import FastAPI, APIRouter

from hestia.api.routers.health import router as health_router
from hestia.api.routers.auth import router as auth_router
from hestia.api.routers.account import router as account_router
from hestia.api.routers.admin import router as admin_router
from hestia.api.routers.notifications import router as notifications_router
from hestia.api.routers.notification_settings import router as notification_settings_router
from hestia.api.routers.llm_settings import router as llm_settings_router
from hestia.api.routers.auth_settings import router as auth_settings_router
from hestia.api.routers.workflow_settings import router as workflow_settings_router
from hestia.api.routers.logs import router as logs_router
from hestia.api.routers.conversations import router as convo_router
from hestia.api.routers.encode import router as encode_router
from hestia.api.routers.generate import router as generate_router
from hestia.api.routers.chat import router as chat_router
from hestia.api.routers.search import router as search_router
from hestia.api.routers.ingestion import router as ingestion_router


@dataclass(frozen=True)
class RouterSpec:
    router: APIRouter
    prefix: str = ""
    tags: Sequence[str] = field(default_factory=tuple)
    service: Optional[str] = None
    always_on: bool = False


ROUTER_REGISTRY: Dict[str, RouterSpec] = {
    "health":    RouterSpec(router=health_router,   prefix="",       tags=("health",),       always_on=True),
    "auth":      RouterSpec(router=auth_router,      prefix="",       tags=("auth",),         always_on=True),
    "account":   RouterSpec(router=account_router,   prefix="",       tags=("account",),      always_on=True),
    "convo":     RouterSpec(router=convo_router,     prefix="",       tags=("conversations",), always_on=True),
    "admin":     RouterSpec(router=admin_router,     prefix="/admin", tags=("admin",),        always_on=True),
    "notifications": RouterSpec(router=notifications_router, prefix="", tags=("notifications",), always_on=True),
    "notification_settings": RouterSpec(router=notification_settings_router, prefix="/admin", tags=("admin",), always_on=True),
    "llm_settings": RouterSpec(router=llm_settings_router, prefix="/admin", tags=("admin",),  always_on=True),
    "auth_settings": RouterSpec(router=auth_settings_router, prefix="/admin", tags=("admin",), always_on=True),
    "workflow_settings": RouterSpec(router=workflow_settings_router, prefix="/admin", tags=("admin",), always_on=True),
    "logs":      RouterSpec(router=logs_router,      prefix="/admin", tags=("admin",),        always_on=True),
    "encode":    RouterSpec(router=encode_router,    prefix="/api",   tags=("encode",),       service="encDense"),
    "generate":  RouterSpec(router=generate_router,  prefix="/api",   tags=("generate",),     service="generate"),
    "chat":      RouterSpec(router=chat_router,      prefix="/api",   tags=("chat",),         service="generate"),
    "search":    RouterSpec(router=search_router,    prefix="/api",   tags=("search",),       service="search"),
    "ingestion": RouterSpec(router=ingestion_router, prefix="/api",   tags=("ingestion",),   service="ingestion"),
}


# @MRS-002
def include_routers(app: FastAPI, enabled_services: set[str]) -> None:
    seen_routes: set[tuple[str, str]] = set()
    for name, spec in ROUTER_REGISTRY.items():
        if spec.always_on or (spec.service and spec.service in enabled_services):
            for route in spec.router.routes:
                full_path = spec.prefix + route.path
                for method in getattr(route, "methods", None) or ():
                    key = (method, full_path)
                    if key in seen_routes:
                        raise RuntimeError(
                            f"Duplicate route registration: {method} {full_path} "
                            f"(router '{name}' collides with an earlier router). "
                            "Two routers claiming the same path can silently bypass "
                            "whichever one has the stricter auth dependency."
                        )
                    seen_routes.add(key)
            app.include_router(spec.router, prefix=spec.prefix, tags=list(spec.tags))
