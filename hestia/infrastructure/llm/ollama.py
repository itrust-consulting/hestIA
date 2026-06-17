from __future__ import annotations

import logging
from typing import Any, AsyncIterator, Callable, Dict, List, Literal, Optional, overload

from hestia.infrastructure.http.client import HttpClient
from hestia.infrastructure.llm.protocol import LLMProvider

Message = Dict[str, str]
ChunkExtractor = Callable[[Dict[str, Any]], Optional[str]]

_log = logging.getLogger("hestia.system")


# @MRS-022
class OllamaProvider(LLMProvider):

    def __init__(self, http: str | HttpClient, model: Optional[str] = None, timeout: tuple[float, float] = (10.0, 800.0)):
        self.http = http if isinstance(http, HttpClient) else HttpClient(base_url=http, timeout=timeout)
        self.model = model

    async def embed(self, inputs: List[str] | str, *, model: str | None = None, options: Dict[str, Any] | None = None) -> List[List[float]]:
        _m = model or self.model
        _inputs = list(inputs) if isinstance(inputs, str) else inputs
        _log.debug("ollama_embed", extra={"model": _m, "n_inputs": len(_inputs)})
        payload = {"model": _m, "input": _inputs, "options": options}
        j = await self.http.post("/api/embed", payload)
        result = j.json().get("embeddings") or []
        _log.debug("ollama_embed_done", extra={"model": _m, "n_vectors": len(result)})
        return result

    def embed_blocking(self, inputs: List[str] | str, *, model: str | None = None, options: Dict[str, Any] | None = None) -> List[List[float]]:
        _m = model or self.model
        _inputs = list(inputs) if isinstance(inputs, str) else inputs
        payload = {"model": _m, "input": _inputs, "options": options}
        j = self.http.post_blocking("/api/embed", payload)
        return j.json().get("embeddings") or []

    @overload
    async def generate(self, prompt: str, *, model: str | None = None, options: Dict[str, Any] | None = None, stream: Literal[False] = False) -> str: ...
    @overload
    async def generate(self, prompt: str, *, model: str | None = None, options: Dict[str, Any] | None = None, stream: Literal[True]) -> AsyncIterator[Dict[str, str]]: ...

    async def generate(self, prompt: str, *, model: str | None = None, options: Dict[str, Any] | None = None, stream: bool = False):
        _m = model or self.model
        _log.debug("ollama_generate", extra={"model": _m, "prompt_len": len(prompt), "stream": stream})
        payload = {"model": _m, "prompt": prompt, "options": options, "stream": stream}
        if stream:
            return self._stream("/api/generate", payload, extract=lambda x: x.get("response"))
        j = await self.http.post("/api/generate", payload)
        resp = (j.json().get("response") or "").strip()
        _log.debug("ollama_generate_done", extra={"model": _m, "response_len": len(resp)})
        return resp

    @overload
    async def chat(self, messages: List[Message], *, model: str | None = None, options: Optional[Dict[str, Any]] = None, stream: Literal[False] = False) -> str: ...
    @overload
    async def chat(self, messages: List[Message], *, model: str | None = None, options: Optional[Dict[str, Any]] = None, stream: Literal[True]) -> AsyncIterator[Dict[str, str]]: ...

    async def chat(self, messages: List[Message], *, model: str | None = None, options: Dict[str, Any] | None = None, stream: bool = False):
        _m = model or self.model
        _log.debug("ollama_chat", extra={"model": _m, "n_messages": len(messages), "stream": stream})
        payload = {"model": _m, "messages": messages, "options": options, "stream": stream}
        if stream:
            return self._stream(
                "/api/chat", payload,
                extract=lambda x: (x.get("message") or {}).get("content"),
                extract_thinking=lambda x: (x.get("message") or {}).get("thinking"),
            )
        j = await self.http.post("/api/chat", payload)
        msg = (j.json().get("message") or {}).get("content", "")
        resp = (msg or "").strip()
        _log.debug("ollama_chat_done", extra={"model": _m, "response_len": len(resp)})
        return resp

    async def _stream(
        self,
        endpoint: str,
        payload: Dict[str, Any],
        extract: ChunkExtractor,
        extract_thinking: ChunkExtractor | None = None,
    ) -> AsyncIterator[Dict[str, str]]:
        async with (await self.http.post(endpoint, payload, stream=True)) as r:
            async for obj in self.http.iter_ndjson(r):
                content = extract(obj) or ""
                thinking = (extract_thinking(obj) if extract_thinking else None) or ""
                if content or thinking:
                    yield {"content": content, "thinking": thinking}
                if obj.get("done"):
                    break

    @property
    def models(self) -> dict:
        j = self.http.get_blocking("/api/tags")
        model_list = j.json().get("models") or []
        return {"models": [{"id": i, "model": m.get("model")} for i, m in enumerate(model_list)]}

    async def aclose(self) -> None:
        await self.http.aclose()
