import uuid
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException

from hestia.api.dependencies import get_handler
from hestia.api.security import (
    get_current_user,
    assert_admin,
    assert_admin_or_moderator,
    assert_collection_moderator,
    assert_tenant_moderator,
    assert_tenant_role_assigner,
)
from hestia.api.schemas.requests import CreateUserRequest, CreateOrgRequest, UpdateOrgRequest
from hestia.domain.auth.models import User
from hestia.handler import RequestHandler
from hestia.infrastructure.logging.audit import audit
from hestia.infrastructure.logging.query import count_failed_logins

router = APIRouter()

# A few multiples of the frontend's 45s heartbeat interval -- forgiving of
# browsers throttling setInterval in backgrounded tabs.
_ONLINE_THRESHOLD_MS = 3 * 60 * 1000


def _since_7d_str() -> str:
    # Match _JsonFormatter's exact "ts" string shape (config.py) -- plain
    # string comparison in count_failed_logins/_matches needs the same
    # format on both sides, not Python's default +00:00 isoformat() suffix.
    since_dt = datetime.now(timezone.utc) - timedelta(days=7)
    return since_dt.strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"


def _annotate_online(users: list[dict]) -> list[dict]:
    """Adds is_online (from last_seen_at) to each user dict for the overview
    table -- kept cheap (no log scan, no join) since this is the frequently-
    loaded admin list. Conversation/message counts and failed-login history
    live on the per-user detail page instead (get_user_profile below)."""
    now = int(datetime.now(timezone.utc).timestamp() * 1000)
    for u in users:
        last_seen = u.get("last_seen_at")
        u["is_online"] = bool(last_seen and now - last_seen < _ONLINE_THRESHOLD_MS)
    return users


# Users
@router.get("/users")
def get_users(
    h: RequestHandler = Depends(get_handler),
    user: User = Depends(get_current_user),
):
    assert_admin_or_moderator(user)
    svc = h.container.services.get("users")
    if user.permissions.is_admin:
        return {"users": _annotate_online(svc.list_users())}
    seen: set[uuid.UUID] = set()
    result = []
    for org_id in user.permissions.moderated_tenants:
        for u in svc.get_org_users(org_id=org_id):
            if u["id"] not in seen:
                seen.add(u["id"])
                result.append(u)
    return {"users": _annotate_online(result)}


@router.get("/users/user/{uid}")
def get_user_profile(
    uid: str,
    h: RequestHandler = Depends(get_handler),
    user: User = Depends(get_current_user),
):
    assert_admin(user)
    svc = h.container.services.get("users")
    profile = svc.load_user_profile(uuid.UUID(uid))
    if profile is None:
        raise HTTPException(404, "User not found")
    failed = count_failed_logins(h.container.settings.log_dir, since=_since_7d_str())
    return {
        **profile.model_dump(),
        **svc.get_user_activity(uuid.UUID(uid)),
        "failed_logins_7d": failed.get(profile.username, 0),
    }


@router.patch("/users/user/{uid}")
def update_user(
    uid: str,
    req: dict,
    h: RequestHandler = Depends(get_handler),
    user: User = Depends(get_current_user),
):
    assert_admin(user)
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
    audit.admin_action(
        actor_id=str(user.id), action="user_update", target=uid,
        detail={
            "username": req.get("username"), "email": req.get("email"), "role_ids": req.get("role_ids"),
            "expires_at": req.get("expires_at"), "password_reset": bool(req.get("new_password")),
        },
    )
    return {"ok": True}


@router.delete("/users/user/{uid}")
def delete_user(
    uid: str,
    h: RequestHandler = Depends(get_handler),
    user: User = Depends(get_current_user),
):
    assert_admin(user)
    h.container.services.get("users").delete_user(uuid.UUID(uid))
    audit.admin_action(actor_id=str(user.id), action="user_delete", target=uid)
    return {"ok": True}


@router.post("/users/create")
def create_user(
    req: CreateUserRequest,
    h: RequestHandler = Depends(get_handler),
    user: User = Depends(get_current_user),
):
    assert_admin(user)
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
    audit.admin_action(
        actor_id=str(user.id), action="user_create", target=str(user_id),
        detail={"username": req.username, "roles": req.roles, "organization": req.organization},
    )
    return {"ok": True, "user_id": str(user_id)}


