from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse, Response
from hestia.schemas.api import GenerateRequest, GenerateResponse, GenerateData, ChatRequest
from hestia.container import Container
from hestia.utils.deps import get_container

router = APIRouter()

@router.post("/chat")
def generate(req: ChatRequest, c: Container = Depends(get_container)):
    generator = c.services["chat"]  # safe: router only registered if service exists
    
    messages = [{"role": m.role, "content": m.content} for m in req.messages]
    if req.stream:
        it = generator.chat(messages, model=req.model, options=req.options, stream=True)
        return StreamingResponse(it, media_type="application/json")
    response = generator.chat(messages, model=req.model, options=req.options)

    return Response(response, media_type="application/json")
