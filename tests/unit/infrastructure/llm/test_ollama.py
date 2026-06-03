from __future__ import annotations

from unittest.mock import MagicMock

import pytest

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


# ---------------------------------------------------------------------------
# embed
# ---------------------------------------------------------------------------

class TestOllamaEmbed:

    def test_normalizes_string_input_to_list(self, provider, mock_http):
        resp = MagicMock()
        resp.json.return_value = {"embeddings": [[0.1, 0.2]]}
        mock_http.post.return_value = resp
        provider.embed("hello")
        call_payload = mock_http.post.call_args[0][1]
        assert isinstance(call_payload["input"], list)

    def test_returns_embedding_list(self, provider, mock_http):
        resp = MagicMock()
        resp.json.return_value = {"embeddings": [[0.1, 0.2, 0.3]]}
        mock_http.post.return_value = resp
        result = provider.embed(["hello"])
        assert result == [[0.1, 0.2, 0.3]]

    def test_empty_response_returns_empty(self, provider, mock_http):
        resp = MagicMock()
        resp.json.return_value = {"embeddings": None}
        mock_http.post.return_value = resp
        result = provider.embed(["x"])
        assert result == []


# ---------------------------------------------------------------------------
# generate (non-streaming)
# ---------------------------------------------------------------------------

class TestOllamaGenerate:

    def test_returns_stripped_response(self, provider, mock_http):
        resp = MagicMock()
        resp.json.return_value = {"response": "  hello world  "}
        mock_http.post.return_value = resp
        result = provider.generate("prompt")
        assert result == "hello world"

    def test_uses_default_model(self, provider, mock_http):
        resp = MagicMock()
        resp.json.return_value = {"response": "ok"}
        mock_http.post.return_value = resp
        provider.generate("prompt")
        payload = mock_http.post.call_args[0][1]
        assert payload["model"] == "llama3"

    def test_explicit_model_overrides(self, provider, mock_http):
        resp = MagicMock()
        resp.json.return_value = {"response": "ok"}
        mock_http.post.return_value = resp
        provider.generate("prompt", model="custom-model")
        payload = mock_http.post.call_args[0][1]
        assert payload["model"] == "custom-model"


# ---------------------------------------------------------------------------
# chat (non-streaming)
# ---------------------------------------------------------------------------

class TestOllamaChat:

    def test_returns_message_content(self, provider, mock_http):
        resp = MagicMock()
        resp.json.return_value = {"message": {"content": "  reply  "}}
        mock_http.post.return_value = resp
        result = provider.chat([{"role": "user", "content": "hi"}])
        assert result == "reply"


# ---------------------------------------------------------------------------
# models property
# ---------------------------------------------------------------------------

class TestOllamaGenerateStreaming:

    def test_yields_content_dicts_when_streaming(self, provider, mock_http):
        ndjson_lines = [
            '{"response": "Hello", "done": false}',
            '{"response": " world", "done": true}',
        ]
        mock_resp = MagicMock()
        mock_resp.iter_lines.return_value = ndjson_lines

        # _stream uses http.post as a context manager
        mock_http.post.return_value.__enter__ = lambda s: mock_resp
        mock_http.post.return_value.__exit__ = MagicMock(return_value=False)
        mock_http.iter_ndjson.side_effect = lambda r: (
            __import__("json").loads(line) for line in ndjson_lines
        )

        results = list(provider.generate("prompt", stream=True))
        assert len(results) > 0
        assert any(r.get("content") for r in results)


class TestOllamaModels:

    def test_formats_model_list(self, provider, mock_http):
        resp = MagicMock()
        resp.json.return_value = {"models": [{"model": "llama3"}, {"model": "mistral"}]}
        mock_http.get.return_value = resp
        result = provider.models
        assert len(result["models"]) == 2
        assert result["models"][0]["model"] == "llama3"
