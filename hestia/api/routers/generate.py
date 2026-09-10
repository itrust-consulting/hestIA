import json

from fastapi import APIRouter, Depends, Request
from fastapi.responses import Response, StreamingResponse

from hestia.api.dependencies import get_handler
from hestia.api.schemas.requests import GenerateRequest
from hestia.api.security import get_current_user
from hestia.api.streaming import abort_on_disconnect
from hestia.domain.auth.models import User
from hestia.domain.rag.graph import ExecutionRequest
from hestia.handler import RequestHandler

router = APIRouter()


# @MRS-084
@router.post("/generate")
async def generate(
    req: GenerateRequest,
    request: Request,
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
        gen = abort_on_disconnect(request, await h.resolve(exec_req, stream=True))
        return StreamingResponse(gen, media_type="application/json")
    return Response(json.dumps({"content": await h.resolve(exec_req)}), media_type="application/json")
