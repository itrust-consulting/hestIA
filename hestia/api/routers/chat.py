from fastapi import APIRouter, Depends
from fastapi.responses import Response, StreamingResponse

from hestia.api.dependencies import get_handler
from hestia.api.schemas.requests import ChatRequest
from hestia.api.security import get_current_user
from hestia.domain.auth.models import User
from hestia.domain.rag.graph import ExecutionRequest
from hestia.handler import RequestHandler

router = APIRouter()


@router.post("/chat")
def chat(
    req: ChatRequest,
    h: RequestHandler = Depends(get_handler),
    user: User = Depends(get_current_user),
):
    last_user_message = next(
        (m["content"] for m in reversed(req.messages) if m["role"] == "user"), None
    )

    exec_req = ExecutionRequest(
        user=user,
        exec_type="rag_chat" if req.collection else "chat",
        history=req.messages[:-1],
        last_user_message=last_user_message,
        last_user_display_content=req.last_user_display_content,
        last_user_attachments=req.last_user_attachments,
        model=req.model,
        model_kwargs=req.model_kwargs,
        collection=req.collection,
        query_kwargs=req.query_kwargs,
        conversation_id=req.conversation_id,
        conversation_title=req.conversation_title,
        save_chat=req.save_chat,
        stream=req.stream,
    )

    if req.stream:
        return StreamingResponse(h.resolve(exec_req, stream=True), media_type="application/json")
    return Response(h.resolve(exec_req), media_type="application/json")
