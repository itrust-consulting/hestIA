from fastapi import APIRouter, Depends

from hestia.api.dependencies import get_container
from hestia.api.schemas.requests import SearchRequest
from hestia.container import Container
from hestia.domain.rag.types import DenseVector, HybridQuery, SparseVector

router = APIRouter()


@router.post("/search")
def search(req: SearchRequest, c: Container = Depends(get_container)):
    retriever = c.services["search"]

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

    result = retriever.retrieve(collection=req.collection, query=query, options=req.options)
    return {"data": result}