# Organizations
@router.get("/organizations")
def list_organizations(
    h: RequestHandler = Depends(get_handler),
    user: User = Depends(get_current_user),
):
    """Lightweight org list for dropdowns — requires admin or moderator authentication."""
    assert_admin_or_moderator(user)
    svc = h.container.services.get("users")
    if svc is None:
        return {"organizations": []}
    return {"organizations": svc.list_orgs()}


@router.get("/organizations/list")
def list_organizations_alias(
    h: RequestHandler = Depends(get_handler),
    user: User = Depends(get_current_user),
):
    assert_admin_or_moderator(user)
    svc = h.container.services.get("users")
    if svc is None:
        return {"organizations": []}
    return {"organizations": svc.list_orgs()}


# @MRS-004
@router.post("/organizations/create")
def create_organization(
    req: CreateOrgRequest,
    h: RequestHandler = Depends(get_handler),
    user: User = Depends(get_current_user),
):
    assert_admin(user)
    if not req.name or not req.abbreviation:
        raise HTTPException(400, "Organization name and abbreviation required")
    created = h.container.services.get("users").create_org(name=req.name, abbreviation=req.abbreviation)
    if not created:
        raise HTTPException(409, "A tenant with that name or abbreviation already exists.")
    audit.admin_action(
        actor_id=str(user.id), action="org_create", target=req.name,
        detail={"abbreviation": req.abbreviation},
    )
    return {"ok": True}


@router.put("/organizations/{org_id}")
def update_organization(
    org_id: int,
    req: UpdateOrgRequest,
    h: RequestHandler = Depends(get_handler),
    user: User = Depends(get_current_user),
):
    assert_admin(user)
    if not req.name or not req.abbreviation:
        raise HTTPException(400, "Organization name and abbreviation required")
    h.container.services.get("users").update_org(org_id=org_id, name=req.name, abbreviation=req.abbreviation)
    audit.admin_action(
        actor_id=str(user.id), action="org_update", target=str(org_id),
        detail={"name": req.name, "abbreviation": req.abbreviation},
    )
    return {"ok": True}


@router.delete("/organizations/{org_id}")
def delete_organization(
    org_id: int,
    h: RequestHandler = Depends(get_handler),
    user: User = Depends(get_current_user),
):
    assert_admin(user)
    h.container.services.get("users").delete_org(org_id=org_id)
    audit.admin_action(actor_id=str(user.id), action="org_delete", target=str(org_id))
    return {"ok": True}


@router.get("/organizations/{org_id}/members")
def get_organization_members(
    org_id: int,
    h: RequestHandler = Depends(get_handler),
    user: User = Depends(get_current_user),
):
    assert_tenant_moderator(user, org_id)
    members = h.container.services.get("users").get_org_users(org_id=org_id)
    return {"members": members}


@router.post("/organizations/{org_id}/members/{user_id}")
def add_organization_member(
    org_id: int,
    user_id: str,
    h: RequestHandler = Depends(get_handler),
    user: User = Depends(get_current_user),
):
    assert_tenant_moderator(user, org_id)
    h.container.services.get("users").add_user_to_org(
        user_id=uuid.UUID(user_id), org_id=org_id
    )
    audit.admin_action(actor_id=str(user.id), action="org_member_add", target=f"{org_id}:{user_id}")
    return {"ok": True}


@router.delete("/organizations/{org_id}/members/{user_id}")
def remove_organization_member(
    org_id: int,
    user_id: str,
    h: RequestHandler = Depends(get_handler),
    user: User = Depends(get_current_user),
):
    assert_tenant_moderator(user, org_id)
    h.container.services.get("users").remove_user_from_org(
        user_id=uuid.UUID(user_id), org_id=org_id
    )
    audit.admin_action(actor_id=str(user.id), action="org_member_remove", target=f"{org_id}:{user_id}")
    return {"ok": True}


