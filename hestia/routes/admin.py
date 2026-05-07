from fastapi import APIRouter, Depends
from fastapi.exceptions import HTTPException

from hestia.handler import RequestHandler
from hestia.utils.security import get_current_user
from hestia.utils.deps import get_handler
from hestia.schemas.api import User, CreateUserRequest, CreateOrgRequest


"""
TODO:
- user management methods:
    - list user roles, orgs, and permissions
    - add_user
    - del_user
    - set/change user roles and permissions (org association)
    - reset user passwords -> set must-change_pw
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

def require_permission(permission_name: str):
    def guard(user: User = Depends(get_current_user)) -> User:
        value = getattr(user.permissions, permission_name, None)

        if not value:
            raise HTTPException(
                status_code=403,
                detail=f"Permission denied."
            )

        return user
    return guard

# Users mgmt
@router.get("/users")
async def get_users(
    h: RequestHandler = Depends(get_handler),
    user: User = Depends(require_permission("user_management"))
    ):

    svc = h.container.services.get("users")
    return svc.list_users()

@router.get("/users/user/{uid}")
async def get_user_profile(
    uid,
    h: RequestHandler = Depends(get_handler),
    user: User = Depends(require_permission("user_management"))
    ):
    
    svc = h.container.services.get("users")

    return svc.load_user_profile(bytes.fromhex(uid))

@router.post("/users/create")
async def create_user(
    req: CreateUserRequest,
    h: RequestHandler = Depends(get_handler),
    user: User = Depends(require_permission("user_management"))
    ):

    svc = h.container.services.get("users")

    if not req.username or not req.password:
        raise HTTPException(400, "Username and password required")

    try:
        user_id = svc.create_user(
            username=req.username, 
            email=req.email, 
            password = req.password,
            first_name = req.first_name,
            last_name = req.last_name,
            role = req.role,
            organization = req.organization,
            expires_at=req.expires_at,
            permissions=req.permissions
        )

        return {"ok": True, "user_id": user_id.hex()}
    except ValueError as e:
        raise HTTPException(400, str(e))

# org mgmt
@router.get("/organizations")
async def get_organizations(    
    h: RequestHandler = Depends(get_handler),
    user: User = Depends(require_permission("user_management"))
    ):

    svc = h.container.services.get("users")
    return svc.list_orgs()


@router.post("/organizations/create")
async def create_organization(
    req: CreateOrgRequest,
    h: RequestHandler = Depends(get_handler),
    user: User = Depends(require_permission("user_management"))
    ):

    svc = h.container.services.get("users")

    if not req.name and not req.abbreviation:
        raise HTTPException(400, "Organization name and abbreviation required")
    
    try:
        svc.create_org(name=req.name, abbreviation=req.abbreviation)
        return {"ok": True}
    except ValueError as e:
        raise HTTPException(400, str(e))


# role mgmt
@router.get("/roles")
async def get_roles(    
    h: RequestHandler = Depends(get_handler),
    user: User = Depends(require_permission("user_management"))
    ):

    svc = h.container.services.get("users")
    return svc.list_roles()

@router.get("/roles/{rid}/permissions")
async def get_role_permissions(
    rid,
    h: RequestHandler = Depends(get_handler),
    user: User = Depends(require_permission("user_management"))
    ):

    svc = h.container.services.get("users")
    return svc.list_role_permissions(int(rid))



# permission mgmt
@router.get("/permissions")
async def list_permissions(    
    h: RequestHandler = Depends(get_handler),
    user: User = Depends(require_permission("user_management"))
    ):

    svc = h.container.services.get("users")
    return svc.list_permissions()

@router.post("/permissions")
async def create_permission(
    req,
    h: RequestHandler = Depends(get_handler),
    user: User = Depends(require_permission("system_management"))
    ):

    svc = h.container.services.get("users")
    name = req.get("name")
    description = req.get("description")
    value_type = req.get("value_type")
    
    svc.create_permission(name, description, value_type)