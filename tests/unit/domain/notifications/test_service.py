from __future__ import annotations

import uuid
from unittest.mock import ANY, MagicMock

import pytest

from hestia.domain.exceptions import NotFoundError, ValidationError
from hestia.domain.notifications.service import NotificationService
from hestia.infrastructure.db.user_repository import ModeratorConflictError


def _uid():
    return uuid.uuid4()


@pytest.fixture
def repo():
    return MagicMock()


@pytest.fixture
def settings_repo():
    settings_repo = MagicMock()
    settings_repo.get_settings.return_value = None
    return settings_repo


@pytest.fixture
def service(repo, settings_repo):
    return NotificationService(repo, settings_repo)


# ---------------------------------------------------------------------------
# approve_join_request — now backed by one transactional repo call instead
# of a sequence of independently-committing ones.
# ---------------------------------------------------------------------------

class TestApproveJoinRequest:

    def _pending_request(self, repo, user_id, org_id=1):
        repo.get_join_request.return_value = {
            "id": _uid().bytes, "user_id": user_id.bytes, "org_id": org_id, "status": "pending",
        }
        repo.get_organization_by_id.return_value = {"id": org_id, "name": "Acme", "abbreviation": "ACM"}

    def test_calls_single_transactional_grant_method(self, service, repo):
        user_id = _uid()
        self._pending_request(repo, user_id)
        request_id = _uid()

        service.approve_join_request(request_id, _uid(), tenant_role="co-moderator", classification_level=2)

        repo.approve_join_request_and_grant.assert_called_once()
        kwargs = repo.approve_join_request_and_grant.call_args.kwargs
        assert kwargs["req_id"] == request_id
        assert kwargs["user_id"] == user_id
        assert kwargs["org_id"] == 1
        assert kwargs["classification_level"] == 2
        assert kwargs["tenant_role"] == "co-moderator"
        # None of the old per-step calls should exist on this service anymore.
        assert not hasattr(service, "users")

    def test_rejects_already_resolved_request_without_granting(self, service, repo):
        repo.get_join_request.return_value = {"status": "approved", "user_id": _uid().bytes, "org_id": 1}
        with pytest.raises(ValidationError):
            service.approve_join_request(_uid(), _uid())
        repo.approve_join_request_and_grant.assert_not_called()

    def test_missing_request_raises_not_found(self, service, repo):
        repo.get_join_request.return_value = None
        with pytest.raises(NotFoundError):
            service.approve_join_request(_uid(), _uid())
        repo.approve_join_request_and_grant.assert_not_called()

    def test_second_moderator_for_same_tenant_is_rejected_before_granting(self, service, repo):
        user_id = _uid()
        self._pending_request(repo, user_id)
        other_moderator_id = _uid()
        repo.get_org_tenant_moderator.return_value = {"user_id": other_moderator_id.bytes}

        with pytest.raises(ValidationError, match="already has a moderator"):
            service.approve_join_request(_uid(), _uid(), tenant_role="moderator")

        repo.approve_join_request_and_grant.assert_not_called()

    def test_concurrent_double_approval_raises_validation_error(self, service, repo):
        # The pre-flight read above can't catch a request resolved by a
        # concurrent call between the read and the write -- the repo's
        # transactional grant is the authoritative source, signalled by a
        # False return.
        user_id = _uid()
        self._pending_request(repo, user_id)
        repo.approve_join_request_and_grant.return_value = False

        with pytest.raises(ValidationError, match="already been resolved"):
            service.approve_join_request(_uid(), _uid())

    def test_concurrent_moderator_conflict_from_repo_raises_validation_error(self, service, repo):
        # Same race, but for the one-moderator-per-tenant invariant: the
        # pre-flight get_org_tenant_moderator() read can miss a concurrent
        # grant that lands between the read and this call's own write. The
        # repo's in-transaction check is what actually prevents the double
        # grant, surfaced here as ModeratorConflictError.
        user_id = _uid()
        self._pending_request(repo, user_id)
        repo.get_org_tenant_moderator.return_value = None
        repo.approve_join_request_and_grant.side_effect = ModeratorConflictError("Tenant already has a moderator.")

        with pytest.raises(ValidationError, match="already has a moderator"):
            service.approve_join_request(_uid(), _uid(), tenant_role="moderator")


# ---------------------------------------------------------------------------
# approve_share_request
# ---------------------------------------------------------------------------

