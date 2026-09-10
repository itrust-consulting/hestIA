import json

from fastapi import APIRouter, Depends, Request
from fastapi.responses import Response, StreamingResponse

from hestia.api.dependencies import get_handler
from hestia.api.schemas.requests import ChatRequest
from hestia.api.security import get_current_user
from hestia.api.streaming import abort_on_disconnect
from hestia.domain.auth.models import User
from hestia.domain.rag.graph import ExecutionRequest, has_query_text
from hestia.handler import RequestHandler

router = APIRouter()


# @MRS-029, @MRS-084
@router.post("/chat")
async def chat(
    req: ChatRequest,
    request: Request,
    h: RequestHandler = Depends(get_handler),
    user: User = Depends(get_current_user),
):
    # The client always appends the current user message plus an empty
    # assistant placeholder before calling this endpoint (see
    # hestia-ui/src/lib/chat/actions.ts's sendMessage/streamFromHistoryInto),
    # so req.messages ends with [..., current_user_msg, empty_placeholder].
    # Slicing off just the last element (the placeholder) still leaves the
    # CURRENT turn inside "history" -- normally masked for existing
    # conversations because RequestHandler overwrites history from the
    # authoritative DB tail, but fully exposed on a brand-new conversation's
    # first message (no conversation_id yet, so that overwrite never runs),
    # producing two consecutive user-role messages sent to the model. Slice
    # at the last user-role message instead, which is correct in both cases.
    last_user_idx = next(
        (i for i in range(len(req.messages) - 1, -1, -1) if req.messages[i]["role"] == "user"),
        None,
    )
    last_user_message = req.messages[last_user_idx]["content"] if last_user_idx is not None else None
    history = req.messages[:last_user_idx] if last_user_idx is not None else req.messages

    # Retrieval needs a real query to search with -- a file-only turn (no
    # typed text) skips it entirely rather than embedding/searching on
    # nothing, and falls back to the plain chat template (no Encode/
    # Retrieve nodes); the attachment still reaches the model via
    # ${attached_documents} in that template's prompt.
    exec_req = ExecutionRequest(
        user=user,
        exec_type="rag_chat" if (
            req.collection and has_query_text(req.last_user_display_content, last_user_message)
        ) else "chat",
        history=history,
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
        gen = abort_on_disconnect(request, await h.resolve(exec_req, stream=True))
        return StreamingResponse(gen, media_type="application/json")
    return Response(json.dumps({"content": await h.resolve(exec_req)}), media_type="application/json")
