
from typing import Optional, List, Dict, Any

from hestia.protocols.llm import LLMProvider
from hestia.settings import DEFAULT_EMB_MODEL


class Embedder:

    def __init__(self, provider: LLMProvider, model=DEFAULT_EMB_MODEL):
        self.provider = provider
        self.default_model = model

    def embed(self, inputs: str | List[str], 
              model: str | None = None, 
              options: Optional[Dict[str, Any]] = None) -> List[List[float]]:
        inputs = [inputs] if isinstance(inputs, str) else inputs
        use_model = model or self.default_model
        return self.provider.embed(inputs, model=use_model, options=options)
         
    
