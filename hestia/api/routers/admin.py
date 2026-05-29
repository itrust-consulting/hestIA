import uuid

from fastapi import APIRouter, Depends, HTTPException, Request

from hestia.api.dependencies import get_handler
from hestia.api.security import get_current_user
from hestia.api.schemas.requests import CreateUserRequest, CreateOrgRequest, UpdateOrgRequest
from hestia.domain.auth.models import User
from hestia.handler import RequestHandler

router = APIRouter()


def require_admin():
    def guard(user: User = Depends(get_current_user)) -> User:
        if not user.permissions.is_admin:
            raise HTTPException(403, "Admin access required.")
        return user
    return guard


def require_tenant_moderator(param: str = "org_id"):
    def guard(request: Request, user: User = Depends(get_current_user)) -> User:
        if user.permissions.is_admin:
            return user
        org_id = int(request.path_params[param])
        if org_id not in user.permissions.moderated_tenants:
            raise HTTPException(403, "Tenant moderator access required.")
        return user
    return guard


def require_tenant_role_assigner(param: str = "org_id"):
    def guard(request: Request, user: User = Depends(get_current_user)) -> User:
        if user.permissions.is_admin:
            return user
        org_id = int(request.path_params[param])
        if org_id not in user.permissions.role_assignable_tenants:
            raise HTTPException(403, "Only the tenant moderator can assign roles.")
        return user
    return guard


def require_admin_or_moderator():
    def guard(user: User = Depends(get_current_user)) -> User:
        if not user.permissions.is_admin and not user.permissions.moderated_tenants:
            raise HTTPException(403, "Admin or moderator access required.")
        return user
    return guard


def require_collection_owner_moderator(collection_param: str = "collection_id"):
    """Admin, or moderator of the tenant that owns the collection."""
    def guard(request: Request, user: User = Depends(get_current_user),
              h: RequestHandler = Depends(get_handler)) -> User:
        if user.permissions.is_admin:
            return user
        collection_id = request.path_params[collection_param]
        svc = h.container.services.get("users")
        if svc is None:
            raise HTTPException(503, "User service unavailable.")
        grants = svc.get_collection_grants(collection_id)
        owner = grants.get("owner")
        if not owner or owner["id"] not in user.permissions.moderated_tenants:
            raise HTTPException(403, "Only the collection owner's moderator may manage access.")
        return user
    return guard


# Users
@router.get("/users")
def get_users(
    h: RequestHandler = Depends(get_handler),
    user: User = Depends(require_admin_or_moderator()),
):
    return h.container.services.get("users").list_users()


@router.get("/users/user/{uid}")
def get_user_profile(
    uid: str,
    h: RequestHandler = Depends(get_handler),
    user: User = Depends(require_admin()),
):
    return h.container.services.get("users").load_user_profile(uuid.UUID(uid))


@router.patch("/users/user/{uid}")
def update_user(
    uid: str,
    req: dict,
    h: RequestHandler = Depends(get_handler),
    user: User = Depends(require_admin()),
):
    svc = h.container.services.get("users")
    svc.update_user(
        uuid.UUID(uid),
        username=req.get("username", ""),
        email=req.get("email", ""),
        first_name=req.get("first_name", ""),
        last_name=req.get("last_name", ""),
        expires_at=req.get("expires_at"),
        role_ids=req.get("role_ids"),
        new_password=req.get("new_password") or None,
    )
    return {"ok": True}


@router.delete("/users/user/{uid}")
def delete_user(
    uid: str,
    h: RequestHandler = Depends(get_handler),
    user: User = Depends(require_admin()),
):
    h.container.services.get("users").delete_user(uuid.UUID(uid))
    return {"ok": True}


@router.post("/users/create")
def create_user(
    req: CreateUserRequest,
    h: RequestHandler = Depends(get_handler),
    user: User = Depends(require_admin()),
):
    if not req.username or not req.password:
        raise HTTPException(400, "Username and password required")
    user_id = h.container.services.get("users").create_user(
        username=req.username,
        email=req.email,
        password=req.password,
        first_name=req.first_name,
        last_name=req.last_name,
        roles=req.roles,
        organization=req.organization,
        expires_at=req.expires_at,
    )
    return {"ok": True, "user_id": str(user_id)}


# Organizations
@router.get("/organizations")
def list_organizations(
    h: RequestHandler = Depends(get_handler),
    user: User = Depends(require_admin_or_moderator()),
):
    """Lightweight org list for dropdowns — requires admin or moderator authentication."""
    svc = h.container.services.get("users")
    if svc is None:
        return {"organizations": []}
    return {"organizations": svc.list_orgs()}


@router.get("/organizations/list")
def list_organizations_alias(
    h: RequestHandler = Depends(get_handler),
    user: User = Depends(get_current_user),
):
    svc = h.container.services.get("users")
    if svc is None:
        return {"organizations": []}
    return {"organizations": svc.list_orgs()}


@router.post("/organizations/create")
def create_organization(
    req: CreateOrgRequest,
    h: RequestHandler = Depends(get_handler),
    user: User = Depends(require_admin()),
):
    if not req.name or not req.abbreviation:
        raise HTTPException(400, "Organization name and abbreviation required")
    h.container.services.get("users").create_org(name=req.name, abbreviation=req.abbreviation)
    return {"ok": True}


@router.put("/organizations/{org_id}")
def update_organization(
    org_id: int,
    req: UpdateOrgRequest,
    h: RequestHandler = Depends(get_handler),
    user: User = Depends(require_admin()),
):
    if not req.name or not req.abbreviation:
        raise HTTPException(400, "Organization name and abbreviation required")
    h.container.services.get("users").update_org(org_id=org_id, name=req.name, abbreviation=req.abbreviation)
    return {"ok": True}


