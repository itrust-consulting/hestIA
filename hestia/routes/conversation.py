from fastapi import APIRouter, Depends
from fastapi.exceptions import HTTPException
from hestia.utils.deps import get_handler
from hestia.handler import RequestHandler

from hestia.utils.security import User, get_current_user


router = APIRouter()


@router.get("/conversations")
def list_user_conversations(
    h: RequestHandler = Depends(get_handler),
    user: User = Depends(get_current_user)
):
    svc = h.container.services.get("auth")
    return svc.get_user_conversations(user.id.bytes)

@router.patch("/conversations/{cid}")
def patch_conversation(
    cid,
    req: dict,
    h: RequestHandler = Depends(get_handler),
    user: User = Depends(get_current_user)
    ):
    
    new_title = req.get("title")
    if not new_title:
        raise HTTPException(400, "No title specified.")
    
    svc = h.container.services.get("auth")
    svc.rename_user_conversation(user.id.bytes, bytes.fromhex(cid), title=req.get("title"))
    return {"status": "ok", "title": new_title}

@router.get("/conversations/{cid}")
def list_conversation_messages(
    cid,
    h: RequestHandler = Depends(get_handler),
    user: User = Depends(get_current_user)
):
    svc = h.container.services.get("auth")
    return svc.get_conversation_messages(bytes.fromhex(cid))

@router.delete("/conversations/{cid}")
def delete_conversation(
    cid,
    h: RequestHandler = Depends(get_handler),
    user: User = Depends(get_current_user)
    ):

    svc = h.container.services.get("auth")
    svc.delete_user_conversation(user.id.bytes, bytes.fromhex(cid))

@router.delete("/conversations/{cid}/messages/{mid}")
def delete_message(
    cid,
    mid,
    h: RequestHandler = Depends(get_handler),
    user: User = Depends(get_current_user)
    ):

    svc = h.container.services.get("auth")
    svc.delete_conversation_message(user.id.bytes, 
                                    bytes.fromhex(cid),
                                    bytes.fromhex(mid))