# Tenant collections
@router.get("/organizations/{org_id}/collections")
def get_tenant_collections(
    org_id: int,
    h: RequestHandler = Depends(get_handler),
    user: User = Depends(get_current_user),
):
    assert_tenant_moderator(user, org_id)
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
    user: User = Depends(get_current_user),
):
    role = req.get("role", "access")
    if role not in ("owner", "access"):
        raise HTTPException(400, "role must be 'owner' or 'access'")
    if role == "owner":
        assert_admin(user)
    else:
        assert_collection_moderator(user, collection_id, h)
    raw_cap = req.get("max_classification")
    max_classification = int(raw_cap) if raw_cap is not None else None
    h.container.services.get("users").add_tenant_collection(
        org_id, collection_id, role=role, max_classification=max_classification
    )
    if role == "owner":
        db = h.container.providers.get("db")
        if db is not None:
            db.update_collection_owner(collection_id, org_id)
    audit.admin_action(
        actor_id=str(user.id), action="tenant_collection_grant", target=f"{org_id}:{collection_id}",
        detail={"role": role, "max_classification": max_classification},
    )
    return {"ok": True}


@router.delete("/organizations/{org_id}/collections/{collection_id}")
def remove_tenant_collection(
    org_id: int,
    collection_id: str,
    h: RequestHandler = Depends(get_handler),
    user: User = Depends(get_current_user),
):
    assert_collection_moderator(user, collection_id, h)
    h.container.services.get("users").remove_tenant_collection(org_id, collection_id)
    audit.admin_action(actor_id=str(user.id), action="tenant_collection_revoke", target=f"{org_id}:{collection_id}")
    return {"ok": True}


# Member management (moderator)
@router.patch("/organizations/{org_id}/members/{user_id}/classification")
def set_member_classification(
    org_id: int,
    user_id: str,
    req: dict,
    h: RequestHandler = Depends(get_handler),
    user: User = Depends(get_current_user),
):
    assert_tenant_moderator(user, org_id)
    level = int(req.get("level", 0))
    h.container.services.get("users").set_member_classification(uuid.UUID(user_id), org_id, level)
    audit.admin_action(
        actor_id=str(user.id), action="member_classification_set", target=f"{org_id}:{user_id}",
        detail={"level": level},
    )
    return {"ok": True}


@router.patch("/organizations/{org_id}/members/{user_id}/role")
def set_member_tenant_role(
    org_id: int,
    user_id: str,
    req: dict,
    h: RequestHandler = Depends(get_handler),
    user: User = Depends(get_current_user),
):
    assert_tenant_role_assigner(user, org_id)
    role = req.get("role")  # 'moderator', 'co-moderator', or None
    h.container.services.get("users").set_member_tenant_role(uuid.UUID(user_id), org_id, role)
    audit.admin_action(
        actor_id=str(user.id), action="member_tenant_role_set", target=f"{org_id}:{user_id}",
        detail={"role": role},
    )
    return {"ok": True}


# Collections (create)
@router.post("/collections/create")
def create_collection(
    req: dict,
    h: RequestHandler = Depends(get_handler),
    user: User = Depends(get_current_user),
):
    assert_admin_or_moderator(user)
    name = (req.get("name") or "").strip()
    if not name:
        raise HTTPException(400, "Collection name required.")
    db = h.container.providers.get("db")
    if db is None:
        raise HTTPException(503, "Database not available.")
    pipeline = h.container.services.get("ingestion")
    if pipeline is None:
        raise HTTPException(503, "Ingestion service not available.")
    dense_dim = pipeline.dense_encoder.vector_dim
    owner_org_id: int | None = req.get("owner_org_id") or None
    if owner_org_id is not None and not user.permissions.is_admin:
        if owner_org_id not in user.permissions.moderated_tenants:
            raise HTTPException(403, "You can only assign collections to organizations you moderate.")
    try:
        db.initialize(name, {"dense_dim": dense_dim, "create_indexes": True, "owner_org_id": owner_org_id})
    except Exception as e:
        raise HTTPException(500, f"Failed to create collection: {e}")
    if owner_org_id is not None:
        svc = h.container.services.get("users")
        if svc:
            svc.add_tenant_collection(owner_org_id, name, role="owner")
    audit.admin_action(
        actor_id=str(user.id), action="collection_create", target=name,
        detail={"owner_org_id": owner_org_id},
    )
    return {"ok": True, "name": name}


