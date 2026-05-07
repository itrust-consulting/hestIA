from typing import Sequence, List, Dict, Callable, Optional, Any, Literal, Iterator, overload

from hestia.protocols.llm import LLMProvider
from hestia.utils import HttpClient

Message = Dict[str, str] # {"role": "user"|"assistant"|"system", "content": "..."}
ChunkExtractor = Callable[[Dict[str, Any]], Optional[str]]

class vLLMProvider(LLMProvider):

    def __init__(self, 
                 chat: str | HttpClient,
                 embed: str | HttpClient | None = None,
                 rerank: str | HttpClient | None = None, 
                 model: Optional[str] = None):
        
        def _hc(x):
            return x if isinstance(x, HttpClient) else HttpClient(base_url=x)

        self.http_chat = _hc(chat)
        self.http_embed = _hc(embed)
        self.http_rrk = _hc(rerank)
        self.model = model

    def embed(self, 
              inputs: Sequence[str], 
              *,
              model: str | None = None, 
              options: Dict[str, Any] | None = None ) -> List[List[float]]:
        
        ENDPOINT_URL = "/v1/embeddings"
        payload = {
                   "input": list(inputs), 
                   "options": options}

        j = self.http_embed.post(ENDPOINT_URL, payload)
        return [j.json().get("data")[0].get("embedding")] or []

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
        
        ENDPOINT_URL = "/v1/completions"
        payload = {"prompt": prompt, "options": options, "stream": stream}
        if stream:
            return self._stream(ENDPOINT_URL, payload, extract=lambda x: x.get("response"))
        else:
            j = self.http_chat.post(ENDPOINT_URL, payload)
            
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
        
        ENDPOINT_URL = "/v1/chat/completions"
        payload = {"messages": messages, "options": options, "stream": stream}
        if stream:
            return self._stream(ENDPOINT_URL, payload, extract=lambda obj: (
                obj.get("choices", [{}])[0].get("delta", {}).get("content")))
        else:
            j = self.http_chat.post(ENDPOINT_URL, payload)
            msg = (j.json().get("message") or {}).get("content", "")
            return (msg or "").strip()
        
    def _stream(self, endpoint: str , payload: Dict[str, Any], extract: ChunkExtractor) -> Iterator[str]:
        with self.http_chat.post(endpoint, payload, stream=True) as r:
            for obj in self.http_chat.iter_sse_json(r):
                chunk = extract(obj)
                if chunk:
                    yield chunk

    @property
    def models(self):
        # TODO create ModelsResponse (or similar) to capture model name and use
        j = self.http_chat.get("/v1/models")
        available_models = []
        model_list = j.json().get("models")
        if model_list:
            for idx, model in enumerate(model_list):
                available_models.append({"id": idx, "model" : model.get("model")})
        return {"models" : available_models}