# auth_jwt.py
from fastapi import Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer

from datetime import datetime, timedelta, timezone
import jwt

from hestia.container import Container
from hestia.utils.deps import get_container
from hestia.schemas.api import User

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")

def create_access_token(
        user_id_bytes: bytes,
        *,
        key: str,
        algorithm: str = "HS256",
        expiration_time: int = 15):
    
    expire = datetime.now(timezone.utc) + timedelta(minutes=expiration_time)
    payload = {
        "sub": user_id_bytes.hex(),   # store user_id in safe serializable form
        "exp": expire,
    }
    return jwt.encode(payload, key, algorithm=algorithm)


def get_current_user(token: str = Depends(oauth2_scheme),
                     c: Container = Depends(get_container)) -> User:
    """
    Decode JWT, validate, fetch the user record.
    """
    user_services = c.services.get("users")
    auth_config = c.services.get("auth").config

    try:
        payload = jwt.decode(
            token, 
            key=auth_config.token_secret_key, 
            algorithms=[auth_config.token_encoding_alg])
        user_id_hex = payload.get("sub")
        if not user_id_hex:
            raise HTTPException(
                status_code=401, 
                detail="Invalid authentication payload")
        
        user_id = bytes.fromhex(user_id_hex)

    except jwt.exceptions.ExpiredSignatureError or jwt.exceptions.DecodeError:
        raise HTTPException(status_code=401, detail="Invalid or expired token")

    # Fetch user from DB (minimal)
    user = user_services.load_user_profile(user_id)
    if not user:
        raise HTTPException(status_code=401, detail="User not found")

    return user


