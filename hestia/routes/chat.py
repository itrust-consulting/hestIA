from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse, Response

from hestia.schemas.api import ChatRequest, ExecutionRequest
from hestia.utils.deps import get_handler
from hestia.handler import RequestHandler

from hestia.utils.security import User, get_current_user


router = APIRouter()

@router.post("/chat")
def chat(req: ChatRequest, 
             h: RequestHandler = Depends(get_handler),
             user: User  = Depends(get_current_user)):
    
    last_user_message = None
    for msg in reversed(req.messages):
        if msg["role"] == "user":
            last_user_message = msg["content"]
            break

    request = ExecutionRequest(
        user                =   user,
        exec_type           =   "rag_chat" if req.collection else "chat",
        history             =   req.messages[:-1],
        last_user_message   =   last_user_message,
        model               =   req.model,
        model_kwargs        =   req.model_kwargs,
        collection          =   req.collection,
        query_kwargs        =   req.query_kwargs,
        conversation_id     =   req.conversation_id,
        conversation_title  =   req.conversation_title,
        save_chat           =   req.save_chat,
        stream              =   req.stream if req.stream else False,
    )

    try:
        if req.stream:
            it = h.resolve(request, stream=True)
            return StreamingResponse(it, media_type="application/json")
        result = h.resolve(request)
        return Response(result, media_type="application/json")
    except PermissionError:
        raise HTTPException(403, "Forbidden")