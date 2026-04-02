from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm

from hestia.container import Container
from hestia.utils.deps import get_container
from hestia.utils.security import create_access_token

router = APIRouter()

@router.post("/login")
async def login(form_data: OAuth2PasswordRequestForm = Depends(),
                c: Container = Depends(get_container)):
    auth = c.services.get("auth")
    ok, msg, user = auth.authenticate(form_data.username, form_data.password)
    if not ok:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=msg,
        )
    access_token = create_access_token(user["id"])
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "must_change_pw": bool(user["must_change_pw"]),
    }