class TestApproveShareRequest:

    def _pending_request(self, repo, target_org_id=2, requesting_org_id=1):
        repo.get_share_request.return_value = {
            "id": _uid().bytes, "status": "pending",
            "target_org_id": target_org_id, "requesting_org_id": requesting_org_id,
        }
        repo.get_organization_by_id.return_value = {"id": target_org_id, "name": "Target", "abbreviation": "TGT"}

    def test_calls_single_transactional_grant_method_with_validated_collections(self, service, repo):
        self._pending_request(repo)
        repo.get_collection_owner.return_value = {"id": 2, "name": "Target", "abbreviation": "TGT"}
        request_id = _uid()

        service.approve_share_request(
            request_id, _uid(), [{"collection_id": "col-a", "max_classification": 1}],
        )

        repo.approve_share_request_and_grant.assert_called_once()
        kwargs = repo.approve_share_request_and_grant.call_args.kwargs
        assert kwargs["req_id"] == request_id
        assert kwargs["requesting_org_id"] == 1
        assert kwargs["grants"] == [("col-a", 1)]

    def test_concurrent_double_approval_raises_validation_error(self, service, repo):
        self._pending_request(repo)
        repo.get_collection_owner.return_value = {"id": 2, "name": "Target", "abbreviation": "TGT"}
        repo.approve_share_request_and_grant.return_value = False

        with pytest.raises(ValidationError, match="already been resolved"):
            service.approve_share_request(_uid(), _uid(), [{"collection_id": "col-a"}])

    def test_collection_not_owned_by_target_tenant_is_rejected_before_granting(self, service, repo):
        self._pending_request(repo)
        repo.get_collection_owner.return_value = {"id": 999, "name": "Someone Else", "abbreviation": "SE"}

        with pytest.raises(ValidationError, match="not owned"):
            service.approve_share_request(_uid(), _uid(), [{"collection_id": "col-a"}])

        repo.approve_share_request_and_grant.assert_not_called()

    def test_no_collections_selected_is_rejected(self, service, repo):
        self._pending_request(repo)
        with pytest.raises(ValidationError):
            service.approve_share_request(_uid(), _uid(), [])
        repo.approve_share_request_and_grant.assert_not_called()


# ---------------------------------------------------------------------------
# accept_invitation
# ---------------------------------------------------------------------------

class TestAcceptInvitation:

    def test_calls_single_transactional_grant_method(self, service, repo):
        user_id = _uid()
        invitation_id = _uid()
        repo.get_invitation.return_value = {
            "id": invitation_id.bytes, "user_id": user_id.bytes, "org_id": 5, "status": "pending",
        }
        repo.get_organization_by_id.return_value = {"id": 5, "name": "Org", "abbreviation": "O"}
        repo.get_user_by_id.return_value = {"first_name": "A", "last_name": "B"}

        service.accept_invitation(invitation_id, user_id)

        repo.accept_invitation_and_grant.assert_called_once()
        kwargs = repo.accept_invitation_and_grant.call_args.kwargs
        assert kwargs["inv_id"] == invitation_id
        assert kwargs["user_id"] == user_id
        assert kwargs["org_id"] == 5

    def test_invitation_for_a_different_user_is_not_found(self, service, repo):
        repo.get_invitation.return_value = {
            "id": _uid().bytes, "user_id": _uid().bytes, "org_id": 5, "status": "pending",
        }
        with pytest.raises(NotFoundError):
            service.accept_invitation(_uid(), _uid())
        repo.accept_invitation_and_grant.assert_not_called()

    def test_already_resolved_invitation_raises_validation_error(self, service, repo):
        user_id = _uid()
        repo.get_invitation.return_value = {
            "id": _uid().bytes, "user_id": user_id.bytes, "org_id": 5, "status": "accepted",
        }
        with pytest.raises(ValidationError):
            service.accept_invitation(_uid(), user_id)
        repo.accept_invitation_and_grant.assert_not_called()

    def test_concurrent_double_resolution_raises_validation_error(self, service, repo):
        user_id = _uid()
        repo.get_invitation.return_value = {
            "id": _uid().bytes, "user_id": user_id.bytes, "org_id": 5, "status": "pending",
        }
        repo.accept_invitation_and_grant.return_value = False

        with pytest.raises(ValidationError, match="already been resolved"):
            service.accept_invitation(_uid(), user_id)


# ---------------------------------------------------------------------------
# reject_join_request
# ---------------------------------------------------------------------------

