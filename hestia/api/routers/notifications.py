import uuid

from fastapi import APIRouter, Depends, HTTPException

from hestia.api.dependencies import get_handler
from hestia.api.security import assert_org_member, get_current_user
from hestia.domain.auth.models import User
from hestia.handler import RequestHandler

router = APIRouter()


def _notification_svc(h: RequestHandler):
    svc = h.container.services.get("notifications")
    if svc is None:
        raise HTTPException(503, "Notification service unavailable.")
    return svc


# ---- inbox ----

@router.get("/notifications")
def list_notifications(
    limit: int = 20,
    before_created_at: int | None = None,
    before_rowid: int | None = None,
    h: RequestHandler = Depends(get_handler),
    user: User = Depends(get_current_user),
):
    svc = _notification_svc(h)
    return svc.list_notifications(
        user.id, limit=limit, before_created_at=before_created_at, before_rowid=before_rowid,
    )


@router.post("/notifications/{notification_id}/read")
def mark_notification_read(
    notification_id: str,
    h: RequestHandler = Depends(get_handler),
    user: User = Depends(get_current_user),
):
    svc = _notification_svc(h)
    svc.mark_read(uuid.UUID(notification_id), user.id)
    return {"ok": True}


@router.post("/notifications/read-all")
def mark_all_notifications_read(
    h: RequestHandler = Depends(get_handler),
    user: User = Depends(get_current_user),
):
    svc = _notification_svc(h)
    svc.mark_all_read(user.id)
    return {"ok": True}


# ---- tenant discovery ----

@router.get("/organizations/browse")
def browse_organizations(
    h: RequestHandler = Depends(get_handler),
    user: User = Depends(get_current_user),
):
    svc = _notification_svc(h)
    return {"organizations": svc.browse_organizations()}


@router.get("/organizations/{org_id}/summary")
def get_organization_summary(
    org_id: int,
    h: RequestHandler = Depends(get_handler),
    user: User = Depends(get_current_user),
):
    assert_org_member(user, org_id)
    svc = h.container.services.get("users")
    if svc is None:
        raise HTTPException(503, "User service unavailable.")
    return svc.get_tenant_summary(org_id, user.id)


# ---- self-service join requests ----

@router.post("/organizations/{org_id}/join-requests")
def file_join_request(
    org_id: int,
    req: dict,
    h: RequestHandler = Depends(get_handler),
    user: User = Depends(get_current_user),
):
    svc = _notification_svc(h)
    req_id = svc.file_join_request(user.id, org_id, message=req.get("message") or None)
    return {"ok": True, "request_id": str(req_id)}


@router.get("/account/join-requests")
def get_my_join_requests(
    h: RequestHandler = Depends(get_handler),
    user: User = Depends(get_current_user),
):
    svc = _notification_svc(h)
    return {"requests": svc.list_user_join_requests(user.id)}


# ---- self-service invitations ----

@router.get("/account/invitations")
def get_my_invitations(
    status: str | None = None,
    h: RequestHandler = Depends(get_handler),
    user: User = Depends(get_current_user),
):
    svc = _notification_svc(h)
    return {"invitations": svc.list_user_invitations(user.id, status=status)}


@router.post("/account/invitations/{inv_id}/accept")
def accept_invitation(
    inv_id: str,
    h: RequestHandler = Depends(get_handler),
    user: User = Depends(get_current_user),
):
    svc = _notification_svc(h)
    svc.accept_invitation(uuid.UUID(inv_id), user.id)
    return {"ok": True}


@router.post("/account/invitations/{inv_id}/decline")
def decline_invitation(
    inv_id: str,
    h: RequestHandler = Depends(get_handler),
    user: User = Depends(get_current_user),
):
    svc = _notification_svc(h)
    svc.decline_invitation(uuid.UUID(inv_id), user.id)
    return {"ok": True}
