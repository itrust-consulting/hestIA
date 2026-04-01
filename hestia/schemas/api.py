from pydantic import BaseModel, Field
from typing import Optional, Union, List, Dict, Any, Literal, TypeAlias, Tuple

import uuid
from hestia.schemas.base import APIModel, Request, Response


class GenerateRequest(Request):
    prompt: str = Field(..., description="Prompt.")
    model: Optional[str] = Field(None, description="Generate model override.")
    model_kwargs: Optional[Dict[str, Any]] = Field(None, description="Provider-specific options pass-through.")
    collection: Optional[str] = Field(None, description="Spcify collection for augmented retrieval.")
    query_kwargs: Optional[Dict[str, Any]] = Field(None, description="Augmented retrieval provider-specific query options pass-through")
    stream: bool = Field(False, description="If True, stream tokens as plain text.")


class GenerateData(APIModel):
    response: str


GenerateResponse = Response[GenerateData]


class ChatRequest(Request):
    conversation_id: Optional[str] = Field(None, description="Conversation id of the active chat. Required to save chats.")
    conversation_title: Optional[str] = Field(None, description="Conversation title of the active chat.")
    messages: List[Dict[str, Any]] = Field(..., description="Chat history. Last user message drives the response.")
    model: Optional[str] = Field(None, description="Chat model override.")
    model_kwargs: Optional[Dict[str, Any]] = Field(None, description="Provider-specific options pass-through.")
    collection: Optional[str] = Field(None, description="Colllection name.")
    query_kwargs: Optional[Dict[str, Any]] = Field(None, description="Provider-specific options pass-through.")
    save_chat: bool = Field(False, description="If True, chat conversation is stored.")
    stream: bool = Field(False, description="If True, stream tokens as plain text.")


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


# This should move to types/models
class SparseVector(APIModel):
    indices: List[int]
    values: List[float]

class DenseVector(APIModel):
    vector: List[float]

class HybridQuery(APIModel):
    dense: DenseVector
    sparse: SparseVector

Query: TypeAlias = Union[
    DenseVector,
    SparseVector,
    HybridQuery,
    ]
QueryMode = Literal["semantic", "keyword", "hybrid"]

class QueryPoints(APIModel):
    id: str
    score: float
    payload: Optional[Dict[str, Any]]
    vector: Optional[Union[List[float], List[List[float]]]]


class SearchRequest(Request):
    mode: QueryMode = Field("dense", description="Query mode: 'semantic', 'keyword', 'hybrid'")
    query: List[float | int] | Dict[str, Any] = Field(..., description="Vector queries.")
    collection: str = Field(..., description="Collection to query.")
    options: Dict[str, Any] = Field(None, description="Query options.")


class SearchData(APIModel):
    points: List[QueryPoints]

SearchResponse = Response[Any]

class Permissions(BaseModel):
    use_rag: bool = False
    max_classification: int = 0
    allowed_collections: List[str] = []

    manage_users: bool = False
    assign_roles: bool = False
    view_users: bool = False

    configure_llm: bool = False
    view_llm_status: bool = False

    manage_system: bool = False
    manage_database: bool = False
    view_system_status: bool = False

    manage_documents: bool = False
    manage_collections: bool = False
    reindex_corpus: bool = False

    # catch-all for future dynamic permissions
    extra: Dict[str, Any] = {}


from enum import Enum
class Role(str, Enum):
    ADMIN = "admin"
    MODERATOR = "moderator"
    AUDITOR = "auditor"
    ISMS = "isms_member"
    USER = "user"
    GUEST = "guest"

class User(BaseModel):
    id: uuid.UUID
    username: str
    roles: list[str]
    permissions: Permissions
    must_change_pw: bool
    created_at: int


class ExecutionRequest(BaseModel):
    user: User
    exec_type: str
    history: Optional[List[Dict[str, Any]]] = None
    # prompt and last_user_message effectively the same, only for readabilty
    last_user_message: Optional[str] = None
    prompt: Optional[str] = None
    model: Optional[str] = None
    model_kwargs: Optional[Dict[str, Any]] = None
    collection: Optional[str] = None
    query_kwargs: Optional[Dict[str, Any]] = None
    conversation_id: Optional[str] = None
    conversation_title: Optional[str] = None
    save_chat: bool = False
    stream: bool = False

class Node(BaseModel):
    id: str
    type: str
    inputs: Dict[str, Any]
    outputs: Dict[str, Any]
    options: Optional[Dict[str, Any]] = None
    model: Optional[str] = None

class ExecutionGraph(BaseModel):
    nodes: List[Node]
    edges: List[Tuple[str, str]] = Field(default_factory=list)
    entrypoint: str
    exitpoints: List[str] = Field(default_factory=list)
    context_refs: Dict[str, str] = Field(default_factory=dict)  # e.g. kv://... refs