class TestRejectJoinRequest:

    def test_missing_request_raises_not_found(self, service, repo):
        repo.get_join_request.return_value = None
        with pytest.raises(NotFoundError):
            service.reject_join_request(_uid(), _uid())
        repo.resolve_join_request.assert_not_called()

    def test_already_resolved_request_raises_validation_error(self, service, repo):
        repo.get_join_request.return_value = {
            "status": "approved", "user_id": _uid().bytes, "org_id": 1,
        }
        with pytest.raises(ValidationError):
            service.reject_join_request(_uid(), _uid())
        repo.resolve_join_request.assert_not_called()

    def test_resolves_and_notifies_requester(self, service, repo):
        user_id = _uid()
        request_id = _uid()
        reviewer_id = _uid()
        repo.get_join_request.return_value = {
            "user_id": user_id.bytes, "org_id": 1, "status": "pending",
        }
        repo.get_organization_by_id.return_value = {"id": 1, "name": "Acme", "abbreviation": "ACM"}

        service.reject_join_request(request_id, reviewer_id, reason="not a fit")

        repo.resolve_join_request.assert_called_once_with(
            req_id=request_id, status="rejected", reviewed_by=reviewer_id, review_reason="not a fit",
            granted_tenant_role=None, granted_classification_level=None, ts=ANY,
        )
        repo.insert_notification.assert_called_once()
        kwargs = repo.insert_notification.call_args.kwargs
        assert kwargs["user_id"] == user_id
        assert kwargs["type"] == "join_request_rejected"
        assert "Acme" in kwargs["title"]

    def test_concurrent_double_resolution_raises_validation_error(self, service, repo):
        repo.get_join_request.return_value = {
            "user_id": _uid().bytes, "org_id": 1, "status": "pending",
        }
        repo.resolve_join_request.return_value = False

        with pytest.raises(ValidationError, match="already been resolved"):
            service.reject_join_request(_uid(), _uid())


# ---------------------------------------------------------------------------
# reject_share_request
# ---------------------------------------------------------------------------

class TestRejectShareRequest:

    def test_missing_request_raises_not_found(self, service, repo):
        repo.get_share_request.return_value = None
        with pytest.raises(NotFoundError):
            service.reject_share_request(_uid(), _uid())
        repo.resolve_share_request.assert_not_called()

    def test_already_resolved_request_raises_validation_error(self, service, repo):
        repo.get_share_request.return_value = {
            "status": "approved", "target_org_id": 1, "requesting_org_id": 2,
        }
        with pytest.raises(ValidationError):
            service.reject_share_request(_uid(), _uid())
        repo.resolve_share_request.assert_not_called()

    def test_resolves_and_notifies_requesting_org_moderators(self, service, repo):
        request_id = _uid()
        reviewer_id = _uid()
        repo.get_share_request.return_value = {
            "target_org_id": 1, "requesting_org_id": 2, "status": "pending",
        }
        repo.get_organization_by_id.return_value = {"id": 1, "name": "Target", "abbreviation": "TGT"}
        mod_id = _uid()
        repo.get_org_moderators.return_value = [{"user_id": mod_id.bytes}]

        service.reject_share_request(request_id, reviewer_id, reason="not enough capacity")

        repo.resolve_share_request.assert_called_once_with(
            req_id=request_id, status="rejected", reviewed_by=reviewer_id,
            review_reason="not enough capacity", ts=ANY,
        )
        repo.get_org_moderators.assert_called_once_with(2)
        repo.insert_notification.assert_called_once()
        kwargs = repo.insert_notification.call_args.kwargs
        assert kwargs["user_id"] == mod_id
        assert kwargs["type"] == "share_request_rejected"

    def test_concurrent_double_resolution_raises_validation_error(self, service, repo):
        repo.get_share_request.return_value = {
            "target_org_id": 1, "requesting_org_id": 2, "status": "pending",
        }
        repo.resolve_share_request.return_value = False

        with pytest.raises(ValidationError, match="already been resolved"):
            service.reject_share_request(_uid(), _uid())


# ---------------------------------------------------------------------------
# invite_user
# ---------------------------------------------------------------------------

