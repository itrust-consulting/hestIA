# auth_jwt.py
from fastapi import Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer

from datetime import datetime, timedelta, timezone
import jwt

from hestia.settings import SECRET_KEY
from hestia.container import Container
from hestia.utils.deps import get_container
from hestia.schemas.api import Permissions, User


ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 720

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")

def create_access_token(user_id_bytes: bytes):
    expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    payload = {
        "sub": user_id_bytes.hex(),   # store user_id in safe serializable form
        "exp": expire,
    }
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def get_current_user(token: str = Depends(oauth2_scheme),
                     c: Container = Depends(get_container)) -> User:
    """
    Decode JWT, validate, fetch the user record.
    """
    user_services = c.services.get("auth")
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id_hex = payload.get("sub")
        if not user_id_hex:
            raise HTTPException(
                status_code=401, 
                detail="Invalid authentication payload")
        
        user_id = bytes.fromhex(user_id_hex)

    except jwt.DecodeError:
        raise HTTPException(status_code=401, detail="Invalid or expired token")

    # Fetch user from DB (minimal)
    user = user_services.load_user(user_id)
    if not user:
        raise HTTPException(status_code=401, detail="User not found")

    return user


