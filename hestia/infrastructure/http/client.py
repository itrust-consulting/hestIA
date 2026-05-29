from __future__ import annotations

import json
import logging
from contextlib import contextmanager
from dataclasses import dataclass, field
from typing import Any, Dict, Iterator, Optional, Tuple

import requests

from hestia.domain.exceptions import ProviderError

_log = logging.getLogger("hestia.system")


@dataclass(frozen=True)
class HttpClient:
    base_url: str
    timeout: Tuple[float, float] = (10.0, 800.0)
    api_key: Optional[str] = None
    session: requests.Session = field(default_factory=requests.Session, repr=False, compare=False)

    @contextmanager
    def _post_stream(self, endpoint: str, payload: Dict[str, Any], headers: Optional[Dict[str, str]] = None):
        url = self.base_url + endpoint
        try:
            r = self.session.post(url, json=payload, headers=headers, timeout=self.timeout, stream=True)
            r.raise_for_status()
        except requests.exceptions.Timeout:
            _log.warning("http_timeout", extra={"url": url, "method": "POST"})
            raise ProviderError(f"Request timed out: POST {endpoint}")
        except requests.exceptions.ConnectionError:
            _log.warning("http_connection_error", extra={"url": url, "method": "POST"})
            raise ProviderError(f"Could not connect to provider: {self.base_url}")
        except requests.exceptions.HTTPError as e:
            status = e.response.status_code if e.response is not None else "?"
            _log.warning("http_error_response", extra={"url": url, "method": "POST", "status_code": status})
            raise ProviderError(f"Provider returned {status}: POST {endpoint}")
        try:
            yield r
        finally:
            r.close()

    def post(self, endpoint: str, payload: Dict[str, Any], headers: Optional[Dict[str, str]] = None, stream: bool = False):
        if stream:
            return self._post_stream(endpoint, payload, headers)
        url = self.base_url + endpoint
        try:
            r = self.session.post(url, json=payload, headers=headers, timeout=self.timeout)
            r.raise_for_status()
            return r
        except requests.exceptions.Timeout:
            _log.warning("http_timeout", extra={"url": url, "method": "POST"})
            raise ProviderError(f"Request timed out: POST {endpoint}")
        except requests.exceptions.ConnectionError:
            _log.warning("http_connection_error", extra={"url": url, "method": "POST"})
            raise ProviderError(f"Could not connect to provider: {self.base_url}")
        except requests.exceptions.HTTPError as e:
            status = e.response.status_code if e.response is not None else "?"
            _log.warning("http_error_response", extra={"url": url, "method": "POST", "status_code": status})
            raise ProviderError(f"Provider returned {status}: POST {endpoint}")

    def get(self, endpoint: str):
        url = self.base_url + endpoint
        try:
            r = self.session.get(url, timeout=self.timeout)
            r.raise_for_status()
            return r
        except requests.exceptions.Timeout:
            _log.warning("http_timeout", extra={"url": url, "method": "GET"})
            raise ProviderError(f"Request timed out: GET {endpoint}")
        except requests.exceptions.ConnectionError:
            _log.warning("http_connection_error", extra={"url": url, "method": "GET"})
            raise ProviderError(f"Could not connect to provider: {self.base_url}")
        except requests.exceptions.HTTPError as e:
            status = e.response.status_code if e.response is not None else "?"
            _log.warning("http_error_response", extra={"url": url, "method": "GET", "status_code": status})
            raise ProviderError(f"Provider returned {status}: GET {endpoint}")

    @staticmethod
    def iter_ndjson(r: requests.Response) -> Iterator[Dict[str, Any]]:
        for line in r.iter_lines(decode_unicode=True):
            if not line:
                continue
            try:
                yield json.loads(line)
            except json.JSONDecodeError as e:
                _log.warning("ndjson_parse_error", extra={"error": str(e), "line": line[:120]})

    @staticmethod
    def iter_sse_json(r: requests.Response) -> Iterator[Dict[str, Any]]:
        for raw_line in r.iter_lines(decode_unicode=True):
            if not raw_line or not raw_line.startswith("data:"):
                continue
            data = raw_line[len("data:"):].strip()
            if data == "[DONE]":
                break
            try:
                yield json.loads(data)
            except json.JSONDecodeError as e:
                _log.warning("sse_parse_error", extra={"error": str(e), "data": data[:120]})
