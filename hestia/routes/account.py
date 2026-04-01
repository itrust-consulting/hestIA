from fastapi import APIRouter, Depends
from fastapi.exceptions import HTTPException
from hestia.utils.deps import get_handler
from hestia.handler import RequestHandler

from hestia.utils.security import User, get_current_user


router = APIRouter()

@router.get("/account")
def get_account(
        h: RequestHandler = Depends(get_handler),
        user: User  = Depends(get_current_user)
    ):
    svc = h.container.services.get("auth")
    return svc.load_user(user.id.bytes)

@router.patch("/account/password")
def change_passwrd(
        req: dict,
        h: RequestHandler = Depends(get_handler),
        user: User  = Depends(get_current_user)
    ):

    current_pw = req.get("current_pw")
    new_pw = req.get("new_pw")
    if not current_pw or not new_pw:
        raise HTTPException(400, "Missing Fields.")
    
    svc = h.container.services.get("auth")

    ok = svc.change_password(user.id.bytes, current_pw, new_pw)
    if not ok:
        raise HTTPException(401, "Incorrect current password.")
    return {"status": "ok"}