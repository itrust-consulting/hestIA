from fastapi import APIRouter, Depends, HTTPException

from hestia.api.dependencies import get_handler
from hestia.api.security import get_current_user
from hestia.domain.auth.models import User
from hestia.domain.auth.users import now_epoch
from hestia.handler import RequestHandler
from hestia.infrastructure.logging.audit import audit, audited

router = APIRouter()


@router.get("/account")
def get_account(
    h: RequestHandler = Depends(get_handler),
    user: User = Depends(get_current_user),
):
    svc = h.container.services.get("users")
    return svc.load_user_profile(user.id)


@router.patch("/account/password")
def change_password(
    req: dict,
    h: RequestHandler = Depends(get_handler),
    user: User = Depends(get_current_user),
):
    current_pw = req.get("current_pw")
    new_pw = req.get("new_pw")
    if not current_pw or not new_pw:
        raise HTTPException(400, "Missing fields: current_pw, new_pw")

    svc = h.container.services.get("users")
    with audited(audit.user_action, actor_id=str(user.id), action="password_change"):
        svc.change_password(user.id, current_pw, new_pw)
    return {"status": "ok"}


@router.post("/account/heartbeat")
def heartbeat(
    h: RequestHandler = Depends(get_handler),
    user: User = Depends(get_current_user),
):
    h.container.services.get("users").repo.touch_last_seen(id=user.id, ts=now_epoch())
    n_svc = h.container.services.get("notifications")
    return {"ok": True, "unread_notifications": n_svc.unread_count(user.id) if n_svc else 0}