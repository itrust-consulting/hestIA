from pydantic import BaseModel, Field
from typing import Optional, Union, List, Dict, Any, Literal, TypeAlias

from hestia.schemas.base import APIModel, Request, Response


class GenerateRequest(Request):
    prompt: str = Field(..., description="Prompt.")
    model: Optional[str] = Field(None, description="Generate model override.")
    options: Optional[Dict[str, Any]] = Field(None, description="Provider-specific options pass-through.")
    stream: bool = Field(False, description="If True, stream tokens as plain text.")


class GenerateData(APIModel):
    response: str


GenerateResponse = Response[GenerateData]


Role = Literal["system", "user", "assistant"]


class ChatMessage(BaseModel):
    role: Role
    content: str


class ChatRequest(Request):
    messages: List[ChatMessage] = Field(..., description="Chat history. Last user message drives the response.")
    model: Optional[str] = Field(None, description="Chat model override.")
    options: Optional[Dict[str, Any]] = Field(None, description="Provider-specific options pass-through.")
    stream: bool = Field(False, description="If True, stream tokens as plain text.")


class EmbedRequest(Request):
    inputs: Union[str, List[str]] = Field(..., description="Text(s) to embed.")
    model: Optional[str] = Field(None, description="Embedding model override.")
    options: Optional[Dict[str, Any]] = Field(None, description="Provider-specific options pass-through.")


class EmbedData(APIModel):
    embeddings: List[List[float]]


EmbedResponse = Response[EmbedData]


class RerankRequest(Request):
    inputs: Union[str, List[str]] = Field(..., description="Text(s) to rerank.")
    model: Optional[str] = Field(None, description="Rerank model override.")
    top_k: int | None = Field(None, description="Return only top_k.") 
    options: Optional[Dict[str, Any]] = Field(None, description="Provider-specific options pass-through.")


class RerankData(APIModel):
    scores: List[float]
    order: List[int]
    top_k: List[int]

RerankResponse = Response[RerankData]


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


class RAGenerateRequest(Request):
    collection: str
    message: str
    options: Dict[str, Any] = None
    stream: bool = False


RAGenerateResponse = Response[GenerateData]
