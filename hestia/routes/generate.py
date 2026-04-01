from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse, Response

from hestia.schemas.api import GenerateRequest, ExecutionRequest
from hestia.handler import RequestHandler
from hestia.utils.deps import get_handler

from hestia.utils.security import User, get_current_user

router = APIRouter()

@router.post("/generate")
def generate(req: GenerateRequest, 
             h: RequestHandler = Depends(get_handler),
             user: User = Depends(get_current_user)):
    
    request = ExecutionRequest(
        permissions     =   user.permissions,
        exec_type       =   "rag_generate" if req.collection else "generate",
        prompt          =   req.prompt,
        model           =   req.model,
        model_kwargs    =   req.model_kwargs,
        collection      =   req.collection,
        query_kwargs    =   req.query_kwargs,
        stream          =   req.stream if req.stream else False,
    )
    
    if req.stream:
        it = h.resolve(request, stream=True)
        return StreamingResponse(it, media_type="application/json")
    result = h.resolve(request)
    return Response(result, media_type="applicaiton/json")