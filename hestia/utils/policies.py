from typing import Protocol, Any
from pydantic import BaseModel
from enum import Enum

from hestia.schemas.api import ExecutionRequest, Permissions

class PolicyDecision(Enum):
    ALLOW = "allow"
    DENY = "deny"
    FILTER = "filter"

class PolicyResult(BaseModel):
    decision: PolicyDecision
    filters: dict[str, Any] = {}
    msg: str | None = None

class PolicyGuard(Protocol):
    def check(self, req: ExecutionRequest) -> None:
        ...

class CollectionAccessPolicy(PolicyGuard):

    def check(self, req: ExecutionRequest) -> PolicyResult:
        permissions: Permissions = req.user.permissions
        
        if req.exec_type not in {"rag_chat", "rag_generate"}:
            return PolicyResult(decision=PolicyDecision.ALLOW)

        collection = req.collection
        if not collection:
            return PolicyResult(decision=PolicyDecision.ALLOW)

        acl = permissions.allowed_collections

        perm = acl.get(collection) or acl.get("*")

        if not perm:
            return PolicyResult(
                decision=PolicyDecision.DENY,
                msg="Collection access denied."
            )

        if not perm.access:
            return PolicyResult(
                decision=PolicyDecision.DENY,
                msg="Collection access denied."
            )

        return PolicyResult(
            decision=PolicyDecision.FILTER,
            filters={
                "max_classification": perm.max_classification
            },
            msg=f"Max classification set to: {perm.max_classification}"
        )
    
class ExecutionPolicy(PolicyGuard):

    POLICIES = [
        CollectionAccessPolicy(),
    ]

    def check(self, req: ExecutionRequest) -> PolicyResult:
        for policy in self.POLICIES:
            result = policy.check(req)
            if result.decision != PolicyDecision.ALLOW:
                return result

        return PolicyResult(decision=PolicyDecision.ALLOW)
            