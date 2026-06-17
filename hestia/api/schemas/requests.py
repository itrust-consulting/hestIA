from __future__ import annotations

from typing import Any, Dict, List, Literal, Optional, Union

from pydantic import BaseModel, Field

from hestia.api.schemas.base import APIModel, Request, Response
from hestia.domain.rag.types import DenseVector, HybridQuery, Query, SparseVector


# ---- LLM generation ----

class GenerateRequest(Request):
    prompt: str
    model: Optional[str] = None
    model_kwargs: Optional[Dict[str, Any]] = None
    collection: Optional[str] = None
    query_kwargs: Optional[Dict[str, Any]] = None
    stream: bool = False


class GenerateData(APIModel):
    response: str


GenerateResponse = Response[GenerateData]


# ---- Chat ----

# @MRS-037
class ChatRequest(Request):
    conversation_id: Optional[str] = None
    conversation_title: Optional[str] = None
    messages: List[Dict[str, Any]]
    model: Optional[str] = None
    model_kwargs: Optional[Dict[str, Any]] = None
    collection: Optional[str] = None
    query_kwargs: Optional[Dict[str, Any]] = None
    save_chat: bool = False
    stream: bool = False
    last_user_display_content: Optional[str] = None
    last_user_attachments: Optional[List[Dict[str, Any]]] = None


# ---- Encode ----

class EncodeRequest(BaseModel):
    type: Literal["dense", "sparse"]
    input: str
    model: Optional[str] = None
    options: Optional[Dict[str, Any]] = None
    collection: Optional[str] = None


class EncodeResponse(BaseModel):
    type: Literal["dense", "sparse"]
    vector: Any
    model: Optional[str] = None
    meta: Optional[Dict[str, Any]] = None


# ---- Search ----

QueryMode = Literal["semantic", "keyword", "hybrid"]


class SearchRequest(Request):
    mode: QueryMode = Field("dense")
    query: List[float | int] | Dict[str, Any]
    collection: str
    options: Dict[str, Any] = None


class QueryPoints(APIModel):
    id: str
    score: float
    payload: Optional[Dict[str, Any]]
    vector: Optional[Union[List[float], List[List[float]]]]


class SearchData(APIModel):
    points: List[QueryPoints]


SearchResponse = Response[Any]


# ---- User management ----

class CreateUserRequest(Request):
    username: str
    email: str
    first_name: str
    last_name: str
    password: str
    roles: list[int] = Field([0])
    organization: str = None
    expires_at: int | None = None


class CreateOrgRequest(Request):
    name: str
    abbreviation: str


class UpdateOrgRequest(Request):
    name: str
    abbreviation: str
