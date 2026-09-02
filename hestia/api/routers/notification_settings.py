from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from hestia.api.dependencies import get_handler
from hestia.api.security import assert_admin, get_current_user
from hestia.domain.auth.models import User
from hestia.handler import RequestHandler
from hestia.infrastructure.logging.audit import audit

router = APIRouter()


def _notification_svc(h: RequestHandler):
    svc = h.container.services.get("notifications")
    if svc is None:
        raise HTTPException(503, "Notification service unavailable.")
    return svc


@router.get("/notification-settings")
def get_notification_settings(
    h: RequestHandler = Depends(get_handler),
    user: User = Depends(get_current_user),
):
    assert_admin(user)
    return _notification_svc(h).get_welcome_settings()


@router.put("/notification-settings")
def update_notification_settings(
    req: dict,
    h: RequestHandler = Depends(get_handler),
    user: User = Depends(get_current_user),
):
    assert_admin(user)
    _notification_svc(h).update_welcome_settings(
        welcome_title=req.get("welcome_title", ""), welcome_body=req.get("welcome_body", ""),
    )
    audit.admin_action(actor_id=str(user.id), action="notification_settings_update", target="welcome_message")
    return {"ok": True}
