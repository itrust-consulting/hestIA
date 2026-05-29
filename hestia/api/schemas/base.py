from __future__ import annotations

from typing import Any, Dict, Generic, Optional, TypeVar

from pydantic import BaseModel, ConfigDict, Field

T = TypeVar("T")


class APIModel(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        validate_assignment=True,
        populate_by_name=True,
        str_strip_whitespace=True,
    )


class Request(APIModel):
    request_id: Optional[str] = Field(default=None)
    meta: Dict[str, Any] = Field(default_factory=dict)


class Error(APIModel):
    code: str
    message: str
    details: Dict[str, Any] = Field(default_factory=dict)


class Response(APIModel, Generic[T]):
    data: Optional[T] = Field(None)
    error: Optional[Error] = Field(None)
    meta: Dict[str, Any] = Field(default_factory=dict)

    @classmethod
    def success(cls, data: T, *, meta: Optional[Dict[str, Any]] = None) -> "Response[T]":
        return cls(data=data, error=None, meta=meta or {})

    @classmethod
    def fail(cls, code: str, message: str, *, details: Optional[Dict[str, Any]] = None, meta: Optional[Dict[str, Any]] = None) -> "Response[T]":
        return cls(data=None, error=Error(code=code, message=message, details=details or {}), meta=meta or {})
