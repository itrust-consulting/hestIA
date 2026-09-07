from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from hestia.domain.exceptions import ProviderError
from hestia.infrastructure.http.client import HttpClient, _retry_delay, _BASE_DELAY_S


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


def _stream_cm(response=None, enter_exc=None):
    """Build a mock async context manager matching httpx.AsyncClient.stream()'s
    return value -- .stream() itself is a plain (sync) method that returns
    something usable with `async with`."""
    cm = MagicMock()
    if enter_exc is not None:
        cm.__aenter__ = AsyncMock(side_effect=enter_exc)
    else:
        cm.__aenter__ = AsyncMock(return_value=response)
    cm.__aexit__ = AsyncMock(return_value=False)
    return cm


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
# _retry_delay
# ---------------------------------------------------------------------------

class TestRetryDelay:

    def test_invalid_retry_after_header_falls_back_to_exponential_backoff(self):
        response = MagicMock(headers={"Retry-After": "not-a-number"})
        delay = _retry_delay(response, attempt=0)
        # falls back to _BASE_DELAY_S * 2**attempt + jitter, not the header
        assert _BASE_DELAY_S <= delay < _BASE_DELAY_S + 0.5


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

    def test_retries_once_then_succeeds_on_connection_error(self):
        # A pooled keep-alive connection killed by a remote proxy surfaces as
        # ConnectError/ReadError only once httpx tries to reuse it — a fresh
        # connection on the next attempt should succeed without the caller
        # ever seeing an error.
        mock_resp = MagicMock()
        mock_resp.raise_for_status.return_value = None
        async_client = MagicMock()
        async_client.post = AsyncMock(side_effect=[httpx.ConnectError("boom"), mock_resp])
        result = asyncio.run(_client(async_client).post("/endpoint", {}))
        assert result is mock_resp
        assert async_client.post.await_count == 2

    def test_retries_once_then_succeeds_on_read_error(self):
        mock_resp = MagicMock()
        mock_resp.raise_for_status.return_value = None
        async_client = MagicMock()
        async_client.post = AsyncMock(side_effect=[httpx.ReadError("dropped"), mock_resp])
        result = asyncio.run(_client(async_client).post("/endpoint", {}))
        assert result is mock_resp

    def test_raises_provider_error_when_connection_error_persists(self):
        async_client = MagicMock()
        async_client.post = AsyncMock(side_effect=httpx.ConnectError("boom"))
        with pytest.raises(ProviderError, match="connect"):
            asyncio.run(_client(async_client).post("/endpoint", {}))
        assert async_client.post.await_count == 2  # exhausted the one retry, didn't loop forever

    def test_does_not_retry_on_timeout(self):
        async_client = MagicMock()
        async_client.post = AsyncMock(side_effect=httpx.TimeoutException("timed out"))
        with pytest.raises(ProviderError):
            asyncio.run(_client(async_client).post("/endpoint", {}))
        assert async_client.post.await_count == 1

    def test_does_not_retry_on_http_status_error(self):
        mock_response = MagicMock(status_code=503)
        async_client = MagicMock()
        async_client.post = AsyncMock(
            side_effect=httpx.HTTPStatusError("error", request=MagicMock(), response=mock_response)
        )
        with pytest.raises(ProviderError):
            asyncio.run(_client(async_client).post("/endpoint", {}))
        assert async_client.post.await_count == 1

    def test_raises_provider_error_when_read_error_persists(self):
        async_client = MagicMock()
        async_client.post = AsyncMock(side_effect=httpx.ReadError("dropped"))
        with pytest.raises(ProviderError, match="lost"):
            asyncio.run(_client(async_client).post("/endpoint", {}))
        assert async_client.post.await_count == 2  # exhausted the one retry

    def test_stream_true_returns_post_stream_context_manager(self):
        # post(..., stream=True) hands back the _post_stream async context
        # manager directly (not awaited internally) so callers can do
        # `async with (await client.post(..., stream=True)) as r:`.
        fake_response = MagicMock()
        fake_response.raise_for_status.return_value = None
        async_client = MagicMock()
        async_client.stream = MagicMock(return_value=_stream_cm(response=fake_response))
        client = _client(async_client)

        async def _run():
            cm = await client.post("/endpoint", {}, stream=True)
            async with cm as r:
                return r

        result = asyncio.run(_run())
        assert result is fake_response


