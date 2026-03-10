from typing import Literal, get_args

LLMBackend = Literal["ollama"]      # extend later
DBBackend  = Literal["qdrant"]      # extend later

ServiceName = Literal["embed", "generate", "chat", "retrieve", "rerank"]

Mode = Literal["simple", "q2e", "hyDE", ] # "cot", "contrast""hybrid", "extract", , 
_AVAILABLE_MODES = list(get_args(Mode))

Ranking = Literal["rrf", "dbsf", "max_score"]
_ALLOWED_RANKINGS = set(get_args(Ranking))
