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

class ExecutionPolicy(PolicyGuard):

    def check(self, req: ExecutionRequest) -> None:
        permissions: Permissions = req.user.permissions

        if req.exec_type in ["rag_chat", "rag_generate"]:
            # check if user is allowed to retrieve from knowledge base
            if not permissions.use_rag:
                return PolicyResult(decision=PolicyDecision.DENY,
                                    msg="Retrieval permission denied.")
            
            # check if user is allowed to access requested collection
            if req.collection is not None:
                if permissions.allowed_collections != ["*"] and \
                req.collection not in permissions.allowed_collections:
                    return PolicyResult(decision=PolicyDecision.DENY,
                                        msg="Collection access denied.")
                
                # check user's max classification and set filter
                return PolicyResult(decision=PolicyDecision.FILTER,
                                    filters={
                                        "max_classification": permissions.max_classification,
                                    },
                                    msg=f"Max classification set to: {permissions.max_classification}")

        # allow generic "chat" and "generate" requests
        return PolicyResult(decision=PolicyDecision.ALLOW)
            