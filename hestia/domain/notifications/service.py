from __future__ import annotations

import json
import logging
import uuid

from hestia.domain.auth.users import UserService, new_uuid, now_epoch
from hestia.domain.exceptions import NotFoundError, ValidationError
from hestia.infrastructure.db.notification_settings_repository import (
    DEFAULT_WELCOME_BODY, DEFAULT_WELCOME_TITLE, NotificationSettingsRepository,
)
from hestia.infrastructure.db.user_repository import UserRepository

_log = logging.getLogger("hestia.system")

_ELEVATED_TENANT_ROLES = ("moderator", "co-moderator")


def _load_data(raw: str | None) -> dict:
    if not raw:
        return {}
    try:
        data = json.loads(raw)
    except (json.JSONDecodeError, TypeError):
        return {}
    return data if isinstance(data, dict) else {}


class NotificationService:

    def __init__(self, repo: UserRepository, user_service: UserService,
                settings_repo: NotificationSettingsRepository):
        self.repo = repo
        self.users = user_service
        self.settings_repo = settings_repo

    # ---- notification helpers ----

    def _notify(self, *, user_id: uuid.UUID | None, type: str, title: str, body: str | None = None,
                link: str | None = None, ref_type: str | None = None, ref_id: str | None = None,
                data: dict | None = None) -> uuid.UUID:
        notif_id = new_uuid()
        self.repo.insert_notification(
            notif_id=notif_id, user_id=user_id, type=type, title=title, body=body, link=link,
            ref_type=ref_type, ref_id=ref_id, data_json=json.dumps(data) if data else None, ts=now_epoch(),
        )
        return notif_id

    def _notify_org_moderators(self, org_id: int, **kwargs) -> None:
        for row in self.repo.get_org_moderators(org_id):
            self._notify(user_id=uuid.UUID(bytes=row["user_id"]), **kwargs)

    @staticmethod
    def _row_to_notification(row) -> dict:
        return {
            "id": uuid.UUID(bytes=row["id"]),
            "user_id": uuid.UUID(bytes=row["user_id"]) if row["user_id"] else None,
            "type": row["type"],
            "title": row["title"],
            "body": row["body"],
            "link": row["link"],
            "ref_type": row["ref_type"],
            "ref_id": row["ref_id"],
            "data": _load_data(row["data_json"]),
            "created_at": row["created_at"],
            "is_read": bool(row["is_read"]),
        }

    # ---- inbox ----

    def list_notifications(self, user_id: uuid.UUID, limit: int = 20,
                           before_created_at: int | None = None, before_rowid: int | None = None) -> dict:
        rows = self.repo.get_notifications_for_user(
            user_id, limit=limit + 1, before_created_at=before_created_at, before_rowid=before_rowid,
        )
        has_more = len(rows) > limit
        rows = rows[:limit]
        notifications = [self._row_to_notification(r) for r in rows]
        last = rows[-1] if rows else None
        return {
            "notifications": notifications,
            "has_more": has_more,
            "next_cursor": {"created_at": last["created_at"], "rowid": last["rowid"]} if has_more and last else None,
        }

    def unread_count(self, user_id: uuid.UUID) -> int:
        return self.repo.get_unread_notification_count(user_id)

    def mark_read(self, notification_id: uuid.UUID, user_id: uuid.UUID) -> None:
        self.repo.mark_notification_read(notification_id=notification_id, user_id=user_id, ts=now_epoch())

    def mark_all_read(self, user_id: uuid.UUID) -> None:
        self.repo.mark_all_notifications_read(user_id=user_id, ts=now_epoch())

    def broadcast(self, title: str, body: str | None = None, link: str | None = None) -> uuid.UUID:
        if not title:
            raise ValidationError("Notification title required.")
        return self._notify(user_id=None, type="system", title=title, body=body, link=link)

    def send_welcome_notification(self, user_id: uuid.UUID) -> uuid.UUID:
        settings = self.settings_repo.get_settings()
        title = (settings["welcome_title"] if settings else "") or DEFAULT_WELCOME_TITLE
        body = (settings["welcome_body"] if settings else "") or DEFAULT_WELCOME_BODY
        return self._notify(user_id=user_id, type="system", title=title, body=body, link="/chat")

    def get_welcome_settings(self) -> dict:
        settings = self.settings_repo.get_settings()
        return {
            "welcome_title": (settings["welcome_title"] if settings else "") or DEFAULT_WELCOME_TITLE,
            "welcome_body": (settings["welcome_body"] if settings else "") or DEFAULT_WELCOME_BODY,
        }

    def update_welcome_settings(self, welcome_title: str, welcome_body: str) -> None:
        welcome_title = (welcome_title or "").strip()
        welcome_body = (welcome_body or "").strip()
        if not welcome_title:
            raise ValidationError("Welcome title required.")
        if not welcome_body:
            raise ValidationError("Welcome body required.")
        self.settings_repo.update_settings(welcome_title=welcome_title, welcome_body=welcome_body)

    def list_broadcasts(self, limit: int = 20, before_created_at: int | None = None,
                        before_rowid: int | None = None) -> dict:
        rows = self.repo.list_broadcast_notifications(
            limit=limit + 1, before_created_at=before_created_at, before_rowid=before_rowid,
        )
        has_more = len(rows) > limit
        rows = rows[:limit]
        broadcasts = [
            {"id": uuid.UUID(bytes=r["id"]), "title": r["title"], "body": r["body"],
             "link": r["link"], "created_at": r["created_at"]}
            for r in rows
        ]
        last = rows[-1] if rows else None
        return {
            "broadcasts": broadcasts,
            "has_more": has_more,
            "next_cursor": {"created_at": last["created_at"], "rowid": last["rowid"]} if has_more and last else None,
        }

    # ---- tenant browse ----

    def browse_organizations(self) -> list[dict]:
        return [
            {"id": o["id"], "name": o["name"], "abbreviation": o["abbreviation"]}
            for o in self.repo.list_organizations()
        ]

    # ---- tenant join requests ----

    @staticmethod
    def _join_request_row_to_dict(row) -> dict:
        return {
            "id": uuid.UUID(bytes=row["id"]),
            "user_id": uuid.UUID(bytes=row["user_id"]),
            "org_id": row["org_id"],
            "status": row["status"],
            "message": row["message"],
            "reviewed_by": uuid.UUID(bytes=row["reviewed_by"]) if row["reviewed_by"] else None,
            "review_reason": row["review_reason"],
            "granted_tenant_role": row["granted_tenant_role"],
            "granted_classification_level": row["granted_classification_level"],
            "created_at": row["created_at"],
            "resolved_at": row["resolved_at"],
        }

    def file_join_request(self, user_id: uuid.UUID, org_id: int, message: str | None = None) -> uuid.UUID:
        org = self.repo.get_organization_by_id(org_id)
        if not org:
            raise NotFoundError("Tenant not found.")
        memberships = self.repo.get_user_org_memberships(user_id)
        if any(m["org_id"] == org_id for m in memberships):
            raise ValidationError("You are already a member of this tenant.")
        if self.repo.get_pending_join_request(user_id, org_id):
            raise ValidationError("You already have a pending request for this tenant.")

        req_id = new_uuid()
        self.repo.insert_join_request(req_id=req_id, user_id=user_id, org_id=org_id, message=message, ts=now_epoch())

        requester = self.repo.get_user_by_id(user_id)
        requester_name = f"{requester['first_name']} {requester['last_name']}" if requester else "A user"
        self._notify_org_moderators(
            org_id, type="join_request_received", title=f"{requester_name} requested to join {org['name']}",
            body=message, link=f"/admin/tenants/{org_id}",
            ref_type="join_request", ref_id=str(req_id),
            data={"request_id": str(req_id), "org_id": org_id, "org_name": org["name"],
                  "requester_id": str(user_id), "requester_name": requester_name},
        )
        return req_id

    def list_org_join_requests(self, org_id: int, status: str | None = None) -> list[dict]:
        return [self._join_request_row_to_dict(r) | {
            "username": r["username"], "first_name": r["first_name"], "last_name": r["last_name"], "email": r["email"],
        } for r in self.repo.list_join_requests_for_org(org_id, status=status)]

    def list_user_join_requests(self, user_id: uuid.UUID) -> list[dict]:
        return [self._join_request_row_to_dict(r) | {
            "org_name": r["org_name"], "org_abbreviation": r["org_abbreviation"],
        } for r in self.repo.list_join_requests_for_user(user_id)]

    def approve_join_request(self, request_id: uuid.UUID, reviewer_id: uuid.UUID, *,
                             tenant_role: str | None = None, classification_level: int = 0) -> None:
        req = self.repo.get_join_request(request_id)
        if not req:
            raise NotFoundError("Join request not found.")
        if req["status"] != "pending":
            raise ValidationError("This request has already been resolved.")
        if tenant_role and tenant_role not in _ELEVATED_TENANT_ROLES:
            raise ValidationError("tenant_role must be 'moderator', 'co-moderator', or omitted for a plain member.")

        user_id = uuid.UUID(bytes=req["user_id"])
        org_id = req["org_id"]

        self.users.add_user_to_org(user_id=user_id, org_id=org_id)
        self.users.set_member_classification(user_id, org_id, classification_level or 0)
        if tenant_role:
            self.users.set_member_tenant_role(user_id, org_id, tenant_role)

        self.repo.resolve_join_request(
            req_id=request_id, status="approved", reviewed_by=reviewer_id, review_reason=None,
            granted_tenant_role=tenant_role, granted_classification_level=classification_level, ts=now_epoch(),
        )

        org = self.repo.get_organization_by_id(org_id)
        self._notify(
            user_id=user_id, type="join_request_approved",
            title=f"Your request to join {org['name']} was accepted",
            body=f"You joined as {tenant_role or 'a member'}.",
            link="/account/overview?section=tenants", ref_type="join_request", ref_id=str(request_id),
            data={"org_id": org_id, "org_name": org["name"], "tenant_role": tenant_role,
                  "classification_level": classification_level},
        )

    def reject_join_request(self, request_id: uuid.UUID, reviewer_id: uuid.UUID, reason: str | None = None) -> None:
        req = self.repo.get_join_request(request_id)
        if not req:
            raise NotFoundError("Join request not found.")
        if req["status"] != "pending":
            raise ValidationError("This request has already been resolved.")

        self.repo.resolve_join_request(
            req_id=request_id, status="rejected", reviewed_by=reviewer_id, review_reason=reason,
            granted_tenant_role=None, granted_classification_level=None, ts=now_epoch(),
        )

        org = self.repo.get_organization_by_id(req["org_id"])
        self._notify(
            user_id=uuid.UUID(bytes=req["user_id"]), type="join_request_rejected",
            title=f"Your request to join {org['name']} was rejected",
            body=reason, link="/account/overview?section=tenants", ref_type="join_request", ref_id=str(request_id),
            data={"org_id": req["org_id"], "org_name": org["name"], "reason": reason},
        )

    # ---- tenant share requests ----

    @staticmethod
    def _share_request_row_to_dict(row) -> dict:
        return {
            "id": uuid.UUID(bytes=row["id"]),
            "requesting_org_id": row["requesting_org_id"],
            "target_org_id": row["target_org_id"],
            "status": row["status"],
            "message": row["message"],
            "requested_by": uuid.UUID(bytes=row["requested_by"]),
            "reviewed_by": uuid.UUID(bytes=row["reviewed_by"]) if row["reviewed_by"] else None,
            "review_reason": row["review_reason"],
            "created_at": row["created_at"],
            "resolved_at": row["resolved_at"],
            "other_org_name": row["other_org_name"],
            "other_org_abbreviation": row["other_org_abbreviation"],
        }

    def file_share_request(self, requesting_org_id: int, target_org_id: int, requested_by: uuid.UUID,
                           message: str | None = None) -> uuid.UUID:
        if requesting_org_id == target_org_id:
            raise ValidationError("A tenant cannot request access from itself.")
        requesting_org = self.repo.get_organization_by_id(requesting_org_id)
        target_org = self.repo.get_organization_by_id(target_org_id)
        if not requesting_org or not target_org:
            raise NotFoundError("Tenant not found.")

        req_id = new_uuid()
        self.repo.insert_share_request(
            req_id=req_id, requesting_org_id=requesting_org_id, target_org_id=target_org_id,
            message=message, requested_by=requested_by, ts=now_epoch(),
        )

        self._notify_org_moderators(
            target_org_id, type="share_request_received",
            title=f"{requesting_org['name']} requested access to your knowledge bases",
            body=message, link=f"/admin/tenants/{target_org_id}",
            ref_type="share_request", ref_id=str(req_id),
            data={"request_id": str(req_id), "requesting_org_id": requesting_org_id,
                  "requesting_org_name": requesting_org["name"]},
        )
        return req_id

    def list_org_share_requests(self, org_id: int, direction: str, status: str | None = None) -> list[dict]:
        if direction not in ("incoming", "outgoing"):
            raise ValidationError("direction must be 'incoming' or 'outgoing'.")
        return [self._share_request_row_to_dict(r) for r in self.repo.list_share_requests_for_org(org_id, direction, status=status)]

    def approve_share_request(self, request_id: uuid.UUID, reviewer_id: uuid.UUID, collections: list[dict]) -> None:
        req = self.repo.get_share_request(request_id)
        if not req:
            raise NotFoundError("Share request not found.")
        if req["status"] != "pending":
            raise ValidationError("This request has already been resolved.")
        if not collections:
            raise ValidationError("Select at least one knowledge base to share.")

        target_org_id = req["target_org_id"]
        requesting_org_id = req["requesting_org_id"]

        shared_ids = []
        for c in collections:
            collection_id = c.get("collection_id")
            max_classification = c.get("max_classification")
            owner = self.repo.get_collection_owner(collection_id)
            if not owner or owner["id"] != target_org_id:
                raise ValidationError(f"Collection '{collection_id}' is not owned by this tenant.")
            self.users.add_tenant_collection(requesting_org_id, collection_id, role="access", max_classification=max_classification)
            self.repo.insert_share_grant(req_id=request_id, collection_id=collection_id, max_classification=max_classification)
            shared_ids.append(collection_id)

        self.repo.resolve_share_request(
            req_id=request_id, status="approved", reviewed_by=reviewer_id, review_reason=None, ts=now_epoch(),
        )

        target_org = self.repo.get_organization_by_id(target_org_id)
        self._notify_org_moderators(
            requesting_org_id, type="share_request_approved",
            title=f"{target_org['name']} shared {len(shared_ids)} knowledge base(s) with you",
            link=f"/admin/tenants/{requesting_org_id}", ref_type="share_request", ref_id=str(request_id),
            data={"target_org_id": target_org_id, "target_org_name": target_org["name"], "collections": shared_ids},
        )

    def reject_share_request(self, request_id: uuid.UUID, reviewer_id: uuid.UUID, reason: str | None = None) -> None:
        req = self.repo.get_share_request(request_id)
        if not req:
            raise NotFoundError("Share request not found.")
        if req["status"] != "pending":
            raise ValidationError("This request has already been resolved.")

        self.repo.resolve_share_request(
            req_id=request_id, status="rejected", reviewed_by=reviewer_id, review_reason=reason, ts=now_epoch(),
        )

        target_org = self.repo.get_organization_by_id(req["target_org_id"])
        self._notify_org_moderators(
            req["requesting_org_id"], type="share_request_rejected",
            title=f"{target_org['name']} declined your sharing request",
            body=reason, link=f"/admin/tenants/{req['requesting_org_id']}",
            ref_type="share_request", ref_id=str(request_id),
            data={"target_org_id": req["target_org_id"], "target_org_name": target_org["name"], "reason": reason},
        )

    # ---- tenant invitations ----

    @staticmethod
    def _invitation_row_to_dict(row) -> dict:
        return {
            "id": uuid.UUID(bytes=row["id"]),
            "org_id": row["org_id"],
            "user_id": uuid.UUID(bytes=row["user_id"]),
            "invited_by": uuid.UUID(bytes=row["invited_by"]),
            "status": row["status"],
            "message": row["message"],
            "created_at": row["created_at"],
            "resolved_at": row["resolved_at"],
        }

    def invite_user(self, org_id: int, identifier: str, invited_by: uuid.UUID,
                    message: str | None = None) -> uuid.UUID:
        org = self.repo.get_organization_by_id(org_id)
        if not org:
            raise NotFoundError("Tenant not found.")

        identifier = (identifier or "").strip()
        if not identifier:
            raise ValidationError("A username or email is required.")
        target = self.repo.get_user_for_login(identifier)
        if not target:
            raise NotFoundError("No user found with that username or email.")
        target_id = uuid.UUID(bytes=target["id"])

        memberships = self.repo.get_user_org_memberships(target_id)
        if any(m["org_id"] == org_id for m in memberships):
            raise ValidationError("This user is already a member of this tenant.")
        if self.repo.get_pending_invitation(target_id, org_id):
            raise ValidationError("This user already has a pending invitation to this tenant.")

        inv_id = new_uuid()
        self.repo.insert_invitation(
            inv_id=inv_id, org_id=org_id, user_id=target_id, invited_by=invited_by,
            message=message, ts=now_epoch(),
        )

        self._notify(
            user_id=target_id, type="tenant_invitation_received",
            title=f"You've been invited to join {org['name']}",
            body=message, link="/account/overview?section=tenants",
            ref_type="invitation", ref_id=str(inv_id),
            data={"org_id": org_id, "org_name": org["name"]},
        )
        return inv_id

    def list_org_invitations(self, org_id: int, status: str | None = None) -> list[dict]:
        return [self._invitation_row_to_dict(r) | {
            "username": r["username"], "email": r["email"],
            "first_name": r["first_name"], "last_name": r["last_name"],
        } for r in self.repo.list_invitations_for_org(org_id, status=status)]

    def list_user_invitations(self, user_id: uuid.UUID, status: str | None = None) -> list[dict]:
        return [self._invitation_row_to_dict(r) | {
            "org_name": r["org_name"], "org_abbreviation": r["org_abbreviation"],
        } for r in self.repo.list_invitations_for_user(user_id, status=status)]

    def cancel_invitation(self, invitation_id: uuid.UUID, org_id: int) -> None:
        inv = self.repo.get_invitation(invitation_id)
        if not inv or inv["org_id"] != org_id:
            raise NotFoundError("Invitation not found.")
        if inv["status"] != "pending":
            raise ValidationError("This invitation has already been resolved.")
        self.repo.resolve_invitation(inv_id=invitation_id, status="cancelled", ts=now_epoch())

    def accept_invitation(self, invitation_id: uuid.UUID, user_id: uuid.UUID) -> None:
        inv = self.repo.get_invitation(invitation_id)
        if not inv or uuid.UUID(bytes=inv["user_id"]) != user_id:
            raise NotFoundError("Invitation not found.")
        if inv["status"] != "pending":
            raise ValidationError("This invitation has already been resolved.")

        org_id = inv["org_id"]
        self.users.add_user_to_org(user_id=user_id, org_id=org_id)
        self.users.set_member_classification(user_id, org_id, 0)
        self.repo.resolve_invitation(inv_id=invitation_id, status="accepted", ts=now_epoch())

        org = self.repo.get_organization_by_id(org_id)
        invitee = self.repo.get_user_by_id(user_id)
        invitee_name = f"{invitee['first_name']} {invitee['last_name']}" if invitee else "A user"
        self._notify_org_moderators(
            org_id, type="tenant_invitation_accepted",
            title=f"{invitee_name} accepted your invitation to join {org['name']}",
            link=f"/admin/tenants/{org_id}", ref_type="invitation", ref_id=str(invitation_id),
            data={"org_id": org_id, "org_name": org["name"], "user_id": str(user_id)},
        )

    def decline_invitation(self, invitation_id: uuid.UUID, user_id: uuid.UUID) -> None:
        inv = self.repo.get_invitation(invitation_id)
        if not inv or uuid.UUID(bytes=inv["user_id"]) != user_id:
            raise NotFoundError("Invitation not found.")
        if inv["status"] != "pending":
            raise ValidationError("This invitation has already been resolved.")

        org_id = inv["org_id"]
        self.repo.resolve_invitation(inv_id=invitation_id, status="declined", ts=now_epoch())

        org = self.repo.get_organization_by_id(org_id)
        invitee = self.repo.get_user_by_id(user_id)
        invitee_name = f"{invitee['first_name']} {invitee['last_name']}" if invitee else "A user"
        self._notify_org_moderators(
            org_id, type="tenant_invitation_declined",
            title=f"{invitee_name} declined your invitation to join {org['name']}",
            link=f"/admin/tenants/{org_id}", ref_type="invitation", ref_id=str(invitation_id),
            data={"org_id": org_id, "org_name": org["name"], "user_id": str(user_id)},
        )
