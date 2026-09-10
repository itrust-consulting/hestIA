from fastapi import APIRouter, Depends, HTTPException

from hestia.api.dependencies import get_container
from hestia.api.schemas.requests import SearchRequest
from hestia.api.security import get_current_user
from hestia.container import Container
from hestia.domain.auth.models import User
from hestia.domain.policies.guard import ExecutionPolicy, PolicyDecision
from hestia.domain.rag.graph import ExecutionRequest
from hestia.domain.rag.types import DenseVector, HybridQuery, SparseVector

router = APIRouter()

_policy = ExecutionPolicy()


# @MRS-034, @MRS-085
@router.post("/search")
async def search(
    req: SearchRequest,
    c: Container = Depends(get_container),
    user: User = Depends(get_current_user),
):
    if not user.permissions.can_read_collection(req.collection):
        raise HTTPException(403, "Access to this collection is not permitted.")

    # Admins bypass can_read_collection above regardless of an explicit ACL
    # entry (User.permissions.can_read_collection), so the policy check below
    # -- which has no such bypass -- only runs for non-admins. For everyone
    # else, this forces the same server-side max_classification cap the RAG
    # path already applies (handler.py's resolve()), instead of trusting
    # whatever (or no) classification filter the client put in req.options.
    if not user.permissions.is_admin:
        policy_req = ExecutionRequest(user=user, exec_type="search", collection=req.collection)
        result = _policy.check(policy_req)
        if result.decision == PolicyDecision.DENY:
            raise HTTPException(403, result.msg or "Access to this collection is not permitted.")
        if result.decision == PolicyDecision.FILTER:
            req.options = req.options or {}
            req.options["filters"] = result.filters

    retriever = c.require_service("search")

    if req.mode == "semantic":
        query = DenseVector(vector=req.query)
    elif req.mode == "keyword":
        query = SparseVector(indices=req.query.get("indices"), values=req.query.get("values"))
    elif req.mode == "hybrid":
        query = HybridQuery(
            dense=DenseVector(vector=req.query.get("dense")),
            sparse=SparseVector(
                indices=req.query.get("sparse", {}).get("indices"),
                values=req.query.get("sparse", {}).get("values"),
            ),
        )
    else:
        query = DenseVector(vector=req.query)

    result = await retriever.retrieve(collection=req.collection, query=query, options=req.options)
    return {"data": result}
