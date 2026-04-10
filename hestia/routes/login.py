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

    result = auth.authenticate(form_data.username, form_data.password)
    if not result.success:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=result.message,
        )
    access_token = create_access_token(result.user_id)
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "must_change_pw": result.must_change_pw,
    }