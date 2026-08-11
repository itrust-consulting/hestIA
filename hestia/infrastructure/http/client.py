from __future__ import annotations

import json
import logging
import random
import time
from contextlib import asynccontextmanager
from typing import Any, AsyncIterator, Dict, Iterator, Optional, Tuple

import httpx

from hestia.domain.exceptions import ProviderError

_log = logging.getLogger("hestia.system")

# Status codes worth retrying on the blocking (ingestion) path: transient
# provider-side overload/rate-limiting, not client errors like 400/401/404.
_RETRYABLE_STATUS_CODES = {429, 503}
_MAX_RETRIES = 3
_BASE_DELAY_S = 1.0


def _retry_delay(response: httpx.Response, attempt: int) -> float:
    retry_after = response.headers.get("Retry-After")
    if retry_after:
        try:
            return float(retry_after)
        except ValueError:
            pass
    return _BASE_DELAY_S * (2 ** attempt) + random.uniform(0, 0.5)


class HttpClient:

    def __init__(
        self,
        base_url: str,
        timeout: Tuple[float, float] = (10.0, 800.0),
        api_key: Optional[str] = None,
    ):
        self.base_url = base_url
        self.timeout = timeout
        self.api_key = api_key
        _t = httpx.Timeout(timeout[1], connect=timeout[0])
        self._client = httpx.AsyncClient(timeout=_t)
        self._sync_client = httpx.Client(timeout=_t)

    def _auth_headers(self, extra: Optional[Dict[str, str]] = None) -> Dict[str, str]:
        h: Dict[str, str] = {}
        if self.api_key:
            h["Authorization"] = f"Bearer {self.api_key}"
        if extra:
            h.update(extra)
        return h or {}

    # ------------------------------------------------------------------
    # Async interface (inference path)
    # ------------------------------------------------------------------

    @asynccontextmanager
    async def _post_stream(self, endpoint: str, payload: Dict[str, Any], headers: Optional[Dict[str, str]] = None):
        url = self.base_url + endpoint
        try:
            async with self._client.stream(
                "POST", url, json=payload, headers=self._auth_headers(headers),
            ) as r:
                r.raise_for_status()
                yield r
        except httpx.TimeoutException:
            _log.warning("http_timeout", extra={"url": url, "method": "POST"})
            raise ProviderError(f"Request timed out: POST {endpoint}")
        except httpx.ConnectError:
            _log.warning("http_connection_error", extra={"url": url, "method": "POST"})
            raise ProviderError(f"Could not connect to provider: {self.base_url}")
        except httpx.ReadError:
            # a pooled keep-alive connection can be closed by the peer at any
            # time without notice -- httpx only discovers this when it tries
            # to reuse that connection for the next request
            _log.warning("http_read_error", extra={"url": url, "method": "POST"})
            raise ProviderError(f"Connection to provider was lost: POST {endpoint}")
        except httpx.HTTPStatusError as e:
            _log.warning("http_error_response", extra={"url": url, "method": "POST", "status_code": e.response.status_code})
            raise ProviderError(f"Provider returned {e.response.status_code}: POST {endpoint}")

    async def post(self, endpoint: str, payload: Dict[str, Any], headers: Optional[Dict[str, str]] = None, stream: bool = False):
        if stream:
            return self._post_stream(endpoint, payload, headers)
        url = self.base_url + endpoint
        try:
            r = await self._client.post(url, json=payload, headers=self._auth_headers(headers))
            r.raise_for_status()
            return r
        except httpx.TimeoutException:
            _log.warning("http_timeout", extra={"url": url, "method": "POST"})
            raise ProviderError(f"Request timed out: POST {endpoint}")
        except httpx.ConnectError:
            _log.warning("http_connection_error", extra={"url": url, "method": "POST"})
            raise ProviderError(f"Could not connect to provider: {self.base_url}")
        except httpx.ReadError:
            _log.warning("http_read_error", extra={"url": url, "method": "POST"})
            raise ProviderError(f"Connection to provider was lost: POST {endpoint}")
        except httpx.HTTPStatusError as e:
            _log.warning("http_error_response", extra={"url": url, "method": "POST", "status_code": e.response.status_code})
            raise ProviderError(f"Provider returned {e.response.status_code}: POST {endpoint}")

    async def get(self, endpoint: str):
        url = self.base_url + endpoint
        try:
            r = await self._client.get(url, headers=self._auth_headers())
            r.raise_for_status()
            return r
        except httpx.TimeoutException:
            _log.warning("http_timeout", extra={"url": url, "method": "GET"})
            raise ProviderError(f"Request timed out: GET {endpoint}")
        except httpx.ConnectError:
            _log.warning("http_connection_error", extra={"url": url, "method": "GET"})
            raise ProviderError(f"Could not connect to provider: {self.base_url}")
        except httpx.ReadError:
            _log.warning("http_read_error", extra={"url": url, "method": "GET"})
            raise ProviderError(f"Connection to provider was lost: GET {endpoint}")
        except httpx.HTTPStatusError as e:
            _log.warning("http_error_response", extra={"url": url, "method": "GET", "status_code": e.response.status_code})
            raise ProviderError(f"Provider returned {e.response.status_code}: GET {endpoint}")

    @staticmethod
    async def iter_sse_json(r: httpx.Response) -> AsyncIterator[Dict[str, Any]]:
        async for raw_line in r.aiter_lines():
            if not raw_line or not raw_line.startswith("data:"):
                continue
            data = raw_line[5:].strip()
            if data == "[DONE]":
                break
            try:
                yield json.loads(data)
            except json.JSONDecodeError as e:
                _log.warning("sse_parse_error", extra={"error": str(e), "data": data[:120]})

    @staticmethod
    async def iter_ndjson(r: httpx.Response) -> AsyncIterator[Dict[str, Any]]:
        async for line in r.aiter_lines():
            if not line:
                continue
            try:
                yield json.loads(line)
            except json.JSONDecodeError as e:
                _log.warning("ndjson_parse_error", extra={"error": str(e), "line": line[:120]})

    async def aclose(self) -> None:
        await self._client.aclose()
        self._sync_client.close()

    # ------------------------------------------------------------------
    # Sync interface (ingestion / batch path)
    # ------------------------------------------------------------------

    def get_blocking(self, endpoint: str):
        url = self.base_url + endpoint
        try:
            r = self._sync_client.get(url, headers=self._auth_headers())
            r.raise_for_status()
            return r
        except httpx.TimeoutException:
            _log.warning("http_timeout", extra={"url": url, "method": "GET"})
            raise ProviderError(f"Request timed out: GET {endpoint}")
        except httpx.ConnectError:
            _log.warning("http_connection_error", extra={"url": url, "method": "GET"})
            raise ProviderError(f"Could not connect to provider: {self.base_url}")
        except httpx.ReadError:
            _log.warning("http_read_error", extra={"url": url, "method": "GET"})
            raise ProviderError(f"Connection to provider was lost: GET {endpoint}")
        except httpx.HTTPStatusError as e:
            _log.warning("http_error_response", extra={"url": url, "method": "GET", "status_code": e.response.status_code})
            raise ProviderError(f"Provider returned {e.response.status_code}: GET {endpoint}")

    def post_blocking(self, endpoint: str, payload: Dict[str, Any], headers: Optional[Dict[str, str]] = None):
        url = self.base_url + endpoint
        attempt = 0
        while True:
            try:
                r = self._sync_client.post(url, json=payload, headers=self._auth_headers(headers))
                r.raise_for_status()
                return r
            except httpx.TimeoutException:
                _log.warning("http_timeout", extra={"url": url, "method": "POST"})
                raise ProviderError(f"Request timed out: POST {endpoint}")
            except httpx.ConnectError:
                _log.warning("http_connection_error", extra={"url": url, "method": "POST"})
                raise ProviderError(f"Could not connect to provider: {self.base_url}")
            except httpx.ReadError:
                _log.warning("http_read_error", extra={"url": url, "method": "POST"})
                raise ProviderError(f"Connection to provider was lost: POST {endpoint}")
            except httpx.HTTPStatusError as e:
                status = e.response.status_code
                if status in _RETRYABLE_STATUS_CODES and attempt < _MAX_RETRIES:
                    delay = _retry_delay(e.response, attempt)
                    attempt += 1
                    _log.warning("http_retrying_after_status", extra={
                        "url": url, "method": "POST", "status_code": status,
                        "attempt": attempt, "delay_s": delay,
                    })
                    time.sleep(delay)
                    continue
                _log.warning("http_error_response", extra={"url": url, "method": "POST", "status_code": status})
                raise ProviderError(f"Provider returned {status}: POST {endpoint}")

    @staticmethod
    def iter_ndjson_sync(r: httpx.Response) -> Iterator[Dict[str, Any]]:
        for line in r.iter_lines():
            if not line:
                continue
            try:
                yield json.loads(line)
            except json.JSONDecodeError as e:
                _log.warning("ndjson_parse_error", extra={"error": str(e), "line": line[:120]})
