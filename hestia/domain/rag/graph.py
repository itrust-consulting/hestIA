from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple, Union

from pydantic import BaseModel, Field

from hestia.domain.auth.models import User


class ExecutionRequest(BaseModel):
    user: User
    exec_type: str
    history: Optional[List[Dict[str, Any]]] = None
    last_user_message: Optional[Union[str, List[Any]]] = None
    last_user_display_content: Optional[str] = None
    last_user_attachments: Optional[List[Dict[str, Any]]] = None
    prompt: Optional[str] = None
    model: Optional[str] = None
    model_kwargs: Optional[Dict[str, Any]] = None
    collection: Optional[str] = None
    query_kwargs: Optional[Dict[str, Any]] = None
    conversation_id: Optional[str] = None
    conversation_title: Optional[str] = None
    save_chat: bool = False
    stream: bool = False
    # Set by RequestHandler._check_and_compact_budget when this turn's
    # incoming history was over budget and got folded before generation
    # started -- carried through so the final stream frame can announce it.
    freed_tokens: Optional[int] = None


class Node(BaseModel):
    id: str
    type: str
    inputs: Dict[str, Any]
    outputs: Dict[str, Any]
    options: Optional[Dict[str, Any]] = None
    model: Optional[str] = None


# @MRS-058
class ExecutionGraph(BaseModel):
    nodes: List[Node]
    edges: List[Tuple[str, str]] = Field(default_factory=list)
    entrypoint: str
    exitpoints: List[str] = Field(default_factory=list)
    context_refs: Dict[str, str] = Field(default_factory=dict)