@router.delete("/organizations/{org_id}")
def delete_organization(
    org_id: int,
    h: RequestHandler = Depends(get_handler),
    user: User = Depends(require_admin()),
):
    h.container.services.get("users").delete_org(org_id=org_id)
    return {"ok": True}


@router.get("/organizations/{org_id}/members")
def get_organization_members(
    org_id: int,
    h: RequestHandler = Depends(get_handler),
    user: User = Depends(require_tenant_moderator("org_id")),
):
    members = h.container.services.get("users").get_org_users(org_id=org_id)
    return {"members": members}


@router.post("/organizations/{org_id}/members/{user_id}")
def add_organization_member(
    org_id: int,
    user_id: str,
    h: RequestHandler = Depends(get_handler),
    user: User = Depends(require_tenant_moderator("org_id")),
):
    h.container.services.get("users").add_user_to_org(
        user_id=uuid.UUID(user_id), org_id=org_id
    )
    return {"ok": True}


@router.delete("/organizations/{org_id}/members/{user_id}")
def remove_organization_member(
    org_id: int,
    user_id: str,
    h: RequestHandler = Depends(get_handler),
    user: User = Depends(require_tenant_moderator("org_id")),
):
    h.container.services.get("users").remove_user_from_org(
        user_id=uuid.UUID(user_id), org_id=org_id
    )
    return {"ok": True}


# Tenant collections
@router.get("/organizations/{org_id}/collections")
def get_tenant_collections(
    org_id: int,
    h: RequestHandler = Depends(get_handler),
    user: User = Depends(require_tenant_moderator("org_id")),
):
    svc = h.container.services.get("users")
    info = svc.get_tenant_collection_info(org_id)

    try:
        col_meta = {
            c["name"]: c
            for c in h.container.providers["db"].collections.get("collections", [])
        }
    except Exception:
        col_meta = {}

    for col in info["owned"]:
        meta = col_meta.get(col["id"], {})
        col["points_count"] = meta.get("points_count", 0)
        col["status"] = meta.get("status", "unknown")

    for col in info["accessible"]:
        meta = col_meta.get(col["id"], {})
        col["points_count"] = meta.get("points_count", 0)
        col["status"] = meta.get("status", "unknown")

    return info


@router.put("/organizations/{org_id}/collections/{collection_id}")
def add_tenant_collection(
    org_id: int,
    collection_id: str,
    req: dict,
    h: RequestHandler = Depends(get_handler),
    user: User = Depends(require_collection_owner_moderator("collection_id")),
):
    role = req.get("role", "access")
    if role not in ("owner", "access"):
        raise HTTPException(400, "role must be 'owner' or 'access'")
    raw_cap = req.get("max_classification")
    max_classification = int(raw_cap) if raw_cap is not None else None
    h.container.services.get("users").add_tenant_collection(
        org_id, collection_id, role=role, max_classification=max_classification
    )
    return {"ok": True}


@router.delete("/organizations/{org_id}/collections/{collection_id}")
def remove_tenant_collection(
    org_id: int,
    collection_id: str,
    h: RequestHandler = Depends(get_handler),
    user: User = Depends(require_collection_owner_moderator("collection_id")),
):
    h.container.services.get("users").remove_tenant_collection(org_id, collection_id)
    return {"ok": True}


# Member management (moderator)
@router.patch("/organizations/{org_id}/members/{user_id}/classification")
def set_member_classification(
    org_id: int,
    user_id: str,
    req: dict,
    h: RequestHandler = Depends(get_handler),
    user: User = Depends(require_tenant_moderator("org_id")),
):
    level = int(req.get("level", 0))
    h.container.services.get("users").set_member_classification(uuid.UUID(user_id), org_id, level)
    return {"ok": True}


@router.patch("/organizations/{org_id}/members/{user_id}/role")
def set_member_tenant_role(
    org_id: int,
    user_id: str,
    req: dict,
    h: RequestHandler = Depends(get_handler),
    user: User = Depends(require_tenant_role_assigner("org_id")),
):
    role = req.get("role")  # 'moderator', 'co-moderator', or None
    h.container.services.get("users").set_member_tenant_role(uuid.UUID(user_id), org_id, role)
    return {"ok": True}


# Collections (create)
@router.post("/collections/create")
def create_collection(
    req: dict,
    h: RequestHandler = Depends(get_handler),
    user: User = Depends(require_admin_or_moderator()),
):
    name = (req.get("name") or "").strip()
    if not name:
        raise HTTPException(400, "Collection name required.")
    db = h.container.providers.get("db")
    if db is None:
        raise HTTPException(503, "Database not available.")
    pipeline = h.container.services.get("ingestion")
    if pipeline is None:
        raise HTTPException(503, "Ingestion service not available.")
    dense_dim = len(pipeline.dense_encoder.encode("probe").vector)
    owner_org_id: int | None = req.get("owner_org_id") or None
    try:
        db.initialize(name, {"dense_dim": dense_dim, "create_indexes": True, "owner_org_id": owner_org_id})
    except Exception as e:
        raise HTTPException(500, f"Failed to create collection: {e}")
    if owner_org_id is not None:
        svc = h.container.services.get("users")
        if svc:
            svc.add_tenant_collection(owner_org_id, name, role="owner")
    return {"ok": True, "name": name}


# Roles
@router.get("/roles")
def get_roles(
    h: RequestHandler = Depends(get_handler),
    user: User = Depends(require_admin()),
):
    return h.container.services.get("users").list_roles()
