
from typing import Optional, Dict, List, Any, Literal, Iterator, overload

from hestia.protocols.llm import LLMProvider
import hestia.settings as s

Message = Dict[str, str]
class Generator:
    def __init__(self, provider: LLMProvider, model = s.DEFAULT_GEN_MODEL):
        self.provider = provider
        self.default_model = model

    @overload
    def generate(self, prompt: str, *, model: str | None = None, options: Optional[Dict[str, Any]] = None, stream: Literal[False] = False
                 ) -> str: ...

    @overload
    def generate(self, prompt: str, *, model: str | None = None, options: Optional[Dict[str, Any]] = None, stream: Literal[True] = True
                 ) -> Iterator[str]: ...

    def generate(self, 
                 prompt: str, 
                 *,
                 model: str | None = None,
                 options: Optional[Dict[str, Any]] = None,
                 stream: bool = False):
        return self.provider.generate(prompt, 
                                      model=model or self.default_model, 
                                      options=options,
                                      stream=stream)
    
    @overload
    def chat(self, messages: List[str], *, model: str | None = None, options: Optional[Dict[str, Any]] = None, stream: Literal[False] = False
             ) -> str: ...

    @overload
    def chat(self, messages: List[str], *, model: str | None = None, options: Optional[Dict[str, Any]] = None, stream: Literal[True] = True
             ) -> Iterator[str]: ...
    
    def chat(self, 
             messages: List[Message], 
             *,
             model: str | None = None,
             options: Optional[Dict[str, Any]] = None,
             stream: bool = False):
        return self.provider.chat(messages,
                                  model=model or self.default_model, 
                                  options=options,
                                  stream=stream)


