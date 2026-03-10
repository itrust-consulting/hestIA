from typing import Protocol, Union, List, Dict, Optional, Any

class LLMProvider(Protocol):
    def embed(self, 
              inputs: Union[str, List[str]], 
              *,
              model: str | None, 
              options: Optional[Dict[str, Any]] = None ) -> List[List[float]]:
        ...

    def generate(self, 
                 prompt: str, 
                 *,
                 model: str | None, 
                 options: Optional[Dict[str, Any]] = None,
                 stream: bool = False):
        ...

    def chat(self, 
             prompt: str,
             history:List[Dict[str, str]],
             *,
             model: str | None, 
             options: Optional[Dict[str, Any]] = None,
             stream: bool = False):
        ...
    
    @property
    def models(self):
        ...