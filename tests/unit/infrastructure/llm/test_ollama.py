from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from hestia.infrastructure.http.client import HttpClient
from hestia.infrastructure.llm.ollama import OllamaProvider


# ---------------------------------------------------------------------------
# Fixture: OllamaProvider with mocked HttpClient
# ---------------------------------------------------------------------------

@pytest.fixture
def mock_http():
    return MagicMock()


@pytest.fixture
def provider(mock_http):
    p = OllamaProvider.__new__(OllamaProvider)
    p.http = mock_http
    p.model = "llama3"
    return p


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


# ---------------------------------------------------------------------------
# __init__ (constructor branches)
# ---------------------------------------------------------------------------

class TestOllamaConstructor:

    def test_reuses_http_client_instance_directly(self):
        client = MagicMock(spec=HttpClient)
        provider = OllamaProvider(http=client, model="m")
        assert provider.http is client

    def test_plain_url_string_constructs_http_client(self):
        # Keep construction fast/side-effect-free by patching the underlying
        # httpx clients rather than HttpClient itself (isinstance(x,
        # HttpClient) inside __init__ requires HttpClient to stay the real
        # class).
        with patch("hestia.infrastructure.http.client.httpx.AsyncClient"), \
             patch("hestia.infrastructure.http.client.httpx.Client"):
            provider = OllamaProvider(http="http://ollama", model="m")
            assert isinstance(provider.http, HttpClient)
            assert provider.http.base_url == "http://ollama"


# ---------------------------------------------------------------------------
# embed
# ---------------------------------------------------------------------------

class TestOllamaEmbed:

    def test_normalizes_string_input_to_list(self, provider, mock_http):
        resp = MagicMock()
        resp.json.return_value = {"embeddings": [[0.1, 0.2]]}
        mock_http.post = AsyncMock(return_value=resp)
        asyncio.run(provider.embed("hello"))
        call_payload = mock_http.post.call_args[0][1]
        assert isinstance(call_payload["input"], list)

    def test_returns_embedding_list(self, provider, mock_http):
        resp = MagicMock()
        resp.json.return_value = {"embeddings": [[0.1, 0.2, 0.3]]}
        mock_http.post = AsyncMock(return_value=resp)
        result = asyncio.run(provider.embed(["hello"]))
        assert result == [[0.1, 0.2, 0.3]]

    def test_empty_response_returns_empty(self, provider, mock_http):
        resp = MagicMock()
        resp.json.return_value = {"embeddings": None}
        mock_http.post = AsyncMock(return_value=resp)
        result = asyncio.run(provider.embed(["x"]))
        assert result == []


# ---------------------------------------------------------------------------
# embed_blocking
# ---------------------------------------------------------------------------

class TestOllamaEmbedBlocking:

    def test_normalizes_string_input_to_list(self, provider, mock_http):
        resp = MagicMock()
        resp.json.return_value = {"embeddings": [[0.1, 0.2]]}
        mock_http.post_blocking.return_value = resp
        provider.embed_blocking("hello")
        call_payload = mock_http.post_blocking.call_args[0][1]
        assert isinstance(call_payload["input"], list)

    def test_returns_embedding_list(self, provider, mock_http):
        resp = MagicMock()
        resp.json.return_value = {"embeddings": [[0.1, 0.2, 0.3]]}
        mock_http.post_blocking.return_value = resp
        result = provider.embed_blocking(["hello"])
        assert result == [[0.1, 0.2, 0.3]]

    def test_empty_response_returns_empty(self, provider, mock_http):
        resp = MagicMock()
        resp.json.return_value = {"embeddings": None}
        mock_http.post_blocking.return_value = resp
        result = provider.embed_blocking(["x"])
        assert result == []


# ---------------------------------------------------------------------------
# generate (non-streaming)
# ---------------------------------------------------------------------------

class TestOllamaGenerate:

    def test_returns_stripped_response(self, provider, mock_http):
        resp = MagicMock()
        resp.json.return_value = {"response": "  hello world  "}
        mock_http.post = AsyncMock(return_value=resp)
        result = asyncio.run(provider.generate("prompt"))
        assert result == "hello world"

    def test_uses_default_model(self, provider, mock_http):
        resp = MagicMock()
        resp.json.return_value = {"response": "ok"}
        mock_http.post = AsyncMock(return_value=resp)
        asyncio.run(provider.generate("prompt"))
        payload = mock_http.post.call_args[0][1]
        assert payload["model"] == "llama3"

    def test_explicit_model_overrides(self, provider, mock_http):
        resp = MagicMock()
        resp.json.return_value = {"response": "ok"}
        mock_http.post = AsyncMock(return_value=resp)
        asyncio.run(provider.generate("prompt", model="custom-model"))
        payload = mock_http.post.call_args[0][1]
        assert payload["model"] == "custom-model"


