from typing import Tuple, Optional, Dict, Any, Iterator
from dataclasses import dataclass, field
from contextlib import contextmanager
import requests
import json
import hestia.settings as settings

@dataclass(frozen=True)
class HttpClient:
    """
    TODO:
    - initialize without a base_url. always require full url.
    - proper construction of the requests.
    """
    base_url: str
    timeout: Tuple[float, float] = settings.REQUEST_TIMEOUT
    api_key: Optional[str] = None
    session: requests.Session = field(default_factory= requests.Session, repr=False, compare=False)

    @contextmanager
    def _post_stream(self, 
                     endpoint: str,
                     payload: Dict[str, Any],
                     headers: Optional[Dict[str, str]]= None):
        url = self.base_url + endpoint
        r = self.session.post(
            url,
            json=payload,
            headers=headers,
            timeout=self.timeout,
            stream=True
        )
        try:
            r.raise_for_status()
            yield r
        finally:
            r.close()

    def post(self, 
             endpoint: str, 
             payload: Dict[str, Any], 
             headers: Optional[Dict[str, str]] = None,
             stream: bool = False):

        if stream:
            return self._post_stream(endpoint, payload, headers)
        
        url = self.base_url + endpoint
        try:
            r = self.session.post(url, 
                              json=payload, 
                              headers=headers, 
                              timeout=self.timeout)
            r.raise_for_status()
        except requests.HTTPError as e:
            resp = e.response

        return r
    

    @staticmethod
    def iter_ndjson(r: requests.Response) -> Iterator[Dict[str, Any]]:
        """
        Helper: parse NDJSON response into dicts line-by-line.
        """
        
        for line in r.iter_lines(decode_unicode=True):
            if not line:
                continue
            yield json.loads(line)

    
    def get(self):
        pass

    def put(self):
        pass

