from __future__ import annotations

import json
from unittest.mock import MagicMock

import pytest
import requests

from hestia.domain.exceptions import ProviderError
from hestia.infrastructure.http.client import HttpClient


def _client(mock_session, api_key=None):
    """Build an HttpClient with a pre-injected mock session."""
    return HttpClient(base_url="http://localhost", api_key=api_key, session=mock_session)


# ---------------------------------------------------------------------------
# _auth_headers
# ---------------------------------------------------------------------------

class TestAuthHeaders:

    def test_empty_when_no_api_key(self):
        client = HttpClient(base_url="http://localhost")
        assert client._auth_headers() == {}

    def test_bearer_header_when_api_key_set(self):
        client = HttpClient(base_url="http://localhost", api_key="my-key")
        h = client._auth_headers()
        assert h["Authorization"] == "Bearer my-key"

    def test_extra_headers_merged(self):
        client = HttpClient(base_url="http://localhost", api_key="k")
        h = client._auth_headers({"X-Custom": "val"})
        assert h["X-Custom"] == "val"
        assert "Authorization" in h


# ---------------------------------------------------------------------------
# post (non-streaming)
# ---------------------------------------------------------------------------

class TestPost:

    def test_returns_response(self):
        session = MagicMock()
        mock_resp = MagicMock()
        mock_resp.raise_for_status.return_value = None
        session.post.return_value = mock_resp
        result = _client(session).post("/endpoint", {"key": "val"})
        assert result is mock_resp

    def test_raises_provider_error_on_timeout(self):
        session = MagicMock()
        session.post.side_effect = requests.exceptions.Timeout()
        with pytest.raises(ProviderError, match="timed out"):
            _client(session).post("/endpoint", {})

    def test_raises_provider_error_on_connection_error(self):
        session = MagicMock()
        session.post.side_effect = requests.exceptions.ConnectionError()
        with pytest.raises(ProviderError, match="connect"):
            _client(session).post("/endpoint", {})

    def test_raises_provider_error_on_http_error(self):
        session = MagicMock()
        mock_exc = requests.exceptions.HTTPError()
        mock_exc.response = MagicMock(status_code=503)
        session.post.side_effect = mock_exc
        with pytest.raises(ProviderError, match="503"):
            _client(session).post("/endpoint", {})


# ---------------------------------------------------------------------------
# get
# ---------------------------------------------------------------------------

class TestGet:

    def test_returns_response(self):
        session = MagicMock()
        mock_resp = MagicMock()
        mock_resp.raise_for_status.return_value = None
        session.get.return_value = mock_resp
        result = _client(session).get("/endpoint")
        assert result is mock_resp

    def test_raises_provider_error_on_timeout(self):
        session = MagicMock()
        session.get.side_effect = requests.exceptions.Timeout()
        with pytest.raises(ProviderError, match="timed out"):
            _client(session).get("/endpoint")


# ---------------------------------------------------------------------------
# iter_ndjson
# ---------------------------------------------------------------------------

class TestIterNdjson:

    def test_yields_parsed_objects(self):
        resp = MagicMock()
        resp.iter_lines.return_value = [
            '{"a": 1}',
            '{"b": 2}',
        ]
        result = list(HttpClient.iter_ndjson(resp))
        assert result == [{"a": 1}, {"b": 2}]

    def test_skips_empty_lines(self):
        resp = MagicMock()
        resp.iter_lines.return_value = ["", '{"ok": true}', ""]
        result = list(HttpClient.iter_ndjson(resp))
        assert len(result) == 1

    def test_skips_malformed_json(self):
        resp = MagicMock()
        resp.iter_lines.return_value = ["{bad json}", '{"ok": true}']
        result = list(HttpClient.iter_ndjson(resp))
        assert len(result) == 1
        assert result[0] == {"ok": True}


# ---------------------------------------------------------------------------
# iter_sse_json
# ---------------------------------------------------------------------------

class TestIterSseJson:

    def test_yields_parsed_events(self):
        resp = MagicMock()
        resp.iter_lines.return_value = [
            'data: {"token": "hello"}',
            'data: {"token": "world"}',
        ]
        result = list(HttpClient.iter_sse_json(resp))
        assert result == [{"token": "hello"}, {"token": "world"}]

    def test_stops_on_done_sentinel(self):
        resp = MagicMock()
        resp.iter_lines.return_value = [
            'data: {"token": "a"}',
            "data: [DONE]",
            'data: {"token": "b"}',
        ]
        result = list(HttpClient.iter_sse_json(resp))
        assert len(result) == 1

    def test_skips_non_data_lines(self):
        resp = MagicMock()
        resp.iter_lines.return_value = [
            "event: message",
            'data: {"ok": true}',
        ]
        result = list(HttpClient.iter_sse_json(resp))
        assert len(result) == 1
