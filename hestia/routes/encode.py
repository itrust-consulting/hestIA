from fastapi import APIRouter, Depends
from hestia.container import Container
from hestia.utils.deps import get_container
from hestia.schemas.api import EncodeRequest, EncodeResponse


router = APIRouter()

@router.post("/encode", response_model=EncodeResponse)
def encode(req: EncodeRequest, c: Container = Depends(get_container)):
    
    if req.type == "dense":
        encoder = c.services["encDense"]
        dense_vector = encoder.encode(req.input, model=req.model, options=req.options)
        used_model = req.model or encoder.default_model
        
        return EncodeResponse(
            type="dense",
            vector=dense_vector.vector,
            model=used_model,
            meta={"count": len(dense_vector.vector)}
        )

    elif req.type == "sparse":
        if not req.collection:
            raise ValueError("Sparse encoding requires the collection/corpus name.")
        encoder = c.services["encSparse"]
        sparse_vector = encoder.encode(req.input, req.collection)
        
        return EncodeResponse(
            type="sparse",
            vector=sparse_vector,          
            meta={"collection": req.collection}
        )