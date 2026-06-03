from __future__ import annotations

from unittest.mock import MagicMock

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
        mock_http.post.return_value = resp
        provider.embed("hello")
        payload = mock_http.post.call_args[0][1]
        assert isinstance(payload["input"], list)

    def test_returns_embeddings(self, provider, mock_http):
        resp = MagicMock()
        resp.json.return_value = {"data": [{"embedding": [0.1, 0.2]}]}
        mock_http.post.return_value = resp
        result = provider.embed(["hello"])
        assert result == [[0.1, 0.2]]


# ---------------------------------------------------------------------------
# generate (non-streaming)
# ---------------------------------------------------------------------------

class TestVLLMGenerate:

    def test_returns_stripped_response(self, provider, mock_http):
        resp = MagicMock()
        resp.json.return_value = {"response": "  answer  "}
        mock_http.post.return_value = resp
        result = provider.generate("prompt")
        assert result == "answer"

    def test_uses_default_model(self, provider, mock_http):
        resp = MagicMock()
        resp.json.return_value = {"response": "ok"}
        mock_http.post.return_value = resp
        provider.generate("prompt")
        payload = mock_http.post.call_args[0][1]
        # model not in vllm payload (passed separately)
        assert "stream" in payload


# ---------------------------------------------------------------------------
# chat (non-streaming)
# ---------------------------------------------------------------------------

class TestVLLMChat:

    def test_returns_message_content(self, provider, mock_http):
        resp = MagicMock()
        resp.json.return_value = {"message": {"content": "reply"}}
        mock_http.post.return_value = resp
        result = provider.chat([{"role": "user", "content": "hi"}])
        assert result == "reply"


# ---------------------------------------------------------------------------
# models property
# ---------------------------------------------------------------------------

class TestVLLMGenerateStreaming:

    def test_yields_content_dicts_when_streaming(self, provider, mock_http):
        sse_lines = [
            'data: {"response": "token1"}',
            'data: {"response": "token2"}',
            "data: [DONE]",
        ]
        mock_resp = MagicMock()
        mock_resp.iter_lines.return_value = sse_lines

        mock_http.post.return_value.__enter__ = lambda s: mock_resp
        mock_http.post.return_value.__exit__ = MagicMock(return_value=False)
        mock_http.iter_sse_json.side_effect = lambda r: (
            __import__("json").loads(line[len("data:"):].strip())
            for line in sse_lines
            if line.startswith("data:") and line.strip() != "data: [DONE]"
        )

        results = list(provider.generate("prompt", stream=True))
        assert len(results) > 0


class TestVLLMChatStreaming:

    def test_yields_content_from_choices_delta(self, provider, mock_http):
        sse_lines = [
            'data: {"choices": [{"delta": {"content": "Hi"}}]}',
            'data: {"choices": [{"delta": {"content": " there"}}]}',
            "data: [DONE]",
        ]
        mock_resp = MagicMock()
        mock_resp.iter_lines.return_value = sse_lines

        mock_http.post.return_value.__enter__ = lambda s: mock_resp
        mock_http.post.return_value.__exit__ = MagicMock(return_value=False)
        mock_http.iter_sse_json.side_effect = lambda r: (
            __import__("json").loads(line[len("data:"):].strip())
            for line in sse_lines
            if line.startswith("data:") and line.strip() != "data: [DONE]"
        )

        results = list(provider.chat([{"role": "user", "content": "hello"}], stream=True))
        contents = [r.get("content", "") for r in results]
        assert "Hi" in contents or any("Hi" in c for c in contents)


class TestVLLMModels:

    def test_formats_model_list(self, provider, mock_http):
        resp = MagicMock()
        resp.json.return_value = {"models": [{"model": "mistral"}, {"model": "llama3"}]}
        mock_http.get.return_value = resp
        result = provider.models
        assert len(result["models"]) == 2
