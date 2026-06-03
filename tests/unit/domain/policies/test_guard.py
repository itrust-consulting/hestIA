from __future__ import annotations

import uuid
from unittest.mock import MagicMock, patch

import pytest

from hestia.domain.auth.models import CollectionPermission, Permissions, User
from hestia.domain.policies.guard import (
    CollectionAccessPolicy,
    ExecutionPolicy,
    PolicyDecision,
)
from hestia.domain.rag.graph import ExecutionRequest


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _user(is_admin=False, allowed_collections=None):
    return User(
        id=uuid.uuid4(),
        username="u",
        email="u@x.com",
        first_name="U",
        last_name="U",
        roles=[],
        orgs=[],
        permissions=Permissions(
            is_admin=is_admin,
            allowed_collections=allowed_collections or {},
        ),
        must_change_pw=False,
        auth_source="local",
        created_at=0,
        updated_at=0,
        expires_at=None,
    )


def _req(exec_type="rag_chat", collection="col-1", user=None):
    return ExecutionRequest(
        user=user or _user(),
        exec_type=exec_type,
        collection=collection,
    )


# ---------------------------------------------------------------------------
# CollectionAccessPolicy
# ---------------------------------------------------------------------------

class TestCollectionAccessPolicy:

    policy = CollectionAccessPolicy()

    def test_allows_non_rag_exec_type(self):
        r = self.policy.check(_req(exec_type="chat"))
        assert r.decision == PolicyDecision.ALLOW

    def test_allows_when_no_collection(self):
        r = self.policy.check(_req(exec_type="rag_chat", collection=None))
        assert r.decision == PolicyDecision.ALLOW

    def test_denies_when_user_has_no_permission(self):
        r = self.policy.check(_req(exec_type="rag_chat", collection="secret-col"))
        assert r.decision == PolicyDecision.DENY

    def test_filters_when_user_has_explicit_permission(self):
        user = _user(allowed_collections={
            "col-1": CollectionPermission(access=True, max_classification=2)
        })
        r = self.policy.check(_req(exec_type="rag_chat", user=user))
        assert r.decision == PolicyDecision.FILTER
        assert r.filters["max_classification"] == 2

    def test_wildcard_permission_grants_access(self):
        user = _user(allowed_collections={
            "*": CollectionPermission(access=True, max_classification=4)
        })
        r = self.policy.check(_req(exec_type="rag_chat", user=user))
        assert r.decision == PolicyDecision.FILTER

    def test_permission_without_access_denies(self):
        user = _user(allowed_collections={
            "col-1": CollectionPermission(access=False)
        })
        r = self.policy.check(_req(exec_type="rag_chat", user=user))
        assert r.decision == PolicyDecision.DENY

    def test_rag_generate_also_checked(self):
        r = self.policy.check(_req(exec_type="rag_generate", collection="col-1"))
        assert r.decision == PolicyDecision.DENY


# ---------------------------------------------------------------------------
# ExecutionPolicy
# ---------------------------------------------------------------------------

class TestExecutionPolicy:

    def test_allow_when_no_policies_deny(self):
        policy = ExecutionPolicy()
        with patch.object(CollectionAccessPolicy, "check",
                          return_value=MagicMock(decision=PolicyDecision.ALLOW)):
            r = policy.check(_req(exec_type="chat"))
        assert r.decision == PolicyDecision.ALLOW

    def test_returns_first_non_allow_result(self):
        user = _user()
        req = _req(exec_type="rag_chat", user=user)
        with patch("hestia.domain.policies.guard.audit"):
            policy = ExecutionPolicy()
            r = policy.check(req)
        assert r.decision == PolicyDecision.DENY

    def test_audit_called_on_deny(self):
        req = _req(exec_type="rag_chat")
        with patch("hestia.domain.policies.guard.audit") as mock_audit:
            ExecutionPolicy().check(req)
        mock_audit.policy_decision.assert_called_once()
