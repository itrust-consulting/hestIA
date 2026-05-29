from __future__ import annotations

from typing import Any, Dict, List, Optional, Union
from typing import TypeAlias

from pydantic import BaseModel


class SparseVector(BaseModel):
    indices: List[int]
    values: List[float]


class DenseVector(BaseModel):
    vector: List[float]


class HybridQuery(BaseModel):
    dense: DenseVector
    sparse: SparseVector


Query: TypeAlias = Union[DenseVector, SparseVector, HybridQuery]
