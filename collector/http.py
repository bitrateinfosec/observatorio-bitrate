"""Cliente HTTP compartido con reintentos y User-Agent identificable."""
import time

import requests

from .config import HTTP_TIMEOUT, USER_AGENT

_session = requests.Session()
_session.headers.update({"User-Agent": USER_AGENT, "Accept": "application/json"})


def request(method: str, url: str, retries: int = 3, **kwargs):
    kwargs.setdefault("timeout", HTTP_TIMEOUT)
    last = None
    for attempt in range(1, retries + 1):
        try:
            r = _session.request(method, url, **kwargs)
            if r.status_code == 429 or r.status_code >= 500:
                raise requests.HTTPError(f"HTTP {r.status_code}", response=r)
            r.raise_for_status()
            return r
        except requests.RequestException as e:
            last = e
            if attempt < retries:
                time.sleep(2 ** attempt)
    raise last


def get_json(url, **kw):
    return request("GET", url, **kw).json()


def post_json(url, **kw):
    return request("POST", url, **kw).json()