class TestInviteUser:

    def test_missing_org_raises_not_found(self, service, repo):
        repo.get_organization_by_id.return_value = None
        with pytest.raises(NotFoundError):
            service.invite_user(1, "bob", _uid())
        repo.insert_invitation.assert_not_called()

    def test_blank_identifier_raises_validation_error(self, service, repo):
        repo.get_organization_by_id.return_value = {"id": 1, "name": "Acme"}
        with pytest.raises(ValidationError):
            service.invite_user(1, "   ", _uid())
        repo.insert_invitation.assert_not_called()

    def test_unknown_user_raises_not_found(self, service, repo):
        repo.get_organization_by_id.return_value = {"id": 1, "name": "Acme"}
        repo.get_user_for_login.return_value = None
        with pytest.raises(NotFoundError):
            service.invite_user(1, "bob", _uid())
        repo.insert_invitation.assert_not_called()

    def test_already_member_raises_validation_error(self, service, repo):
        target_id = _uid()
        repo.get_organization_by_id.return_value = {"id": 1, "name": "Acme"}
        repo.get_user_for_login.return_value = {"id": target_id.bytes}
        repo.get_user_org_memberships.return_value = [{"org_id": 1}]
        with pytest.raises(ValidationError, match="already a member"):
            service.invite_user(1, "bob", _uid())
        repo.insert_invitation.assert_not_called()

    def test_already_pending_invitation_raises_validation_error(self, service, repo):
        target_id = _uid()
        repo.get_organization_by_id.return_value = {"id": 1, "name": "Acme"}
        repo.get_user_for_login.return_value = {"id": target_id.bytes}
        repo.get_user_org_memberships.return_value = []
        repo.get_pending_invitation.return_value = {"id": _uid().bytes}
        with pytest.raises(ValidationError, match="pending invitation"):
            service.invite_user(1, "bob", _uid())
        repo.insert_invitation.assert_not_called()

    def test_success_inserts_invitation_and_notifies_target(self, service, repo):
        target_id = _uid()
        inviter_id = _uid()
        repo.get_organization_by_id.return_value = {"id": 1, "name": "Acme"}
        repo.get_user_for_login.return_value = {"id": target_id.bytes}
        repo.get_user_org_memberships.return_value = []
        repo.get_pending_invitation.return_value = None

        inv_id = service.invite_user(1, " bob ", inviter_id, message="welcome!")

        repo.insert_invitation.assert_called_once()
        kwargs = repo.insert_invitation.call_args.kwargs
        assert kwargs["inv_id"] == inv_id
        assert kwargs["org_id"] == 1
        assert kwargs["user_id"] == target_id
        assert kwargs["invited_by"] == inviter_id
        assert kwargs["message"] == "welcome!"
        repo.insert_notification.assert_called_once()
        notif_kwargs = repo.insert_notification.call_args.kwargs
        assert notif_kwargs["user_id"] == target_id
        assert notif_kwargs["type"] == "tenant_invitation_received"

    def test_concurrent_double_submit_raises_validation_error(self, service, repo):
        import sqlite3
        repo.get_organization_by_id.return_value = {"id": 1, "name": "Acme"}
        repo.get_user_for_login.return_value = {"id": _uid().bytes}
        repo.get_user_org_memberships.return_value = []
        repo.get_pending_invitation.return_value = None
        repo.insert_invitation.side_effect = sqlite3.IntegrityError("UNIQUE constraint failed")

        with pytest.raises(ValidationError, match="pending invitation"):
            service.invite_user(1, "bob", _uid())
        repo.insert_notification.assert_not_called()


# ---------------------------------------------------------------------------
# cancel_invitation
# ---------------------------------------------------------------------------

class TestCancelInvitation:

    def test_missing_invitation_raises_not_found(self, service, repo):
        repo.get_invitation.return_value = None
        with pytest.raises(NotFoundError):
            service.cancel_invitation(_uid(), 1)
        repo.resolve_invitation.assert_not_called()

    def test_invitation_for_different_org_raises_not_found(self, service, repo):
        repo.get_invitation.return_value = {"org_id": 2, "status": "pending"}
        with pytest.raises(NotFoundError):
            service.cancel_invitation(_uid(), 1)
        repo.resolve_invitation.assert_not_called()

    def test_already_resolved_raises_validation_error(self, service, repo):
        repo.get_invitation.return_value = {"org_id": 1, "status": "accepted"}
        with pytest.raises(ValidationError):
            service.cancel_invitation(_uid(), 1)
        repo.resolve_invitation.assert_not_called()

    def test_success_resolves_as_cancelled(self, service, repo):
        invitation_id = _uid()
        repo.get_invitation.return_value = {"org_id": 1, "status": "pending"}

        service.cancel_invitation(invitation_id, 1)

        repo.resolve_invitation.assert_called_once_with(
            inv_id=invitation_id, status="cancelled", ts=ANY,
        )

    def test_concurrent_accept_raises_validation_error(self, service, repo):
        # The invited user's accept_invitation_and_grant lands first (in the
        # same race window this admin's cancel is trying to close) --
        # resolve_invitation's WHERE clause then matches nothing.
        repo.get_invitation.return_value = {"org_id": 1, "status": "pending"}
        repo.resolve_invitation.return_value = False

        with pytest.raises(ValidationError, match="already been resolved"):
            service.cancel_invitation(_uid(), 1)


