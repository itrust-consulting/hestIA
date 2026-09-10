from typing import Literal, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse

from hestia.api.dependencies import get_handler
from hestia.api.security import assert_admin, get_current_user
from hestia.api.schemas.requests import LogSettingsUpdateRequest
from hestia.domain.auth.models import User
from hestia.handler import RequestHandler
from hestia.infrastructure.logging.audit import audit
from hestia.infrastructure.logging.config import set_log_level
from hestia.infrastructure.logging.query import export_logs, query_logs

router = APIRouter()


@router.get("/logs")
def list_logs(
    h: RequestHandler = Depends(get_handler),
    user: User = Depends(get_current_user),
    log_type: Literal["system", "audit"] = "system",
    level: Optional[str] = None,
    search: Optional[str] = None,
    since: Optional[str] = None,
    until: Optional[str] = None,
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
):
    assert_admin(user)
    audit.admin_action(actor_id=str(user.id), action="logs_view", target=log_type)
    entries, total = query_logs(
        h.container.settings.log_dir, log_type, level=level, search=search,
        since=since, until=until, limit=limit, offset=offset,
    )
    return {"entries": entries, "total": total}


@router.get("/logs/export")
def export_logs_endpoint(
    h: RequestHandler = Depends(get_handler),
    user: User = Depends(get_current_user),
    log_type: Literal["system", "audit"] = "system",
    level: Optional[str] = None,
    search: Optional[str] = None,
    since: Optional[str] = None,
    until: Optional[str] = None,
    format: Literal["ndjson", "csv"] = "ndjson",
):
    assert_admin(user)
    audit.admin_action(
        actor_id=str(user.id), action="logs_export", target=log_type,
        detail={"level": level, "search": search, "since": since, "until": until, "format": format},
    )
    media_type = "application/x-ndjson" if format == "ndjson" else "text/csv"
    filename = f"{log_type}-logs.{('ndjson' if format == 'ndjson' else 'csv')}"
    lines = export_logs(
        h.container.settings.log_dir, log_type, level=level, search=search,
        since=since, until=until, format=format,
    )
    return StreamingResponse(
        lines, media_type=media_type,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/logs/settings")
def get_log_settings(
    h: RequestHandler = Depends(get_handler),
    user: User = Depends(get_current_user),
):
    assert_admin(user)
    settings = h.container.settings
    return {
        "log_level": settings.log_level,
        "log_dir": str(settings.log_dir),
        "log_to_console": settings.log_to_console,
    }


@router.put("/logs/settings")
def update_log_settings(
    req: LogSettingsUpdateRequest,
    h: RequestHandler = Depends(get_handler),
    user: User = Depends(get_current_user),
):
    assert_admin(user)
    try:
        set_log_level(h.container.settings, req.log_level)
    except ValueError as e:
        raise HTTPException(400, str(e))
    audit.admin_action(actor_id=str(user.id), action="log_level_change", target="logging", detail={"log_level": req.log_level})
    return {"ok": True, "log_level": h.container.settings.log_level}
