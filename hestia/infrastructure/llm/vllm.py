from __future__ import annotations

import logging
from typing import Any, AsyncIterator, Callable, Dict, List, Literal, Optional, overload

from hestia.infrastructure.http.client import HttpClient
from hestia.infrastructure.llm.protocol import LLMProvider

Message = Dict[str, Any]
ChunkExtractor = Callable[[Dict[str, Any]], Optional[str]]

_log = logging.getLogger("hestia.system")


# @MRS-022, @MRS-072
class vLLMProvider(LLMProvider):

    def __init__(
        self,
        chat: str | HttpClient,
        embed: str | HttpClient | None = None,
        rerank: str | HttpClient | None = None,
        model: Optional[str] = None,
        timeout: tuple[float, float] = (10.0, 800.0),
        api_key: Optional[str] = None,
    ):
        def _hc(x):
            if isinstance(x, HttpClient):
                return x
            return HttpClient(base_url=x, timeout=timeout, api_key=api_key)

        self.http_chat = _hc(chat)
        self.http_embed = _hc(embed) if embed else self.http_chat
        self.http_rrk = _hc(rerank) if rerank else self.http_chat
        self.model = model

    async def embed(
        self,
        inputs: List[str] | str,
        *,
        model: str | None = None,
        options: Dict[str, Any] | None = None,
    ) -> List[List[float]]:
        _m = model or self.model
        _inputs = list(inputs) if isinstance(inputs, str) else inputs
        _log.debug("vllm_embed", extra={"model": _m, "n_inputs": len(_inputs)})
        payload: Dict[str, Any] = {"model": _m, "input": _inputs}
        if options:
            payload["options"] = options
        j = await self.http_embed.post("/v1/embeddings", payload)
        data = j.json().get("data") or []
        result = [item.get("embedding") for item in data]
        _log.debug("vllm_embed_done", extra={"model": _m, "n_returned": len(result)})
        return result

    def embed_blocking(
        self,
        inputs: List[str] | str,
        *,
        model: str | None = None,
        options: Dict[str, Any] | None = None,
    ) -> List[List[float]]:
        _m = model or self.model
        _inputs = list(inputs) if isinstance(inputs, str) else inputs
        payload: Dict[str, Any] = {"model": _m, "input": _inputs}
        if options:
            payload["options"] = options
        j = self.http_embed.post_blocking("/v1/embeddings", payload)
        data = j.json().get("data") or []
        return [item.get("embedding") for item in data]

    @overload
    async def generate(self, prompt: str, *, model: str | None = None, options: Dict[str, Any] | None = None, stream: Literal[False] = False) -> str: ...
    @overload
    async def generate(self, prompt: str, *, model: str | None = None, options: Dict[str, Any] | None = None, stream: Literal[True]) -> AsyncIterator[Dict[str, str]]: ...

    async def generate(self, prompt: str, *, model: str | None = None, options: Dict[str, Any] | None = None, stream: bool = False):
        _m = model or self.model
        _log.debug("vllm_generate", extra={"model": _m, "prompt_len": len(prompt), "stream": stream})
        # sampling params go at the top level (OpenAI-compatible /v1/completions
        # contract) -- NOT nested under an "options" key, which is Ollama's native
        # convention and is silently ignored here, e.g. max_tokens never applied.
        payload = {"prompt": prompt, "stream": stream, **(options or {})}
        if stream:
            return self._stream(
                "/v1/completions", payload,
                extract=lambda x: (x.get("choices", [{}])[0].get("text")),
            )
        j = await self.http_chat.post("/v1/completions", payload)
        choices = j.json().get("choices") or []
        resp = ((choices[0].get("text") if choices else "") or "").strip()
        _log.debug("vllm_generate_done", extra={"model": _m, "response_len": len(resp)})
        return resp

    @overload
    async def chat(self, messages: List[Message], *, model: str | None = None, options: Optional[Dict[str, Any]] = None, stream: Literal[False] = False) -> str: ...
    @overload
    async def chat(self, messages: List[Message], *, model: str | None = None, options: Optional[Dict[str, Any]] = None, stream: Literal[True]) -> AsyncIterator[Dict[str, str]]: ...

    async def chat(self, messages: List[Message], *, model: str | None = None, options: Dict[str, Any] | None = None, stream: bool = False):
        _m = model or self.model
        _log.debug("vllm_chat", extra={"model": _m, "n_messages": len(messages), "stream": stream})
        # see generate() -- sampling params must be top-level, not nested.
        payload = {"messages": messages, "stream": stream, **(options or {})}
        if stream:
            return self._stream(
                "/v1/chat/completions",
                payload,
                extract=lambda obj: (obj.get("choices", [{}])[0].get("delta", {}).get("content")),
                extract_thinking=lambda obj: (obj.get("choices", [{}])[0].get("delta", {}).get("reasoning")),
            )
        j = await self.http_chat.post("/v1/chat/completions", payload)
        choices = j.json().get("choices") or []
        msg = (choices[0].get("message") or {}) if choices else {}
        resp = (msg.get("content") or "").strip()
        _log.debug("vllm_chat_done", extra={"model": _m, "response_len": len(resp)})
        return resp

    async def _stream(
        self,
        endpoint: str,
        payload: Dict[str, Any],
        extract: ChunkExtractor,
        extract_thinking: ChunkExtractor | None = None,
    ) -> AsyncIterator[Dict[str, str]]:
        async with (await self.http_chat.post(endpoint, payload, stream=True)) as r:
            async for obj in self.http_chat.iter_sse_json(r):
                _log.debug("vllm_sse_chunk", extra={"delta": (obj.get("choices") or [{}])[0].get("delta")})
                content = extract(obj) or ""
                thinking = (extract_thinking(obj) if extract_thinking else None) or ""
                if content or thinking:
                    yield {"content": content, "thinking": thinking}

    @property
    def models(self) -> dict:
        j = self.http_chat.get_blocking("/v1/models")
        model_list = j.json().get("models") or []
        return {"models": [{"id": i, "model": m.get("model")} for i, m in enumerate(model_list)]}

    async def aclose(self) -> None:
        closed: set[int] = set()
        for client in [self.http_chat, self.http_embed, self.http_rrk]:
            if id(client) not in closed:
                await client.aclose()
                closed.add(id(client))