# ---------------------------------------------------------------------------
# decline_invitation
# ---------------------------------------------------------------------------

class TestDeclineInvitation:

    def test_missing_invitation_raises_not_found(self, service, repo):
        repo.get_invitation.return_value = None
        with pytest.raises(NotFoundError):
            service.decline_invitation(_uid(), _uid())
        repo.resolve_invitation.assert_not_called()

    def test_invitation_for_different_user_raises_not_found(self, service, repo):
        repo.get_invitation.return_value = {"user_id": _uid().bytes, "status": "pending"}
        with pytest.raises(NotFoundError):
            service.decline_invitation(_uid(), _uid())
        repo.resolve_invitation.assert_not_called()

    def test_already_resolved_raises_validation_error(self, service, repo):
        user_id = _uid()
        repo.get_invitation.return_value = {"user_id": user_id.bytes, "status": "declined"}
        with pytest.raises(ValidationError):
            service.decline_invitation(_uid(), user_id)
        repo.resolve_invitation.assert_not_called()

    def test_success_resolves_and_notifies_org_moderators(self, service, repo):
        user_id = _uid()
        invitation_id = _uid()
        repo.get_invitation.return_value = {"user_id": user_id.bytes, "org_id": 1, "status": "pending"}
        repo.get_organization_by_id.return_value = {"id": 1, "name": "Acme"}
        repo.get_user_by_id.return_value = {"first_name": "Jane", "last_name": "Doe"}
        mod_id = _uid()
        repo.get_org_moderators.return_value = [{"user_id": mod_id.bytes}]

        service.decline_invitation(invitation_id, user_id)

        repo.resolve_invitation.assert_called_once_with(
            inv_id=invitation_id, status="declined", ts=ANY,
        )
        repo.insert_notification.assert_called_once()
        kwargs = repo.insert_notification.call_args.kwargs
        assert kwargs["user_id"] == mod_id
        assert kwargs["type"] == "tenant_invitation_declined"
        assert "Jane Doe" in kwargs["title"]

    def test_concurrent_double_resolution_raises_validation_error(self, service, repo):
        user_id = _uid()
        repo.get_invitation.return_value = {"user_id": user_id.bytes, "org_id": 1, "status": "pending"}
        repo.resolve_invitation.return_value = False

        with pytest.raises(ValidationError, match="already been resolved"):
            service.decline_invitation(_uid(), user_id)


# ---------------------------------------------------------------------------
# file_join_request
# ---------------------------------------------------------------------------

class TestFileJoinRequest:

    def test_missing_org_raises_not_found(self, service, repo):
        repo.get_organization_by_id.return_value = None
        with pytest.raises(NotFoundError):
            service.file_join_request(_uid(), 1)
        repo.insert_join_request.assert_not_called()

    def test_already_member_raises_validation_error(self, service, repo):
        repo.get_organization_by_id.return_value = {"id": 1, "name": "Acme"}
        repo.get_user_org_memberships.return_value = [{"org_id": 1}]
        with pytest.raises(ValidationError, match="already a member"):
            service.file_join_request(_uid(), 1)
        repo.insert_join_request.assert_not_called()

    def test_already_pending_raises_validation_error(self, service, repo):
        repo.get_organization_by_id.return_value = {"id": 1, "name": "Acme"}
        repo.get_user_org_memberships.return_value = []
        repo.get_pending_join_request.return_value = {"id": _uid().bytes}
        with pytest.raises(ValidationError, match="pending request"):
            service.file_join_request(_uid(), 1)
        repo.insert_join_request.assert_not_called()

    def test_success_inserts_request_and_notifies_moderators(self, service, repo):
        user_id = _uid()
        repo.get_organization_by_id.return_value = {"id": 1, "name": "Acme"}
        repo.get_user_org_memberships.return_value = []
        repo.get_pending_join_request.return_value = None
        repo.get_user_by_id.return_value = {"first_name": "Jane", "last_name": "Doe"}
        mod_id = _uid()
        repo.get_org_moderators.return_value = [{"user_id": mod_id.bytes}]

        req_id = service.file_join_request(user_id, 1, message="please let me in")

        repo.insert_join_request.assert_called_once()
        kwargs = repo.insert_join_request.call_args.kwargs
        assert kwargs["req_id"] == req_id
        assert kwargs["user_id"] == user_id
        assert kwargs["org_id"] == 1
        assert kwargs["message"] == "please let me in"

    def test_concurrent_double_submit_raises_validation_error(self, service, repo):
        # get_pending_join_request's read and insert_join_request's write
        # aren't in the same transaction, so a double-click can pass the
        # pre-check twice -- the partial unique index backing insert_join_
        # request is what actually stops the second insert, surfaced here
        # as sqlite3.IntegrityError.
        import sqlite3
        repo.get_organization_by_id.return_value = {"id": 1, "name": "Acme"}
        repo.get_user_org_memberships.return_value = []
        repo.get_pending_join_request.return_value = None
        repo.insert_join_request.side_effect = sqlite3.IntegrityError("UNIQUE constraint failed")

        with pytest.raises(ValidationError, match="pending request"):
            service.file_join_request(_uid(), 1)
        repo.insert_notification.assert_not_called()


