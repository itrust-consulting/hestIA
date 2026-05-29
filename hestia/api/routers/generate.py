from fastapi import APIRouter, Depends
from fastapi.responses import Response, StreamingResponse

from hestia.api.dependencies import get_handler
from hestia.api.schemas.requests import GenerateRequest
from hestia.api.security import get_current_user
from hestia.domain.auth.models import User
from hestia.domain.rag.graph import ExecutionRequest
from hestia.handler import RequestHandler

router = APIRouter()


@router.post("/generate")
def generate(
    req: GenerateRequest,
    h: RequestHandler = Depends(get_handler),
    user: User = Depends(get_current_user),
):
    exec_req = ExecutionRequest(
        user=user,
        exec_type="rag_generate" if req.collection else "generate",
        prompt=req.prompt,
        model=req.model,
        model_kwargs=req.model_kwargs,
        collection=req.collection,
        query_kwargs=req.query_kwargs,
        stream=req.stream,
    )

    if req.stream:
        return StreamingResponse(h.resolve(exec_req, stream=True), media_type="application/json")
    return Response(h.resolve(exec_req), media_type="application/json")
