from fastapi import APIRouter, Depends

from hestia.schemas.api import SearchRequest, SearchResponse, DenseVector, SparseVector, HybridQuery
from hestia.container import Container
from hestia.utils.deps import get_container

router = APIRouter()

@router.post("/search")
def search(req: SearchRequest, c: Container = Depends(get_container)):
    search = c.services["search"]  # safe: router only registered if service exists
    
    selected_mode = req.mode
    if selected_mode == "semantic":
        query = DenseVector(vector=req.query)

    if selected_mode == "keyword":
        query = SparseVector(
            indicies=req.query.get("indices"),
            values=req.query.get("values"))
    
    if selected_mode == "hybrid":
        dense = DenseVector(vector=req.query.get("dense"))
        sparse= SparseVector(
            indices=req.query.get("sparse").get("indices"),
            values=req.query.get("sparse").get("values"))
        query = HybridQuery(dense=dense, sparse=sparse)

    result = search.retrieve(
            collection=req.collection,
            query=query,
            options=req.options)
    return SearchResponse(data=result)