# ---------------------------------------------------------------------------
# file_share_request
# ---------------------------------------------------------------------------

class TestFileShareRequest:

    def test_requesting_from_self_raises_validation_error(self, service, repo):
        with pytest.raises(ValidationError, match="cannot request access from itself"):
            service.file_share_request(1, 1, _uid())
        repo.insert_share_request.assert_not_called()

    def test_missing_org_raises_not_found(self, service, repo):
        repo.get_organization_by_id.return_value = None
        with pytest.raises(NotFoundError):
            service.file_share_request(1, 2, _uid())
        repo.insert_share_request.assert_not_called()

    def test_success_inserts_request_and_notifies_target_moderators(self, service, repo):
        requested_by = _uid()
        repo.get_organization_by_id.side_effect = [
            {"id": 1, "name": "Requester"}, {"id": 2, "name": "Target"},
        ]
        mod_id = _uid()
        repo.get_org_moderators.return_value = [{"user_id": mod_id.bytes}]

        req_id = service.file_share_request(1, 2, requested_by, message="please share")

        repo.insert_share_request.assert_called_once()
        kwargs = repo.insert_share_request.call_args.kwargs
        assert kwargs["req_id"] == req_id
        assert kwargs["requesting_org_id"] == 1
        assert kwargs["target_org_id"] == 2
        assert kwargs["requested_by"] == requested_by
        repo.get_org_moderators.assert_called_once_with(2)
        repo.insert_notification.assert_called_once()
        notif_kwargs = repo.insert_notification.call_args.kwargs
        assert notif_kwargs["user_id"] == mod_id
        assert notif_kwargs["type"] == "share_request_received"

    def test_concurrent_double_submit_raises_validation_error(self, service, repo):
        import sqlite3
        repo.get_organization_by_id.side_effect = [
            {"id": 1, "name": "Requester"}, {"id": 2, "name": "Target"},
        ]
        repo.insert_share_request.side_effect = sqlite3.IntegrityError("UNIQUE constraint failed")

        with pytest.raises(ValidationError, match="already exists"):
            service.file_share_request(1, 2, _uid())
        repo.insert_notification.assert_not_called()


# ---------------------------------------------------------------------------
# broadcast / list_broadcasts
# ---------------------------------------------------------------------------

class TestBroadcast:

    def test_blank_title_raises_validation_error(self, service, repo):
        with pytest.raises(ValidationError):
            service.broadcast("")
        repo.insert_notification.assert_not_called()

    def test_success_notifies_with_no_user(self, service, repo):
        notif_id = service.broadcast("Big News", body="details", link="/somewhere")

        repo.insert_notification.assert_called_once()
        kwargs = repo.insert_notification.call_args.kwargs
        assert kwargs["notif_id"] == notif_id
        assert kwargs["user_id"] is None
        assert kwargs["type"] == "system"
        assert kwargs["title"] == "Big News"
        assert kwargs["body"] == "details"
        assert kwargs["link"] == "/somewhere"


class TestListBroadcasts:

    def _row(self, **overrides):
        row = {
            "id": _uid().bytes, "title": "T", "body": "B", "link": "/l",
            "created_at": 100, "rowid": 1,
        }
        row.update(overrides)
        return row

    def test_no_more_pages(self, service, repo):
        repo.list_broadcast_notifications.return_value = [self._row()]

        result = service.list_broadcasts(limit=20)

        assert len(result["broadcasts"]) == 1
        assert result["has_more"] is False
        assert result["next_cursor"] is None

    def test_has_more_pages_returns_cursor(self, service, repo):
        rows = [self._row(created_at=i, rowid=i) for i in range(3)]
        repo.list_broadcast_notifications.return_value = rows

        result = service.list_broadcasts(limit=2)

        assert len(result["broadcasts"]) == 2
        assert result["has_more"] is True
        assert result["next_cursor"] == {"created_at": 1, "rowid": 1}