# Notifications
@router.post("/notifications/broadcast")
def broadcast_notification(
    req: dict,
    h: RequestHandler = Depends(get_handler),
    user: User = Depends(get_current_user),
):
    assert_admin(user)
    svc = h.container.services.get("notifications")
    if svc is None:
        raise HTTPException(503, "Notification service unavailable.")
    notif_id = svc.broadcast(req.get("title", ""), body=req.get("body") or None, link=req.get("link") or None)
    audit.admin_action(
        actor_id=str(user.id), action="notification_broadcast", target=str(notif_id),
        detail={"title": req.get("title")},
    )
    return {"ok": True, "notification_id": str(notif_id)}


@router.get("/notifications/history")
def get_notification_history(
    limit: int = 20,
    before_created_at: int | None = None,
    before_rowid: int | None = None,
    h: RequestHandler = Depends(get_handler),
    user: User = Depends(get_current_user),
):
    assert_admin(user)
    svc = h.container.services.get("notifications")
    if svc is None:
        raise HTTPException(503, "Notification service unavailable.")
    return svc.list_broadcasts(limit=limit, before_created_at=before_created_at, before_rowid=before_rowid)


# Tenant join requests (moderator)
@router.get("/organizations/{org_id}/join-requests")
def list_tenant_join_requests(
    org_id: int,
    status: str | None = None,
    h: RequestHandler = Depends(get_handler),
    user: User = Depends(get_current_user),
):
    assert_tenant_moderator(user, org_id)
    svc = h.container.services.get("notifications")
    if svc is None:
        raise HTTPException(503, "Notification service unavailable.")
    return {"requests": svc.list_org_join_requests(org_id, status=status)}


@router.post("/organizations/{org_id}/join-requests/{req_id}/approve")
def approve_tenant_join_request(
    org_id: int,
    req_id: str,
    req: dict,
    h: RequestHandler = Depends(get_handler),
    user: User = Depends(get_current_user),
):
    assert_tenant_moderator(user, org_id)
    tenant_role = req.get("tenant_role") or None
    if tenant_role:
        assert_tenant_role_assigner(user, org_id)
    svc = h.container.services.get("notifications")
    if svc is None:
        raise HTTPException(503, "Notification service unavailable.")
    svc.approve_join_request(
        uuid.UUID(req_id), user.id,
        tenant_role=tenant_role, classification_level=int(req.get("classification_level") or 0),
    )
    audit.admin_action(
        actor_id=str(user.id), action="join_request_approve", target=req_id,
        detail={"org_id": org_id, "tenant_role": tenant_role, "classification_level": req.get("classification_level")},
    )
    return {"ok": True}


@router.post("/organizations/{org_id}/join-requests/{req_id}/reject")
def reject_tenant_join_request(
    org_id: int,
    req_id: str,
    req: dict,
    h: RequestHandler = Depends(get_handler),
    user: User = Depends(get_current_user),
):
    assert_tenant_moderator(user, org_id)
    svc = h.container.services.get("notifications")
    if svc is None:
        raise HTTPException(503, "Notification service unavailable.")
    svc.reject_join_request(uuid.UUID(req_id), user.id, reason=req.get("reason") or None)
    audit.admin_action(actor_id=str(user.id), action="join_request_reject", target=req_id, detail={"org_id": org_id})
    return {"ok": True}


# Tenant invitations (moderator)
@router.post("/organizations/{org_id}/invitations")
def invite_tenant_user(
    org_id: int,
    req: dict,
    h: RequestHandler = Depends(get_handler),
    user: User = Depends(get_current_user),
):
    assert_tenant_moderator(user, org_id)
    svc = h.container.services.get("notifications")
    if svc is None:
        raise HTTPException(503, "Notification service unavailable.")
    identifier = req.get("identifier") or ""
    inv_id = svc.invite_user(org_id, identifier, user.id, message=req.get("message") or None)
    audit.admin_action(
        actor_id=str(user.id), action="tenant_invitation_send", target=str(inv_id),
        detail={"org_id": org_id, "identifier": identifier},
    )
    return {"ok": True, "invitation_id": str(inv_id)}


@router.get("/organizations/{org_id}/invitations")
def list_tenant_invitations(
    org_id: int,
    status: str | None = None,
    h: RequestHandler = Depends(get_handler),
    user: User = Depends(get_current_user),
):
    assert_tenant_moderator(user, org_id)
    svc = h.container.services.get("notifications")
    if svc is None:
        raise HTTPException(503, "Notification service unavailable.")
    return {"invitations": svc.list_org_invitations(org_id, status=status)}