# ---------------------------------------------------------------------------
# _post_stream (interactive streaming path — retry only before yielding)
# ---------------------------------------------------------------------------

class TestPostStream:

    def test_yields_response_on_success(self):
        fake_response = MagicMock()
        fake_response.raise_for_status.return_value = None
        async_client = MagicMock()
        async_client.stream = MagicMock(return_value=_stream_cm(response=fake_response))

        async def _run():
            async with _client(async_client)._post_stream("/endpoint", {}) as r:
                return r

        result = asyncio.run(_run())
        assert result is fake_response
        assert async_client.stream.call_count == 1

    def test_retries_once_then_succeeds_before_yielding(self):
        fake_response = MagicMock()
        fake_response.raise_for_status.return_value = None
        async_client = MagicMock()
        async_client.stream = MagicMock(side_effect=[
            _stream_cm(enter_exc=httpx.ConnectError("boom")),
            _stream_cm(response=fake_response),
        ])

        async def _run():
            async with _client(async_client)._post_stream("/endpoint", {}) as r:
                return r

        result = asyncio.run(_run())
        assert result is fake_response
        assert async_client.stream.call_count == 2

    def test_raises_provider_error_after_exhausting_retry(self):
        async_client = MagicMock()
        async_client.stream = MagicMock(side_effect=[
            _stream_cm(enter_exc=httpx.ConnectError("boom")),
            _stream_cm(enter_exc=httpx.ConnectError("boom")),
        ])

        async def _run():
            async with _client(async_client)._post_stream("/endpoint", {}):
                pass

        with pytest.raises(ProviderError, match="connect"):
            asyncio.run(_run())
        assert async_client.stream.call_count == 2  # exhausted the one retry, didn't loop forever

    def test_does_not_retry_a_failure_raised_after_yielding(self):
        # Critical regression test: once the caller has a response and may
        # already be consuming chunks from it, a dropped connection must
        # propagate, not silently restart the stream from scratch.
        fake_response = MagicMock()
        fake_response.raise_for_status.return_value = None
        async_client = MagicMock()
        async_client.stream = MagicMock(return_value=_stream_cm(response=fake_response))

        async def _run():
            async with _client(async_client)._post_stream("/endpoint", {}):
                raise httpx.ReadError("mid-stream drop")

        with pytest.raises(ProviderError, match="lost"):
            asyncio.run(_run())
        assert async_client.stream.call_count == 1

    def test_does_not_retry_on_timeout(self):
        async_client = MagicMock()
        async_client.stream = MagicMock(
            return_value=_stream_cm(enter_exc=httpx.TimeoutException("timed out"))
        )

        async def _run():
            async with _client(async_client)._post_stream("/endpoint", {}):
                pass

        with pytest.raises(ProviderError, match="timed out"):
            asyncio.run(_run())
        assert async_client.stream.call_count == 1

    def test_does_not_retry_on_http_status_error(self):
        fake_response = MagicMock()
        fake_response.raise_for_status.side_effect = _http_error(503)
        async_client = MagicMock()
        async_client.stream = MagicMock(return_value=_stream_cm(response=fake_response))

        async def _run():
            async with _client(async_client)._post_stream("/endpoint", {}):
                pass

        with pytest.raises(ProviderError, match="503"):
            asyncio.run(_run())
        assert async_client.stream.call_count == 1


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

    def test_raises_provider_error_on_connection_error(self):
        sync_client = MagicMock()
        sync_client.post.side_effect = httpx.ConnectError("boom")
        with pytest.raises(ProviderError, match="connect"):
            _blocking_client(sync_client).post_blocking("/endpoint", {})

    def test_raises_provider_error_on_read_error(self):
        sync_client = MagicMock()
        sync_client.post.side_effect = httpx.ReadError("dropped")
        with pytest.raises(ProviderError, match="lost"):
            _blocking_client(sync_client).post_blocking("/endpoint", {})


# ---------------------------------------------------------------------------
# get_blocking
# ---------------------------------------------------------------------------

