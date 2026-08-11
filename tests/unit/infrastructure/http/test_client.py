from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from hestia.domain.exceptions import ProviderError
from hestia.infrastructure.http.client import HttpClient


def _client(mock_async_client, api_key=None):
    """Build an HttpClient with a mocked httpx.AsyncClient injected."""
    client = HttpClient(base_url="http://localhost", api_key=api_key)
    client._client = mock_async_client
    return client


def _blocking_client(mock_sync_client, api_key=None):
    """Build an HttpClient with a mocked httpx.Client injected."""
    client = HttpClient(base_url="http://localhost", api_key=api_key)
    client._sync_client = mock_sync_client
    return client


def _http_error(status_code, headers=None):
    response = MagicMock(status_code=status_code, headers=headers or {})
    return httpx.HTTPStatusError("error", request=MagicMock(), response=response)


async def _collect(agen):
    return [item async for item in agen]


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
        mock_resp = MagicMock()
        mock_resp.raise_for_status.return_value = None
        async_client = MagicMock()
        async_client.post = AsyncMock(return_value=mock_resp)
        result = asyncio.run(_client(async_client).post("/endpoint", {"key": "val"}))
        assert result is mock_resp

    def test_raises_provider_error_on_timeout(self):
        async_client = MagicMock()
        async_client.post = AsyncMock(side_effect=httpx.TimeoutException("timed out"))
        with pytest.raises(ProviderError, match="timed out"):
            asyncio.run(_client(async_client).post("/endpoint", {}))

    def test_raises_provider_error_on_connection_error(self):
        async_client = MagicMock()
        async_client.post = AsyncMock(side_effect=httpx.ConnectError("boom"))
        with pytest.raises(ProviderError, match="connect"):
            asyncio.run(_client(async_client).post("/endpoint", {}))

    def test_raises_provider_error_on_http_error(self):
        mock_response = MagicMock(status_code=503)
        async_client = MagicMock()
        async_client.post = AsyncMock(
            side_effect=httpx.HTTPStatusError("error", request=MagicMock(), response=mock_response)
        )
        with pytest.raises(ProviderError, match="503"):
            asyncio.run(_client(async_client).post("/endpoint", {}))


# ---------------------------------------------------------------------------
# post_blocking (sync ingestion path — retries on 429/503)
# ---------------------------------------------------------------------------

class TestPostBlocking:

    def test_returns_response(self):
        mock_resp = MagicMock()
        mock_resp.raise_for_status.return_value = None
        sync_client = MagicMock()
        sync_client.post.return_value = mock_resp
        result = _blocking_client(sync_client).post_blocking("/endpoint", {"key": "val"})
        assert result is mock_resp

    def test_raises_provider_error_on_timeout(self):
        sync_client = MagicMock()
        sync_client.post.side_effect = httpx.TimeoutException("timed out")
        with pytest.raises(ProviderError, match="timed out"):
            _blocking_client(sync_client).post_blocking("/endpoint", {})

    def test_raises_provider_error_on_non_retryable_status(self):
        sync_client = MagicMock()
        sync_client.post.side_effect = _http_error(400)
        with pytest.raises(ProviderError, match="400"):
            _blocking_client(sync_client).post_blocking("/endpoint", {})
        assert sync_client.post.call_count == 1

    @patch("hestia.infrastructure.http.client.time.sleep")
    def test_retries_on_429_then_succeeds(self, mock_sleep):
        mock_resp = MagicMock()
        mock_resp.raise_for_status.return_value = None
        sync_client = MagicMock()
        sync_client.post.side_effect = [_http_error(429), _http_error(429), mock_resp]

        result = _blocking_client(sync_client).post_blocking("/endpoint", {})

        assert result is mock_resp
        assert sync_client.post.call_count == 3
        assert mock_sleep.call_count == 2

    @patch("hestia.infrastructure.http.client.time.sleep")
    def test_gives_up_after_max_retries_on_429(self, mock_sleep):
        sync_client = MagicMock()
        sync_client.post.side_effect = _http_error(429)  # every call raises

        with pytest.raises(ProviderError, match="429"):
            _blocking_client(sync_client).post_blocking("/endpoint", {})

        # 1 initial attempt + 3 retries = 4 calls total
        assert sync_client.post.call_count == 4
        assert mock_sleep.call_count == 3

    @patch("hestia.infrastructure.http.client.time.sleep")
    def test_respects_retry_after_header(self, mock_sleep):
        mock_resp = MagicMock()
        mock_resp.raise_for_status.return_value = None
        sync_client = MagicMock()
        sync_client.post.side_effect = [_http_error(429, headers={"Retry-After": "2.5"}), mock_resp]

        _blocking_client(sync_client).post_blocking("/endpoint", {})

        mock_sleep.assert_called_once_with(2.5)


# ---------------------------------------------------------------------------
# get
# ---------------------------------------------------------------------------

class TestGet:

    def test_returns_response(self):
        mock_resp = MagicMock()
        mock_resp.raise_for_status.return_value = None
        async_client = MagicMock()
        async_client.get = AsyncMock(return_value=mock_resp)
        result = asyncio.run(_client(async_client).get("/endpoint"))
        assert result is mock_resp

    def test_raises_provider_error_on_timeout(self):
        async_client = MagicMock()
        async_client.get = AsyncMock(side_effect=httpx.TimeoutException("timed out"))
        with pytest.raises(ProviderError, match="timed out"):
            asyncio.run(_client(async_client).get("/endpoint"))


# ---------------------------------------------------------------------------
# iter_ndjson
# ---------------------------------------------------------------------------

class TestIterNdjson:

    def _resp(self, lines):
        resp = MagicMock()

        async def _aiter_lines():
            for line in lines:
                yield line

        resp.aiter_lines = _aiter_lines
        return resp

    def test_yields_parsed_objects(self):
        resp = self._resp(['{"a": 1}', '{"b": 2}'])
        result = asyncio.run(_collect(HttpClient.iter_ndjson(resp)))
        assert result == [{"a": 1}, {"b": 2}]

    def test_skips_empty_lines(self):
        resp = self._resp(["", '{"ok": true}', ""])
        result = asyncio.run(_collect(HttpClient.iter_ndjson(resp)))
        assert len(result) == 1

    def test_skips_malformed_json(self):
        resp = self._resp(["{bad json}", '{"ok": true}'])
        result = asyncio.run(_collect(HttpClient.iter_ndjson(resp)))
        assert len(result) == 1
        assert result[0] == {"ok": True}


# ---------------------------------------------------------------------------
# iter_sse_json
# ---------------------------------------------------------------------------

class TestIterSseJson:

    def _resp(self, lines):
        resp = MagicMock()

        async def _aiter_lines():
            for line in lines:
                yield line

        resp.aiter_lines = _aiter_lines
        return resp

    def test_yields_parsed_events(self):
        resp = self._resp([
            'data: {"token": "hello"}',
            'data: {"token": "world"}',
        ])
        result = asyncio.run(_collect(HttpClient.iter_sse_json(resp)))
        assert result == [{"token": "hello"}, {"token": "world"}]

    def test_stops_on_done_sentinel(self):
        resp = self._resp([
            'data: {"token": "a"}',
            "data: [DONE]",
            'data: {"token": "b"}',
        ])
        result = asyncio.run(_collect(HttpClient.iter_sse_json(resp)))
        assert len(result) == 1

    def test_skips_non_data_lines(self):
        resp = self._resp([
            "event: message",
            'data: {"ok": true}',
        ])
        result = asyncio.run(_collect(HttpClient.iter_sse_json(resp)))
        assert len(result) == 1
