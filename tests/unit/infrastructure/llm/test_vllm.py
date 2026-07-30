from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock

import pytest

from hestia.infrastructure.llm.vllm import vLLMProvider


# ---------------------------------------------------------------------------
# Fixture
# ---------------------------------------------------------------------------

@pytest.fixture
def mock_http():
    return MagicMock()


@pytest.fixture
def provider(mock_http):
    p = vLLMProvider.__new__(vLLMProvider)
    p.http_chat = mock_http
    p.http_embed = mock_http
    p.http_rrk = mock_http
    p.model = "mistral"
    return p


# ---------------------------------------------------------------------------
# embed
# ---------------------------------------------------------------------------

class TestVLLMEmbed:

    def test_normalizes_string_to_list(self, provider, mock_http):
        resp = MagicMock()
        resp.json.return_value = {"data": [{"embedding": [0.1]}]}
        mock_http.post = AsyncMock(return_value=resp)
        asyncio.run(provider.embed("hello"))
        payload = mock_http.post.call_args[0][1]
        assert isinstance(payload["input"], list)

    def test_returns_embeddings(self, provider, mock_http):
        resp = MagicMock()
        resp.json.return_value = {"data": [{"embedding": [0.1, 0.2]}]}
        mock_http.post = AsyncMock(return_value=resp)
        result = asyncio.run(provider.embed(["hello"]))
        assert result == [[0.1, 0.2]]


# ---------------------------------------------------------------------------
# generate (non-streaming)
# ---------------------------------------------------------------------------

class TestVLLMGenerate:
    # provider.generate() is async and HttpClient.post is awaited internally,
    # so http_chat.post must be an AsyncMock and the call must run inside an
    # event loop — see TestVLLMChat above for the same treatment/reasoning.

    def _generate_result(self, provider, mock_http, resp_json):
        resp = MagicMock()
        resp.json.return_value = resp_json
        mock_http.post = AsyncMock(return_value=resp)
        return asyncio.run(provider.generate("prompt"))

    def test_returns_stripped_response(self, provider, mock_http):
        # Standard OpenAI-compatible /v1/completions non-streaming shape —
        # text is nested under choices[0].text, not a top-level key.
        result = self._generate_result(provider, mock_http, {"choices": [{"text": "  answer  "}]})
        assert result == "answer"

    def test_empty_choices_returns_empty_string(self, provider, mock_http):
        result = self._generate_result(provider, mock_http, {"choices": []})
        assert result == ""

    def test_payload_includes_stream_flag(self, provider, mock_http):
        resp = MagicMock()
        resp.json.return_value = {"choices": [{"text": "ok"}]}
        mock_http.post = AsyncMock(return_value=resp)
        asyncio.run(provider.generate("prompt"))
        payload = mock_http.post.call_args[0][1]
        # model not in vllm payload (single-model deployment; matches chat()'s
        # payload, which also omits "model" and works correctly in production)
        assert "stream" in payload


# ---------------------------------------------------------------------------
# chat (non-streaming)
# ---------------------------------------------------------------------------

class TestVLLMChat:
    # provider.chat() is async and hestia.infrastructure.http.client.HttpClient.post
    # is awaited internally, so http_chat.post must be an AsyncMock and the call
    # itself must run inside an event loop — unlike the other test classes in
    # this file (pre-existing, unrelated to this fix), these three are wired
    # correctly so they actually exercise the real parsing logic.

    def _chat_result(self, provider, mock_http, resp_json, **kwargs):
        resp = MagicMock()
        resp.json.return_value = resp_json
        mock_http.post = AsyncMock(return_value=resp)
        return asyncio.run(provider.chat([{"role": "user", "content": "hi"}], **kwargs))

    def test_returns_message_content(self, provider, mock_http):
        # Standard OpenAI-compatible /v1/chat/completions non-streaming shape —
        # nested under choices[0].message, matching the streaming branch's use
        # of choices[0].delta (see TestVLLMChatStreaming below).
        result = self._chat_result(provider, mock_http, {"choices": [{"message": {"content": "reply"}}]})
        assert result == "reply"

    def test_strips_whitespace(self, provider, mock_http):
        result = self._chat_result(provider, mock_http, {"choices": [{"message": {"content": "  reply  "}}]})
        assert result == "reply"

    def test_empty_choices_returns_empty_string(self, provider, mock_http):
        result = self._chat_result(provider, mock_http, {"choices": []})
        assert result == ""


# ---------------------------------------------------------------------------
# models property
# ---------------------------------------------------------------------------

class _AsyncCM:
    """Minimal async context manager wrapping a pre-built response."""

    def __init__(self, resp):
        self.resp = resp

    async def __aenter__(self):
        return self.resp

    async def __aexit__(self, *exc):
        return False


async def _collect(agen):
    return [item async for item in agen]


class TestVLLMGenerateStreaming:

    def test_yields_content_dicts_when_streaming(self, provider, mock_http):
        sse_objs = [{"choices": [{"text": "token1"}]}, {"choices": [{"text": "token2"}]}]
        mock_resp = MagicMock()
        mock_http.post = AsyncMock(return_value=_AsyncCM(mock_resp))

        async def _fake_iter_sse_json(r):
            for obj in sse_objs:
                yield obj

        mock_http.iter_sse_json = _fake_iter_sse_json

        async def _run():
            gen = await provider.generate("prompt", stream=True)
            return await _collect(gen)

        results = asyncio.run(_run())
        assert len(results) > 0


class TestVLLMChatStreaming:

    def test_yields_content_from_choices_delta(self, provider, mock_http):
        sse_objs = [
            {"choices": [{"delta": {"content": "Hi"}}]},
            {"choices": [{"delta": {"content": " there"}}]},
        ]
        mock_resp = MagicMock()
        mock_http.post = AsyncMock(return_value=_AsyncCM(mock_resp))

        async def _fake_iter_sse_json(r):
            for obj in sse_objs:
                yield obj

        mock_http.iter_sse_json = _fake_iter_sse_json

        async def _run():
            gen = await provider.chat([{"role": "user", "content": "hello"}], stream=True)
            return await _collect(gen)

        results = asyncio.run(_run())
        contents = [r.get("content", "") for r in results]
        assert "Hi" in contents or any("Hi" in c for c in contents)


class TestVLLMModels:

    def test_formats_model_list(self, provider, mock_http):
        resp = MagicMock()
        resp.json.return_value = {"models": [{"model": "mistral"}, {"model": "llama3"}]}
        mock_http.get_blocking.return_value = resp
        result = provider.models
        assert len(result["models"]) == 2
