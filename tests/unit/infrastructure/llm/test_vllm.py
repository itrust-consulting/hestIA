from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from hestia.infrastructure.http.client import HttpClient
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
# __init__ (constructor branches -- avoid constructing real HttpClients,
# which are slow to build in this environment; patch the HttpClient class
# referenced inside vllm.py instead of calling the real one)
# ---------------------------------------------------------------------------

class TestVLLMConstructor:
    # _hc() does `isinstance(x, HttpClient)`, so HttpClient itself must stay
    # the real class (patching it with a MagicMock breaks isinstance). To
    # keep construction fast, patch the underlying httpx.AsyncClient/Client
    # at the http.client module level instead -- the real HttpClient.__init__
    # then runs, but never opens a real connection pool.

    def test_chat_only_reuses_same_client_for_embed_and_rerank(self):
        with patch("hestia.infrastructure.http.client.httpx.AsyncClient"), \
             patch("hestia.infrastructure.http.client.httpx.Client"):
            provider = vLLMProvider(chat="http://chat")
            assert isinstance(provider.http_chat, HttpClient)
            assert provider.http_embed is provider.http_chat
            assert provider.http_rrk is provider.http_chat
            assert provider.http_chat.base_url == "http://chat"

    def test_separate_http_client_instances_are_used_directly(self):
        # When chat/embed/rerank are already HttpClient instances, _hc()
        # must return them unchanged rather than wrapping/reconstructing.
        chat_client = MagicMock(spec=HttpClient)
        embed_client = MagicMock(spec=HttpClient)
        rerank_client = MagicMock(spec=HttpClient)
        provider = vLLMProvider(chat=chat_client, embed=embed_client, rerank=rerank_client)
        assert provider.http_chat is chat_client
        assert provider.http_embed is embed_client
        assert provider.http_rrk is rerank_client

    def test_plain_url_strings_construct_separate_http_clients(self):
        with patch("hestia.infrastructure.http.client.httpx.AsyncClient"), \
             patch("hestia.infrastructure.http.client.httpx.Client"):
            provider = vLLMProvider(
                chat="http://chat", embed="http://embed", rerank="http://rerank", api_key="key123",
            )
            assert provider.http_chat is not provider.http_embed
            assert provider.http_embed is not provider.http_rrk
            assert provider.http_chat.base_url == "http://chat"
            assert provider.http_embed.base_url == "http://embed"
            assert provider.http_rrk.base_url == "http://rerank"
            assert provider.http_chat.api_key == "key123"


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
# embed_blocking
# ---------------------------------------------------------------------------

class TestVLLMEmbedBlocking:

    def test_returns_embeddings(self, provider, mock_http):
        resp = MagicMock()
        resp.json.return_value = {"data": [{"embedding": [0.1, 0.2]}]}
        mock_http.post_blocking.return_value = resp
        result = provider.embed_blocking(["hello"])
        assert result == [[0.1, 0.2]]

    def test_normalizes_string_to_list(self, provider, mock_http):
        resp = MagicMock()
        resp.json.return_value = {"data": []}
        mock_http.post_blocking.return_value = resp
        provider.embed_blocking("hello")
        payload = mock_http.post_blocking.call_args[0][1]
        assert isinstance(payload["input"], list)


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
        # Regression test: vLLM's /v1/models is OpenAI-compatible
        # ({"data": [{"id": ...}]}), not Ollama's native {"models": [...]}
        # shape -- this used to read the wrong key and silently returned an
        # empty list against a real vLLM backend.
        resp = MagicMock()
        resp.json.return_value = {
            "object": "list",
            "data": [{"id": "mistral", "object": "model"}, {"id": "llama3", "object": "model"}],
        }
        mock_http.get_blocking.return_value = resp
        result = provider.models
        assert len(result["models"]) == 2
        assert {m["model"] for m in result["models"]} == {"mistral", "llama3"}

    def test_missing_data_key_returns_empty_list(self, provider, mock_http):
        resp = MagicMock()
        resp.json.return_value = {"object": "list", "data": []}
        mock_http.get_blocking.return_value = resp
        result = provider.models
        assert result["models"] == []


# ---------------------------------------------------------------------------
# _stream -- chunks with no content and no thinking must not be yielded
# ---------------------------------------------------------------------------

class TestVLLMStreamSkipsEmptyChunks:

    def test_skips_chunk_with_no_content_or_thinking(self, provider, mock_http):
        sse_objs = [
            {"choices": [{"delta": {}}]},  # neither content nor reasoning -> skipped
            {"choices": [{"delta": {"content": "Hi"}}]},
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
        assert len(results) == 1
        assert results[0]["content"] == "Hi"


# ---------------------------------------------------------------------------
# aclose -- dedup by id() so a shared HttpClient isn't closed twice
# ---------------------------------------------------------------------------

class TestVLLMAclose:

    def test_closes_each_unique_client_once_when_embed_defaults_to_chat(self):
        shared = MagicMock()
        shared.aclose = AsyncMock()
        distinct = MagicMock()
        distinct.aclose = AsyncMock()
        provider = vLLMProvider.__new__(vLLMProvider)
        provider.http_chat = shared
        provider.http_embed = shared
        provider.http_rrk = distinct

        asyncio.run(provider.aclose())

        shared.aclose.assert_awaited_once()
        distinct.aclose.assert_awaited_once()

    def test_closes_all_three_when_all_distinct(self):
        a, b, c = MagicMock(), MagicMock(), MagicMock()
        a.aclose = AsyncMock()
        b.aclose = AsyncMock()
        c.aclose = AsyncMock()
        provider = vLLMProvider.__new__(vLLMProvider)
        provider.http_chat = a
        provider.http_embed = b
        provider.http_rrk = c

        asyncio.run(provider.aclose())

        a.aclose.assert_awaited_once()
        b.aclose.assert_awaited_once()
        c.aclose.assert_awaited_once()
