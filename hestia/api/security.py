from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

import jwt
from fastapi import Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer

from hestia.api.dependencies import get_container
from hestia.container import Container
from hestia.domain.auth.models import User

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/login")


def create_access_token(
    user_id: uuid.UUID,
    *,
    key: str,
    algorithm: str = "HS256",
    expiration_time: int = 360,
) -> str:
    expire = datetime.now(timezone.utc) + timedelta(minutes=expiration_time)
    payload = {"sub": user_id.hex, "exp": expire}
    return jwt.encode(payload, key, algorithm=algorithm)


def get_current_user(
    token: str = Depends(oauth2_scheme),
    c: Container = Depends(get_container),
) -> User:
    auth_svc = c.services.get("auth")
    user_svc = c.services.get("users")
    auth_config = auth_svc.config if auth_svc else None

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

    user = user_svc.load_user_profile(user_id)
    if not user:
        raise HTTPException(401, "User not found")
    return user
