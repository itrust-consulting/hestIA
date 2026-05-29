import secrets

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import RedirectResponse
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel

from hestia.api.dependencies import get_container
from hestia.api.limiter import limiter, login_rate_limit
from hestia.api.security import _issue_token
from hestia.container import Container

router = APIRouter()


@router.post("/login")
@limiter.limit(login_rate_limit)
async def login(
    request: Request,
    form_data: OAuth2PasswordRequestForm = Depends(),
    c: Container = Depends(get_container),
):
    auth = c.services.get("auth")
    result = auth.authenticate(form_data.username, form_data.password)
    if not result.success:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=result.message)
    return _issue_token(result, auth)


@router.get("/auth/oidc/authorize")
async def oidc_authorize(
    redirect_uri: str,
    c: Container = Depends(get_container),
):
    auth = c.services.get("auth")
    if not auth or not auth.oidc:
        raise HTTPException(status_code=400, detail="OIDC is not enabled.")
    state = secrets.token_urlsafe(16)
    url = auth.oidc.get_authorization_url(redirect_uri=redirect_uri, state=state)
    return {"url": url, "state": state}


@router.get("/auth/oidc/logout")
async def oidc_logout(
    redirect_uri: str,
    c: Container = Depends(get_container),
):
    auth = c.services.get("auth")
    if not auth or not auth.oidc:
        raise HTTPException(status_code=400, detail="OIDC not enabled.")
    return RedirectResponse(url=auth.oidc.get_logout_url(redirect_uri), status_code=302)


class OIDCCallbackRequest(BaseModel):
    code: str
    redirect_uri: str
    state: str | None = None


@router.post("/auth/oidc/callback")
async def oidc_callback(
    body: OIDCCallbackRequest,
    c: Container = Depends(get_container),
):
    auth = c.services.get("auth")
    if not auth or not auth.oidc:
        raise HTTPException(status_code=400, detail="OIDC is not enabled.")
    result = auth.authenticate_oidc(body.code, body.redirect_uri)
    if not result.success:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=result.message)
    return _issue_token(result, auth)