# ---------------------------------------------------------------------------
# get_welcome_settings / update_welcome_settings
# ---------------------------------------------------------------------------

class TestGetWelcomeSettings:

    def test_returns_defaults_when_no_settings_row(self, service, settings_repo):
        settings_repo.get_settings.return_value = None

        result = service.get_welcome_settings()

        from hestia.infrastructure.db.notification_settings_repository import (
            DEFAULT_WELCOME_BODY, DEFAULT_WELCOME_TITLE,
        )
        assert result == {"welcome_title": DEFAULT_WELCOME_TITLE, "welcome_body": DEFAULT_WELCOME_BODY}

    def test_returns_stored_settings(self, service, settings_repo):
        settings_repo.get_settings.return_value = {"welcome_title": "Hi", "welcome_body": "Body"}

        result = service.get_welcome_settings()

        assert result == {"welcome_title": "Hi", "welcome_body": "Body"}


class TestUpdateWelcomeSettings:

    def test_blank_title_raises_validation_error(self, service, settings_repo):
        with pytest.raises(ValidationError, match="title"):
            service.update_welcome_settings("  ", "Body")
        settings_repo.update_settings.assert_not_called()

    def test_blank_body_raises_validation_error(self, service, settings_repo):
        with pytest.raises(ValidationError, match="body"):
            service.update_welcome_settings("Title", "   ")
        settings_repo.update_settings.assert_not_called()

    def test_success_strips_and_updates(self, service, settings_repo):
        service.update_welcome_settings("  Title  ", "  Body  ")
        settings_repo.update_settings.assert_called_once_with(welcome_title="Title", welcome_body="Body")


# ---------------------------------------------------------------------------
# browse_organizations
# ---------------------------------------------------------------------------

class TestBrowseOrganizations:

    def test_maps_organization_rows(self, service, repo):
        repo.list_organizations.return_value = [
            {"id": 1, "name": "Acme", "abbreviation": "ACM"},
            {"id": 2, "name": "Beta", "abbreviation": "BTA"},
        ]

        result = service.browse_organizations()

        assert result == [
            {"id": 1, "name": "Acme", "abbreviation": "ACM"},
            {"id": 2, "name": "Beta", "abbreviation": "BTA"},
        ]


# ---------------------------------------------------------------------------
# list_notifications / unread_count / mark_read / mark_all_read
# ---------------------------------------------------------------------------

class TestListNotifications:

    def _row(self, **overrides):
        row = {
            "id": _uid().bytes, "user_id": _uid().bytes, "type": "system", "title": "T", "body": "B",
            "link": "/l", "ref_type": None, "ref_id": None, "data_json": None,
            "created_at": 100, "is_read": 0, "rowid": 1,
        }
        row.update(overrides)
        return row

    def test_no_more_pages(self, service, repo):
        user_id = _uid()
        repo.get_notifications_for_user.return_value = [self._row()]

        result = service.list_notifications(user_id, limit=20)

        assert len(result["notifications"]) == 1
        assert result["has_more"] is False
        assert result["next_cursor"] is None
        assert result["notifications"][0]["is_read"] is False

    def test_has_more_pages_returns_cursor(self, service, repo):
        user_id = _uid()
        rows = [self._row(created_at=i, rowid=i) for i in range(3)]
        repo.get_notifications_for_user.return_value = rows

        result = service.list_notifications(user_id, limit=2)

        assert len(result["notifications"]) == 2
        assert result["has_more"] is True
        assert result["next_cursor"] == {"created_at": 1, "rowid": 1}

    def test_parses_json_data_field(self, service, repo):
        user_id = _uid()
        repo.get_notifications_for_user.return_value = [self._row(data_json='{"foo": "bar"}')]

        result = service.list_notifications(user_id)

        assert result["notifications"][0]["data"] == {"foo": "bar"}

    def test_malformed_json_data_field_yields_empty_dict(self, service, repo):
        user_id = _uid()
        repo.get_notifications_for_user.return_value = [self._row(data_json="{not valid json")]

        result = service.list_notifications(user_id)

        assert result["notifications"][0]["data"] == {}


