from fastapi import APIRouter, Depends, HTTPException

from hestia.api.dependencies import get_container
from hestia.api.schemas.requests import SearchRequest
from hestia.api.security import get_current_user
from hestia.container import Container
from hestia.domain.auth.models import User
from hestia.domain.rag.types import DenseVector, HybridQuery, SparseVector

router = APIRouter()


# @MRS-034, @MRS-085
@router.post("/search")
async def search(
    req: SearchRequest,
    c: Container = Depends(get_container),
    user: User = Depends(get_current_user),
):
    perms = user.permissions
    if not perms.is_admin:
        allowed = perms.allowed_collections
        wildcard = allowed.get("*")
        if not (wildcard and wildcard.access):
            perm = allowed.get(req.collection)
            if not perm or not perm.access:
                raise HTTPException(403, "Access to this collection is not permitted.")
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
