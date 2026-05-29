from __future__ import annotations

import logging
from enum import Enum
from typing import Any, Protocol

from pydantic import BaseModel

from hestia.domain.auth.models import Permissions
from hestia.domain.rag.graph import ExecutionRequest
from hestia.infrastructure.logging.audit import audit

_log = logging.getLogger("hestia.system")


class PolicyDecision(Enum):
    ALLOW = "allow"
    DENY = "deny"
    FILTER = "filter"


class PolicyResult(BaseModel):
    decision: PolicyDecision
    filters: dict[str, Any] = {}
    msg: str | None = None


class PolicyGuard(Protocol):
    def check(self, req: ExecutionRequest) -> PolicyResult: ...


class CollectionAccessPolicy:

    def check(self, req: ExecutionRequest) -> PolicyResult:
        if req.exec_type not in {"rag_chat", "rag_generate"}:
            return PolicyResult(decision=PolicyDecision.ALLOW)

        collection = req.collection
        if not collection:
            return PolicyResult(decision=PolicyDecision.ALLOW)

        acl = req.user.permissions.allowed_collections
        perm = acl.get(collection) or acl.get("*")

        if not perm or not perm.access:
            return PolicyResult(decision=PolicyDecision.DENY, msg="Collection access denied.")

        return PolicyResult(
            decision=PolicyDecision.FILTER,
            filters={"max_classification": perm.max_classification},
            msg=f"Max classification: {perm.max_classification}",
        )


class ExecutionPolicy:

    POLICIES = [CollectionAccessPolicy()]

    def check(self, req: ExecutionRequest) -> PolicyResult:
        for policy in self.POLICIES:
            result = policy.check(req)
            if result.decision != PolicyDecision.ALLOW:
                audit.policy_decision(
                    user_id=str(req.user.id),
                    exec_type=req.exec_type,
                    collection=req.collection,
                    decision=result.decision.value,
                    reason=result.msg,
                )
                if result.decision == PolicyDecision.DENY:
                    _log.warning(
                        "policy_deny",
                        extra={"user_id": str(req.user.id), "exec_type": req.exec_type,
                               "collection": req.collection},
                    )
                return result

        return PolicyResult(decision=PolicyDecision.ALLOW)
