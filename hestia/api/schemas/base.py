from __future__ import annotations

from typing import Any, Dict, Optional

from pydantic import BaseModel, ConfigDict, Field


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