class TestUnreadCount:

    def test_delegates_to_repo(self, service, repo):
        user_id = _uid()
        repo.get_unread_notification_count.return_value = 5

        assert service.unread_count(user_id) == 5
        repo.get_unread_notification_count.assert_called_once_with(user_id)


class TestMarkRead:

    def test_delegates_to_repo(self, service, repo):
        user_id = _uid()
        notification_id = _uid()

        service.mark_read(notification_id, user_id)

        repo.mark_notification_read.assert_called_once_with(
            notification_id=notification_id, user_id=user_id, ts=ANY,
        )


class TestMarkAllRead:

    def test_delegates_to_repo(self, service, repo):
        user_id = _uid()

        service.mark_all_read(user_id)

        repo.mark_all_notifications_read.assert_called_once_with(
            user_id=user_id, ts=ANY,
        )


# ---------------------------------------------------------------------------
# listing methods
# ---------------------------------------------------------------------------

class TestListOrgJoinRequests:

    def test_merges_requester_fields(self, service, repo):
        row = {
            "id": _uid().bytes, "user_id": _uid().bytes, "org_id": 1, "status": "pending",
            "message": None, "reviewed_by": None, "review_reason": None,
            "granted_tenant_role": None, "granted_classification_level": None,
            "created_at": 1, "resolved_at": None,
            "username": "bob", "first_name": "Bob", "last_name": "Jones", "email": "bob@x.com",
        }
        repo.list_join_requests_for_org.return_value = [row]

        result = service.list_org_join_requests(1, status="pending")

        assert result[0]["username"] == "bob"
        assert result[0]["email"] == "bob@x.com"
        repo.list_join_requests_for_org.assert_called_once_with(1, status="pending")


class TestListUserJoinRequests:

    def test_merges_org_fields(self, service, repo):
        row = {
            "id": _uid().bytes, "user_id": _uid().bytes, "org_id": 1, "status": "pending",
            "message": None, "reviewed_by": None, "review_reason": None,
            "granted_tenant_role": None, "granted_classification_level": None,
            "created_at": 1, "resolved_at": None,
            "org_name": "Acme", "org_abbreviation": "ACM",
        }
        repo.list_join_requests_for_user.return_value = [row]

        result = service.list_user_join_requests(_uid())

        assert result[0]["org_name"] == "Acme"


class TestListOrgShareRequests:

    def test_invalid_direction_raises_validation_error(self, service, repo):
        with pytest.raises(ValidationError):
            service.list_org_share_requests(1, "sideways")
        repo.list_share_requests_for_org.assert_not_called()

    def test_incoming_direction_returns_mapped_rows(self, service, repo):
        row = {
            "id": _uid().bytes, "requesting_org_id": 2, "target_org_id": 1, "status": "pending",
            "message": None, "requested_by": _uid().bytes, "reviewed_by": None, "review_reason": None,
            "created_at": 1, "resolved_at": None,
            "other_org_name": "Requester", "other_org_abbreviation": "REQ",
        }
        repo.list_share_requests_for_org.return_value = [row]

        result = service.list_org_share_requests(1, "incoming", status="pending")

        assert result[0]["other_org_name"] == "Requester"
        repo.list_share_requests_for_org.assert_called_once_with(1, "incoming", status="pending")


class TestListOrgInvitations:

    def test_merges_invitee_fields(self, service, repo):
        row = {
            "id": _uid().bytes, "org_id": 1, "user_id": _uid().bytes, "invited_by": _uid().bytes,
            "status": "pending", "message": None, "created_at": 1, "resolved_at": None,
            "username": "bob", "email": "bob@x.com", "first_name": "Bob", "last_name": "Jones",
        }
        repo.list_invitations_for_org.return_value = [row]

        result = service.list_org_invitations(1, status="pending")

        assert result[0]["username"] == "bob"
        repo.list_invitations_for_org.assert_called_once_with(1, status="pending")


class TestListUserInvitations:

    def test_merges_org_fields(self, service, repo):
        row = {
            "id": _uid().bytes, "org_id": 1, "user_id": _uid().bytes, "invited_by": _uid().bytes,
            "status": "pending", "message": None, "created_at": 1, "resolved_at": None,
            "org_name": "Acme", "org_abbreviation": "ACM",
        }
        repo.list_invitations_for_user.return_value = [row]
        user_id = _uid()

        result = service.list_user_invitations(user_id, status="pending")

        assert result[0]["org_name"] == "Acme"
        repo.list_invitations_for_user.assert_called_once_with(user_id, status="pending")
