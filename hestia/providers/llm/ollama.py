from typing import Sequence, List, Dict, Callable, Optional, Any, Literal, Iterator, overload

from hestia.protocols.llm import LLMProvider
from hestia.utils import HttpClient

Message = Dict[str, str] # {"role": "user"|"assistant"|"system", "content": "..."}
ChunkExtractor = Callable[[Dict[str, Any]], Optional[str]]

class OllamaProvider(LLMProvider):

    def __init__(self, 
                 http: str | HttpClient, 
                 model: Optional[str] = None):
        
        if isinstance(http, str):
            http = HttpClient(base_url=http)
        self.http = http
        self.model = model

    def embed(self, 
              inputs: Sequence[str], 
              *,
              model: str | None = None, 
              options: Dict[str, Any] | None = None ) -> List[List[float]]:
        
        ENDPOINT_URL = "/api/embed"
        payload = {"model": model or self.model, 
                   "input": list(inputs), 
                   "options": options}

        j = self.http.post(ENDPOINT_URL, payload)
        return j.json().get("embeddings") or []

    @overload
    def generate(self, prompt: str, *, model: str | None = None, options: Dict[str, Any] | None = None, stream: Literal[False] = False,
                 ) -> str: ...

    @overload
    def generate(self, prompt: str, *, model: str | None = None, options: Dict[str, Any] | None = None, stream: Literal[True] = True,
                 ) -> Iterator[str]: ...

    def generate(self, prompt: str, *,
                 model: str | None = None, 
                 options: Dict[str, Any] | None = None, 
                 stream: bool = False):
        
        ENDPOINT_URL = "/api/generate"
        payload = {"model": model or self.model, "prompt": prompt, "options": options, "stream": stream}
        if stream:
            return self._stream(ENDPOINT_URL, payload, extract=lambda x: x.get("response"))
        else:
            j = self.http.post(ENDPOINT_URL, payload)
            
            return (j.json().get("response") or "").strip()
        

    @overload
    def chat(self, messages: List[Message], *, model: str | None = None, options: Optional[Dict[str, Any]] = None, stream: Literal[False] = False
             )-> str: ...
    @overload
    def chat(self, messages: List[Message], *, model: str | None = None, options: Optional[Dict[str, Any]] = None, stream: Literal[True] = True
             ) -> Iterator[str]: ...

    def chat(self, 
             messages: List[Message],
             *,
             model: str | None = None, 
             options: Dict[str, Any] | None = None, 
             stream: bool = False):
        
        ENDPOINT_URL = "/api/chat"
        payload = {"model": model or self.model, "messages": messages, "options": options, "stream": stream}
        if stream:
            return self._stream(ENDPOINT_URL, payload, extract=lambda x: (x.get("message") or {}).get("content"))
        else:
            j = self.http.post(ENDPOINT_URL, payload)
            msg = (j.json().get("message") or {}).get("content", "")
            return (msg or "").strip()
        
    def _stream(self, endpoint: str , payload: Dict[str, Any], extract: ChunkExtractor) -> Iterator[str]:
        with self.http.post(endpoint, payload, stream=True) as r:
            for obj in self.http.iter_ndjson(r):
                chunk = extract(obj)
                if chunk:
                    yield chunk
                if obj.get("done"):
                    break

    @property
    def models(self):
        # TODO create ModelsResponse (or similar) to capture model name and use
        j = self.http.get("/api/tags")
        available_models = []
        model_list = j.json().get("models")
        if model_list:
            for idx, model in enumerate(model_list):
                available_models.append({"id": idx, "model" : model.get("model")})
        return {"models" : available_models}