import base64
import hashlib
import secrets

import jwt
from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import RedirectResponse
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel

from hestia.api.dependencies import get_container
from hestia.api.limiter import limiter, login_key, login_rate_limit, stash_login_identifier
from hestia.api.security import _issue_token, get_current_user, oauth2_scheme
from hestia.container import Container
from hestia.domain.auth.models import User
from hestia.domain.auth.users import now_epoch

router = APIRouter()


@router.post("/login")
@limiter.limit(login_rate_limit, key_func=login_key)
async def login(
    request: Request,
    form_data: OAuth2PasswordRequestForm = Depends(),
    c: Container = Depends(get_container),
    _stash: None = Depends(stash_login_identifier),
):
    auth = c.services.get("auth")
    result = auth.authenticate(form_data.username, form_data.password)
    if not result.success:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=result.message)
    return _issue_token(result, auth)


@router.post("/logout")
async def logout(
    user: User = Depends(get_current_user),
    token: str = Depends(oauth2_scheme),
    c: Container = Depends(get_container),
):
    """Called by the frontend's /api/logout handler while the token is still
    valid (before it deletes the cookie) -- get_current_user gives us a
    verified identity rather than trusting an unauthenticated claim. Revokes
    this specific token (by its jti) so a copy captured before logout -- via
    XSS, a log leak, a compromised proxy -- can't keep authenticating as this
    user for the rest of its lifetime; older tokens minted before jti existed
    have nothing to revoke and just fall through."""
    auth = c.services.get("auth")
    if auth is not None:
        auth.audit_logout(user_id=str(user.id), username=user.username, source=user.auth_source)
        payload = jwt.decode(
            token, key=auth.config.token_secret_key, algorithms=[auth.config.token_encoding_alg],
        )
        jti = payload.get("jti")
        if jti:
            auth.local.repo.revoke_token(jti=jti, ts=now_epoch())
    return {"ok": True}


def _assert_redirect_uri_allowed(auth, redirect_uri: str) -> None:
    """The frontend's own cookie-based state check is the primary CSRF guard
    for this flow (see the BFF's /api/auth/callback handler); this allowlist
    is what stops the backend's own OIDC endpoints from forwarding an
    arbitrary, attacker-supplied redirect_uri straight into the IdP URL when
    called directly rather than through the frontend. Left unenforced
    (permissive) until an operator configures OIDC_REDIRECT_ALLOWLIST, so
    existing deployments aren't broken by upgrading."""
    allowlist = auth.oidc.settings.redirect_uri_allowlist
    if allowlist and redirect_uri not in allowlist:
        raise HTTPException(status_code=400, detail="redirect_uri is not allowed.")


def _generate_pkce_pair() -> tuple[str, str]:
    """(code_verifier, code_challenge) per RFC 7636's S256 method. Hardening
    against authorization-code interception -- not load-bearing for this
    app's confidential client, but standard and cheap to add."""
    verifier = secrets.token_urlsafe(64)
    digest = hashlib.sha256(verifier.encode("ascii")).digest()
    challenge = base64.urlsafe_b64encode(digest).rstrip(b"=").decode("ascii")
    return verifier, challenge


@router.get("/auth/oidc/authorize")
@limiter.limit("10/minute")
async def oidc_authorize(
    request: Request,
    redirect_uri: str,
    c: Container = Depends(get_container),
):
    auth = c.services.get("auth")
    if not auth or not auth.oidc:
        raise HTTPException(status_code=400, detail="OIDC is not enabled.")
    _assert_redirect_uri_allowed(auth, redirect_uri)
    state = secrets.token_urlsafe(16)
    code_verifier, code_challenge = _generate_pkce_pair()
    url = auth.oidc.get_authorization_url(redirect_uri=redirect_uri, state=state, code_challenge=code_challenge)
    return {"url": url, "state": state, "code_verifier": code_verifier}


@router.get("/auth/oidc/logout")
@limiter.limit("10/minute")
async def oidc_logout(
    request: Request,
    redirect_uri: str,
    c: Container = Depends(get_container),
):
    auth = c.services.get("auth")
    if not auth or not auth.oidc:
        raise HTTPException(status_code=400, detail="OIDC not enabled.")
    _assert_redirect_uri_allowed(auth, redirect_uri)
    return RedirectResponse(url=auth.oidc.get_logout_url(redirect_uri), status_code=302)


class OIDCCallbackRequest(BaseModel):
    code: str
    redirect_uri: str
    state: str | None = None
    code_verifier: str | None = None


@router.post("/auth/oidc/callback")
@limiter.limit("10/minute")
async def oidc_callback(
    request: Request,
    body: OIDCCallbackRequest,
    c: Container = Depends(get_container),
):
    auth = c.services.get("auth")
    if not auth or not auth.oidc:
        raise HTTPException(status_code=400, detail="OIDC is not enabled.")
    if not body.state:
        # The frontend's BFF layer generates and validates state against a
        # short-lived cookie before ever reaching this endpoint; this is a
        # backstop against a caller that skips that step entirely, not a
        # substitute for it -- the backend has no session of its own to
        # compare the value against.
        raise HTTPException(status_code=400, detail="Missing OIDC state.")
    result = await auth.authenticate_oidc(body.code, body.redirect_uri, code_verifier=body.code_verifier)
    if not result.success:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=result.message)
    return _issue_token(result, auth)
