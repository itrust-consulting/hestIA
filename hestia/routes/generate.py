from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse, Response
from hestia.schemas.api import GenerateRequest, GenerateResponse, GenerateData
from hestia.container import Container
from hestia.utils.deps import get_container

router = APIRouter()

@router.post("/generate")
def generate(req: GenerateRequest, c: Container = Depends(get_container)):
    generator = c.services["generate"]  # safe: router only registered if service exists
    
    if req.stream:
        it = generator.generate(req.prompt, model=req.model, options=req.options, stream=True)
        return StreamingResponse(it, media_type="text/plain; charset=utf-8")
    response = generator.generate(req.prompt, model=req.model, options=req.options)
    """
    used_model = req.model or generator.default_model
    GenerateResponse.success(
        GenerateData(response=response),
        meta={"model": used_model},
    )"""
    return Response(response, media_type="text/plain; charset=utf-8")