@router.post("/organizations/{org_id}/invitations/{inv_id}/cancel")
def cancel_tenant_invitation(
    org_id: int,
    inv_id: str,
    h: RequestHandler = Depends(get_handler),
    user: User = Depends(get_current_user),
):
    assert_tenant_moderator(user, org_id)
    svc = h.container.services.get("notifications")
    if svc is None:
        raise HTTPException(503, "Notification service unavailable.")
    svc.cancel_invitation(uuid.UUID(inv_id), org_id)
    audit.admin_action(actor_id=str(user.id), action="tenant_invitation_cancel", target=inv_id, detail={"org_id": org_id})
    return {"ok": True}


# Tenant sharing requests (moderator)
@router.post("/organizations/{org_id}/share-requests")
def file_tenant_share_request(
    org_id: int,
    req: dict,
    h: RequestHandler = Depends(get_handler),
    user: User = Depends(get_current_user),
):
    assert_tenant_moderator(user, org_id)
    target_org_id = req.get("target_org_id")
    if not target_org_id:
        raise HTTPException(400, "target_org_id required")
    svc = h.container.services.get("notifications")
    if svc is None:
        raise HTTPException(503, "Notification service unavailable.")
    req_id = svc.file_share_request(org_id, int(target_org_id), user.id, message=req.get("message") or None)
    audit.admin_action(
        actor_id=str(user.id), action="share_request_file", target=str(req_id),
        detail={"requesting_org_id": org_id, "target_org_id": target_org_id},
    )
    return {"ok": True, "request_id": str(req_id)}


@router.get("/organizations/{org_id}/share-requests")
def list_tenant_share_requests(
    org_id: int,
    direction: str = "incoming",
    status: str | None = None,
    h: RequestHandler = Depends(get_handler),
    user: User = Depends(get_current_user),
):
    assert_tenant_moderator(user, org_id)
    svc = h.container.services.get("notifications")
    if svc is None:
        raise HTTPException(503, "Notification service unavailable.")
    return {"requests": svc.list_org_share_requests(org_id, direction, status=status)}


@router.post("/organizations/{org_id}/share-requests/{req_id}/approve")
def approve_tenant_share_request(
    org_id: int,
    req_id: str,
    req: dict,
    h: RequestHandler = Depends(get_handler),
    user: User = Depends(get_current_user),
):
    assert_tenant_moderator(user, org_id)
    svc = h.container.services.get("notifications")
    if svc is None:
        raise HTTPException(503, "Notification service unavailable.")
    share_req = svc.repo.get_share_request(uuid.UUID(req_id))
    if not share_req or share_req["target_org_id"] != org_id:
        raise HTTPException(404, "Share request not found for this tenant.")
    svc.approve_share_request(uuid.UUID(req_id), user.id, req.get("collections") or [])
    audit.admin_action(
        actor_id=str(user.id), action="share_request_approve", target=req_id,
        detail={"org_id": org_id, "collections": req.get("collections")},
    )
    return {"ok": True}


@router.post("/organizations/{org_id}/share-requests/{req_id}/reject")
def reject_tenant_share_request(
    org_id: int,
    req_id: str,
    req: dict,
    h: RequestHandler = Depends(get_handler),
    user: User = Depends(get_current_user),
):
    assert_tenant_moderator(user, org_id)
    svc = h.container.services.get("notifications")
    if svc is None:
        raise HTTPException(503, "Notification service unavailable.")
    share_req = svc.repo.get_share_request(uuid.UUID(req_id))
    if not share_req or share_req["target_org_id"] != org_id:
        raise HTTPException(404, "Share request not found for this tenant.")
    svc.reject_share_request(uuid.UUID(req_id), user.id, reason=req.get("reason") or None)
    audit.admin_action(actor_id=str(user.id), action="share_request_reject", target=req_id, detail={"org_id": org_id})
    return {"ok": True}


# Roles
@router.get("/roles")
def get_roles(
    h: RequestHandler = Depends(get_handler),
    user: User = Depends(get_current_user),
):
    assert_admin(user)
    return h.container.services.get("users").list_roles()
