import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from hestia.api.dependencies import get_handler
from hestia.api.security import get_current_user
from hestia.domain.auth.models import User
from hestia.domain.chat.context_budget import check_context_budget, fetch_budget_inputs, run_compaction
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
    used_tokens: int | None = None
    max_tokens: int | None = None
    needs_compaction: bool | None = None


class CompactOut(BaseModel):
    status: str  # "compacted" | "not_needed"
    used_tokens: int
    max_tokens: int


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
    users = h.container.services.get("users")
    conversation_id = uuid.UUID(cid)
    result = users.get_conversation_messages(
        user.id,
        conversation_id,
        limit=limit,
        before_created_at=before_created_at,
        before_rowid=before_rowid,
    )
    if before_created_at is None:
        # Only the initial/most-recent page needs usage info -- pagination
        # calls (loadOlderMessages) don't display it and shouldn't pay for
        # the extra budget check.
        settings = h.container.settings
        prior_summary, tail = fetch_budget_inputs(users, user.id, conversation_id)
        check = check_context_budget(prior_summary, tail, settings)
        result = {
            **result,
            "used_tokens": check.tokens,
            "max_tokens": settings.max_context_tokens,
            "needs_compaction": check.needs_compaction,
        }
    return result


@router.post("/conversations/{cid}/compact", response_model=CompactOut)
async def compact_conversation(
    cid: str,
    h: RequestHandler = Depends(get_handler),
    user: User = Depends(get_current_user),
):
    users = h.container.services.get("users")
    settings = h.container.settings
    conversation_id = uuid.UUID(cid)
    prior_summary, tail = fetch_budget_inputs(users, user.id, conversation_id)
    check = check_context_budget(prior_summary, tail, settings, force=True)
    if not check.needs_compaction:
        return CompactOut(
            status="not_needed", used_tokens=check.tokens, max_tokens=settings.max_context_tokens,
        )
    generator = h.container.services.get("generate")
    await run_compaction(
        generator, settings, users, conversation_id, prior_summary, check.fold, check.keep,
    )
    new_summary, new_tail = fetch_budget_inputs(users, user.id, conversation_id)
    new_check = check_context_budget(new_summary, new_tail, settings)
    return CompactOut(
        status="compacted", used_tokens=new_check.tokens, max_tokens=settings.max_context_tokens,
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