class TestGetBlocking:

    def test_returns_response(self):
        mock_resp = MagicMock()
        mock_resp.raise_for_status.return_value = None
        sync_client = MagicMock()
        sync_client.get.return_value = mock_resp
        result = _blocking_client(sync_client).get_blocking("/endpoint")
        assert result is mock_resp

    def test_raises_provider_error_on_timeout(self):
        sync_client = MagicMock()
        sync_client.get.side_effect = httpx.TimeoutException("timed out")
        with pytest.raises(ProviderError, match="timed out"):
            _blocking_client(sync_client).get_blocking("/endpoint")

    def test_raises_provider_error_on_connection_error(self):
        sync_client = MagicMock()
        sync_client.get.side_effect = httpx.ConnectError("boom")
        with pytest.raises(ProviderError, match="connect"):
            _blocking_client(sync_client).get_blocking("/endpoint")

    def test_raises_provider_error_on_read_error(self):
        sync_client = MagicMock()
        sync_client.get.side_effect = httpx.ReadError("dropped")
        with pytest.raises(ProviderError, match="lost"):
            _blocking_client(sync_client).get_blocking("/endpoint")

    def test_raises_provider_error_on_http_error(self):
        sync_client = MagicMock()
        sync_client.get.side_effect = _http_error(500)
        with pytest.raises(ProviderError, match="500"):
            _blocking_client(sync_client).get_blocking("/endpoint")


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

    def test_retries_once_then_succeeds_on_connection_error(self):
        mock_resp = MagicMock()
        mock_resp.raise_for_status.return_value = None
        async_client = MagicMock()
        async_client.get = AsyncMock(side_effect=[httpx.ConnectError("boom"), mock_resp])
        result = asyncio.run(_client(async_client).get("/endpoint"))
        assert result is mock_resp
        assert async_client.get.await_count == 2

    def test_raises_provider_error_when_read_error_persists(self):
        async_client = MagicMock()
        async_client.get = AsyncMock(side_effect=httpx.ReadError("dropped"))
        with pytest.raises(ProviderError, match="lost"):
            asyncio.run(_client(async_client).get("/endpoint"))
        assert async_client.get.await_count == 2

    def test_raises_provider_error_when_connect_error_persists(self):
        async_client = MagicMock()
        async_client.get = AsyncMock(side_effect=httpx.ConnectError("boom"))
        with pytest.raises(ProviderError, match="connect"):
            asyncio.run(_client(async_client).get("/endpoint"))
        assert async_client.get.await_count == 2

    def test_raises_provider_error_on_http_error(self):
        async_client = MagicMock()
        async_client.get = AsyncMock(side_effect=_http_error(503))
        with pytest.raises(ProviderError, match="503"):
            asyncio.run(_client(async_client).get("/endpoint"))


# ---------------------------------------------------------------------------
# aclose
# ---------------------------------------------------------------------------

class TestAclose:

    def test_closes_both_async_and_sync_clients(self):
        client = HttpClient(base_url="http://localhost")
        mock_async = MagicMock()
        mock_async.aclose = AsyncMock()
        mock_sync = MagicMock()
        client._client = mock_async
        client._sync_client = mock_sync
        asyncio.run(client.aclose())
        mock_async.aclose.assert_awaited_once()
        mock_sync.close.assert_called_once()


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

    def test_skips_malformed_json(self):
        resp = self._resp([
            "data: {bad json}",
            'data: {"ok": true}',
        ])
        result = asyncio.run(_collect(HttpClient.iter_sse_json(resp)))
        assert len(result) == 1
        assert result[0] == {"ok": True}


# ---------------------------------------------------------------------------
# iter_ndjson_sync
# ---------------------------------------------------------------------------

class TestIterNdjsonSync:

    def _resp(self, lines):
        resp = MagicMock()
        resp.iter_lines.return_value = iter(lines)
        return resp

    def test_yields_parsed_objects(self):
        resp = self._resp(['{"a": 1}', '{"b": 2}'])
        result = list(HttpClient.iter_ndjson_sync(resp))
        assert result == [{"a": 1}, {"b": 2}]

    def test_skips_empty_lines(self):
        resp = self._resp(["", '{"ok": true}', ""])
        result = list(HttpClient.iter_ndjson_sync(resp))
        assert len(result) == 1

    def test_skips_malformed_json(self):
        resp = self._resp(["{bad json}", '{"ok": true}'])
        result = list(HttpClient.iter_ndjson_sync(resp))
        assert len(result) == 1
        assert result[0] == {"ok": True}
