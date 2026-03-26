from __future__ import annotations

from typing import Any, Dict, Generic, Optional, TypeVar
from pydantic import BaseModel, ConfigDict, Field

T = TypeVar("T")

class APIModel(BaseModel):
    """
    Shared config for all API models.
    - extra="forbid": reject unknown fields (prevents silent bugs)
    - validate_assignment: keeps models consistent if mutated
    - populate_by_name: allows alias usage for in/out
    """
    model_config = ConfigDict(
        extra="forbid",
        validate_assignment=True,
        populate_by_name=True,
        str_strip_whitespace=True,
    )


class Request(APIModel):
    """
    Base request payload.
    Add request-scoped metadata that clients may optionally send.
    """
    request_id: Optional[str] = Field(
        default=None,
        description="Client-provided correlation ID (optional)."
    )
    meta: Dict[str, Any] = Field(
        default_factory=dict,
        description="Optional request metadata (debug flags, tags, etc.).",
    )


class Error(APIModel):
    code: str = Field(..., description="Machine-readable error code.")
    message: str = Field(..., description="Human-readable error message.")
    details: Dict[str, Any] = Field(default_factory=dict, description="Optional structured details.")


class Response(APIModel, Generic[T]):
    """
    Standard response envelope.
    """
    data: Optional[T] = Field(None, description="Response payload.")
    error: Optional[Error] = Field(None, description="Error payload if ok=false.")
    meta: Dict[str, Any] = Field(default_factory=dict, description="Response metadata (timings, model used, etc.).")

    @classmethod
    def success(cls, data: T, *, meta: Optional[Dict[str, Any]] = None) -> "Response[T]":
        return cls(data=data, error=None, meta=meta or {})

    @classmethod
    def fail(cls, code: str, message: str, *, details: Optional[Dict[str, Any]] = None, meta: Optional[Dict[str, Any]] = None) -> "Response[T]":
        return cls(data=None, error=Error(code=code, message=message, details=details or {}), meta=meta or {})