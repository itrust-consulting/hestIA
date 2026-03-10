from fastapi import APIRouter, Depends
from hestia.schemas.api import EmbedRequest, EmbedResponse, EmbedData
from hestia.container import Container
from hestia.utils.deps import get_container

router = APIRouter()

@router.post("/embed", response_model=EmbedResponse)
def embed(req: EmbedRequest, c: Container = Depends(get_container)) -> EmbedResponse:
    embedder = c.services["embed"]  # safe: router only registered if service exists
    vecs = embedder.embed(req.inputs, model=req.model, options=req.options)

    used_model = req.model or embedder.default_model
    return EmbedResponse.success(
        EmbedData(embeddings=vecs),
        meta={"model": used_model, "count": len(vecs)},
    )