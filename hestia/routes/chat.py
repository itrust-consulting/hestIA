from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse, Response

from hestia.schemas.api import ChatRequest, ExecutionRequest
from hestia.utils.deps import get_handler
from hestia.handler import RequestHandler

router = APIRouter()

@router.post("/chat")
def generate(req: ChatRequest, h: RequestHandler = Depends(get_handler)):

    last_user_message = None
    for msg in reversed(req.messages):
        if msg["role"] == "user":
            last_user_message = msg["content"]
            break

    request = ExecutionRequest(
        exec_type="rag_chat" if req.collection else "chat",
        history=req.messages[:-1],
        last_user_message=last_user_message,
        model=req.model,
        model_kwargs=req.model_kwargs,
        collection=req.collection,
        query_kwargs=req.query_kwargs,
        stream =req.stream if req.stream else False,
    )
    if req.stream:
        it = h.resolve(request, stream=True)
        return StreamingResponse(it, media_type="application/json")
    result = h.resolve(request)
    return Response(result, media_type="application/json")