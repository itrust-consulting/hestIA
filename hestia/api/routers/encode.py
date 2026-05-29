from fastapi import APIRouter, Depends, HTTPException

from hestia.api.dependencies import get_container
from hestia.api.schemas.requests import EncodeRequest, EncodeResponse
from hestia.container import Container

router = APIRouter()


@router.post("/encode", response_model=EncodeResponse)
def encode(req: EncodeRequest, c: Container = Depends(get_container)):
    if req.type == "dense":
        encoder = c.services["encDense"]
        vec = encoder.encode(req.input, model=req.model, options=req.options)
        return EncodeResponse(type="dense", vector=vec.vector, model=req.model or encoder.default_model,
                              meta={"count": len(vec.vector)})

    if req.type == "sparse":
        if not req.collection:
            raise HTTPException(400, "Sparse encoding requires a collection name.")
        encoder = c.services["encSparse"]
        vec = encoder.encode(req.input, req.collection)
        return EncodeResponse(type="sparse", vector=vec, meta={"collection": req.collection})

    raise HTTPException(400, f"Unknown encoding type: {req.type}")