# ---------------------------------------------------------------------------
# chat (non-streaming)
# ---------------------------------------------------------------------------

class TestOllamaChat:

    def test_returns_message_content(self, provider, mock_http):
        resp = MagicMock()
        resp.json.return_value = {"message": {"content": "  reply  "}}
        mock_http.post = AsyncMock(return_value=resp)
        result = asyncio.run(provider.chat([{"role": "user", "content": "hi"}]))
        assert result == "reply"


# ---------------------------------------------------------------------------
# chat (streaming)
# ---------------------------------------------------------------------------

class TestOllamaChatStreaming:

    def test_yields_content_from_message_delta(self, provider, mock_http):
        ndjson_objs = [
            {"message": {"content": "Hi"}, "done": False},
            {"message": {"content": " there"}, "done": True},
        ]
        mock_resp = MagicMock()
        mock_http.post = AsyncMock(return_value=_AsyncCM(mock_resp))

        async def _fake_iter_ndjson(r):
            for obj in ndjson_objs:
                yield obj

        mock_http.iter_ndjson = _fake_iter_ndjson

        async def _run():
            gen = await provider.chat([{"role": "user", "content": "hi"}], stream=True)
            return await _collect(gen)

        results = asyncio.run(_run())
        contents = [r.get("content", "") for r in results]
        assert "Hi" in contents


# ---------------------------------------------------------------------------
# _stream -- chunks with no content/thinking must not be yielded, and the
# loop must keep going until `done` even after a chunk was skipped.
# ---------------------------------------------------------------------------

class TestOllamaStreamSkipsEmptyChunks:

    def test_skips_chunk_with_no_content_before_done(self, provider, mock_http):
        ndjson_objs = [
            {"message": {}, "done": False},  # no content, no thinking -> skipped
            {"message": {"content": "final"}, "done": True},
        ]
        mock_resp = MagicMock()
        mock_http.post = AsyncMock(return_value=_AsyncCM(mock_resp))

        async def _fake_iter_ndjson(r):
            for obj in ndjson_objs:
                yield obj

        mock_http.iter_ndjson = _fake_iter_ndjson

        async def _run():
            gen = await provider.chat([{"role": "user", "content": "hi"}], stream=True)
            return await _collect(gen)

        results = asyncio.run(_run())
        assert len(results) == 1
        assert results[0]["content"] == "final"

    def test_loop_ends_naturally_when_stream_never_sends_done(self, provider, mock_http):
        # If the upstream generator is exhausted before any object has
        # done=True, the async-for must end on its own (no break reached)
        # rather than hanging or erroring.
        ndjson_objs = [
            {"message": {"content": "a"}, "done": False},
            {"message": {"content": "b"}, "done": False},
        ]
        mock_resp = MagicMock()
        mock_http.post = AsyncMock(return_value=_AsyncCM(mock_resp))

        async def _fake_iter_ndjson(r):
            for obj in ndjson_objs:
                yield obj

        mock_http.iter_ndjson = _fake_iter_ndjson

        async def _run():
            gen = await provider.chat([{"role": "user", "content": "hi"}], stream=True)
            return await _collect(gen)

        results = asyncio.run(_run())
        assert [r["content"] for r in results] == ["a", "b"]


# ---------------------------------------------------------------------------
# generate (streaming)
# ---------------------------------------------------------------------------

class TestOllamaGenerateStreaming:

    def test_yields_content_dicts_when_streaming(self, provider, mock_http):
        ndjson_objs = [
            {"response": "Hello", "done": False},
            {"response": " world", "done": True},
        ]
        mock_resp = MagicMock()

        # _stream uses (await http.post(..., stream=True)) as an async context manager
        mock_http.post = AsyncMock(return_value=_AsyncCM(mock_resp))

        async def _fake_iter_ndjson(r):
            for obj in ndjson_objs:
                yield obj

        mock_http.iter_ndjson = _fake_iter_ndjson

        async def _run():
            gen = await provider.generate("prompt", stream=True)
            return await _collect(gen)

        results = asyncio.run(_run())
        assert len(results) > 0
        assert any(r.get("content") for r in results)


# ---------------------------------------------------------------------------
# models property
# ---------------------------------------------------------------------------

class TestOllamaModels:

    def test_formats_model_list(self, provider, mock_http):
        resp = MagicMock()
        resp.json.return_value = {"models": [{"model": "llama3"}, {"model": "mistral"}]}
        mock_http.get_blocking.return_value = resp
        result = provider.models
        assert len(result["models"]) == 2
        assert result["models"][0]["model"] == "llama3"


# ---------------------------------------------------------------------------
# aclose
# ---------------------------------------------------------------------------

class TestOllamaAclose:

    def test_closes_underlying_http_client(self, provider, mock_http):
        mock_http.aclose = AsyncMock()
        asyncio.run(provider.aclose())
        mock_http.aclose.assert_awaited_once()
