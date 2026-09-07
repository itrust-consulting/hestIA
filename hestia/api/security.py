from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

import jwt
from fastapi import Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer

from hestia.api.dependencies import get_container
from hestia.container import Container
from hestia.domain.auth.models import User
from hestia.domain.auth.users import now_epoch
from hestia.domain.exceptions import ConfigurationError

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/login")

# Symmetric algorithms only -- matches this app's shared-secret signing
# model. Never pass an unvalidated algorithm string into jwt.decode's
# algorithms=, since PyJWT trusts whatever is in that list, including "none".
_ALLOWED_JWT_ALGORITHMS = {"HS256", "HS384", "HS512"}


# @MRS-003
def assert_admin(user: User) -> None:
    if not user.permissions.is_admin:
        raise HTTPException(403, "Admin access required.")


def assert_admin_or_moderator(user: User) -> None:
    if not user.permissions.is_admin and not user.permissions.moderated_tenants:
        raise HTTPException(403, "Admin or moderator access required.")


def assert_org_member(user: User, org_id: int) -> None:
    if user.permissions.is_admin:
        return
    if org_id not in {o["id"] for o in user.orgs}:
        raise HTTPException(403, "You must be a member of this tenant.")


def assert_tenant_moderator(user: User, org_id: int) -> None:
    if user.permissions.is_admin:
        return
    if org_id not in user.permissions.moderated_tenants:
        raise HTTPException(403, "Tenant moderator access required.")


def assert_tenant_role_assigner(user: User, org_id: int) -> None:
    if user.permissions.is_admin:
        return
    if org_id not in user.permissions.role_assignable_tenants:
        raise HTTPException(403, "Only the tenant moderator can assign roles.")


def assert_collection_moderator(user: User, collection_id: str, h) -> None:
    """Raise HTTP 403 unless the user is admin or moderates the org that owns the collection."""
    if user.permissions.is_admin:
        return
    svc = h.container.services.get("users")
    if svc is None:
        raise HTTPException(503, "User service unavailable.")
    grants = svc.get_collection_grants(collection_id)
    owner = grants.get("owner")
    if not owner or owner["id"] not in user.permissions.moderated_tenants:
        raise HTTPException(403, "Only the collection owner's moderator may perform this action.")



def _issue_token(result, auth) -> dict:
    token = create_access_token(
        result.user_id,
        key=auth.config.token_secret_key,
        algorithm=auth.config.token_encoding_alg,
        expiration_time=auth.config.token_lifetime_minutes,
    )
    auth.local.repo.record_login(id=result.user_id, ts=now_epoch())
    return {"access_token": token, "token_type": "bearer", "must_change_pw": result.must_change_pw}


def create_access_token(
    user_id: uuid.UUID,
    *,
    key: str,
    algorithm: str = "HS256",
    expiration_time: int = 360,
) -> str:
    if algorithm not in _ALLOWED_JWT_ALGORITHMS:
        raise ConfigurationError(f"Unsupported JWT signing algorithm: '{algorithm}'")
    expire = datetime.now(timezone.utc) + timedelta(minutes=expiration_time)
    # jti lets a specific token be revoked (see get_current_user below and
    # /logout in auth.py) despite the token itself being a stateless JWT --
    # without it, "logout" can only delete the browser's cookie and the
    # captured token would otherwise stay valid for its full lifetime.
    payload = {"sub": user_id.hex, "exp": expire, "jti": uuid.uuid4().hex}
    return jwt.encode(payload, key, algorithm=algorithm)


# @MRS-062
def get_current_user(
    token: str = Depends(oauth2_scheme),
    c: Container = Depends(get_container),
) -> User:
    auth_svc = c.services.get("auth")
    user_svc = c.services.get("users")
    auth_config = auth_svc.config if auth_svc else None

    if auth_config.token_encoding_alg not in _ALLOWED_JWT_ALGORITHMS:
        raise HTTPException(500, "Invalid token signing algorithm configured.")

    try:
        payload = jwt.decode(
            token,
            key=auth_config.token_secret_key,
            algorithms=[auth_config.token_encoding_alg],
        )
        user_id_hex = payload.get("sub")
        if not user_id_hex:
            raise HTTPException(401, "Invalid authentication payload")
        user_id = uuid.UUID(user_id_hex)
    except jwt.ExpiredSignatureError:
        raise HTTPException(401, "Token expired")
    except jwt.DecodeError:
        raise HTTPException(401, "Invalid token")

    jti = payload.get("jti")
    if jti and auth_svc.local.repo.is_token_revoked(jti):
        raise HTTPException(401, "Token has been revoked")

    user = user_svc.load_user_profile(user_id)
    if not user:
        raise HTTPException(401, "User not found")
    return user
