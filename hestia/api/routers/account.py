from fastapi import APIRouter, Depends, HTTPException

from hestia.api.dependencies import get_handler
from hestia.api.security import get_current_user
from hestia.domain.auth.models import User
from hestia.handler import RequestHandler

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
    svc.change_password(user.id, current_pw, new_pw)
    return {"status": "ok"}
