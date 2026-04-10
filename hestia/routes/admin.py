from fastapi import APIRouter, Depends
from fastapi.exceptions import HTTPException

from hestia.handler import RequestHandler
from hestia.container import Container
from hestia.utils.security import get_current_user
from hestia.utils.deps import get_container, get_handler
from hestia.schemas.api import User


"""
TODO:
- user management methods:
    - list_users
    - list user roles, orgs, and permissions
    - add_user
    - del_user
    - set/change user roles and permissions (org association)
    - reset user passwords -> set must-chant_pw
    - revoke user access
    - set user start and expiration 

    - list roles
    - add roles
    - assign roles
    - delete roles
    - set role permissions
    - change role permissions

    - list permissions
    - delete permissions

    - list orgs
    - add orgs
    - delete orgs
    - change orgs
    - add/remove user to rogs
    - list org users
    - add org-role to a user
"""

router = APIRouter()

@router.get("/users")
async def get_users(
    h: RequestHandler = Depends(get_handler),
    user: User = Depends(get_current_user)):
    
    svc = h.container.services.get("users")

    return svc.list_users()

@router.post("/users/create")
async def create_user(
    req,
    h: RequestHandler = Depends(get_handler),
    user: User = Depends(get_current_user)):

    svc = h.container.services.get("users")

    username = req.get("username")
    password = req.get("password")

    if not username or not password:
        raise HTTPException(400, "Username and password required")

    try:
        user_id = svc.create_user(username, password)
        return {"ok": True, "user_id": user_id.hex()}
    except ValueError as e:
        raise HTTPException(400, str(e))