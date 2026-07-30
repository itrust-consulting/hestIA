import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from hestia.api.dependencies import get_handler
from hestia.api.security import get_current_user
from hestia.domain.auth.models import User
from hestia.handler import RequestHandler

router = APIRouter()


class MessageOut(BaseModel):
    id: uuid.UUID
    role: str
    metadata: str | None
    content: str
    options: str | None
    created_at: int
    rowid: int


class MessageCursor(BaseModel):
    created_at: int
    rowid: int


class ConversationMessagesResponse(BaseModel):
    messages: list[MessageOut]
    has_more: bool
    next_cursor: MessageCursor | None


@router.get("/conversations")
def list_conversations(
    h: RequestHandler = Depends(get_handler),
    user: User = Depends(get_current_user),
):
    return h.container.services.get("users").get_user_conversations(user.id)


@router.patch("/conversations/{cid}")
def patch_conversation(
    cid: str,
    req: dict,
    h: RequestHandler = Depends(get_handler),
    user: User = Depends(get_current_user),
):
    new_title = req.get("title")
    if not new_title:
        raise HTTPException(400, "No title specified.")
    h.container.services.get("users").rename_user_conversation(user.id, uuid.UUID(cid), title=new_title)
    return {"status": "ok", "title": new_title}


@router.get("/conversations/{cid}", response_model=ConversationMessagesResponse)
def get_conversation_messages(
    cid: str,
    limit: int = Query(50, ge=1, le=200),
    before_created_at: int | None = None,
    before_rowid: int | None = None,
    h: RequestHandler = Depends(get_handler),
    user: User = Depends(get_current_user),
):
    return h.container.services.get("users").get_conversation_messages(
        user.id,
        uuid.UUID(cid),
        limit=limit,
        before_created_at=before_created_at,
        before_rowid=before_rowid,
    )


@router.delete("/conversations/{cid}")
def delete_conversation(
    cid: str,
    h: RequestHandler = Depends(get_handler),
    user: User = Depends(get_current_user),
):
    h.container.services.get("users").delete_user_conversation(user.id, uuid.UUID(cid))
    return {"status": "ok"}


@router.delete("/conversations/{cid}/messages/{mid}")
def delete_message(
    cid: str,
    mid: str,
    h: RequestHandler = Depends(get_handler),
    user: User = Depends(get_current_user),
):
    h.container.services.get("users").delete_conversation_message(user.id, uuid.UUID(cid), uuid.UUID(mid))
    return {"status": "ok"}
