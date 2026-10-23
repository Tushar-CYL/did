"""Shared HTTP session: realistic UA, retries with backoff, polite per-host
rate limiting, sane timeouts. Used by every scraper so behaviour is uniform
and resilient (one failing host never aborts the run)."""
from __future__ import annotations

import logging
import os
import threading
import time
from collections import defaultdict

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

log = logging.getLogger("accountsignal.http")

_UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36"
)

_MIN_INTERVAL = 0.8  # seconds between requests to the same host
_last_hit: dict[str, float] = defaultdict(float)
_lock = threading.Lock()


def _throttle(host: str) -> None:
    with _lock:
        wait = _MIN_INTERVAL - (time.monotonic() - _last_hit[host])
        if wait > 0:
            time.sleep(wait)
        _last_hit[host] = time.monotonic()


class Http:
    def __init__(self, timeout: int = 30) -> None:
        self.timeout = timeout
        self.session = requests.Session()
        retry = Retry(
            total=3, connect=3, read=3, backoff_factor=1.0,
            status_forcelist=(429, 500, 502, 503, 504),
            allowed_methods=frozenset({"GET", "POST"}),
            raise_on_status=False,
        )
        adapter = HTTPAdapter(max_retries=retry, pool_connections=20, pool_maxsize=20)
        self.session.mount("https://", adapter)
        self.session.mount("http://", adapter)
        self.session.headers.update({
            "User-Agent": _UA,
            "Accept-Language": "en-US,en;q=0.9",
        })
        # On SSL-inspected corporate networks, pip-system-certs makes Python
        # trust the OS cert store. As a last resort, ACCOUNTSIGNAL_VERIFY_SSL=false
        # disables verification entirely.
        if os.getenv("ACCOUNTSIGNAL_VERIFY_SSL", "true").lower() in ("0", "false", "no"):
            self.session.verify = False
            try:
                import urllib3
                urllib3.disable_warnings()
            except Exception:
                pass

    def get(self, url: str, **kw) -> requests.Response | None:
        return self._req("GET", url, **kw)

    def post(self, url: str, **kw) -> requests.Response | None:
        return self._req("POST", url, **kw)

    def _req(self, method: str, url: str, **kw) -> requests.Response | None:
        from urllib.parse import urlparse
        host = urlparse(url).netloc
        _throttle(host)
        kw.setdefault("timeout", self.timeout)
        try:
            resp = self.session.request(method, url, **kw)
            if resp.status_code >= 400:
                log.warning("%s %s -> HTTP %s", method, url, resp.status_code)
            return resp
        except requests.RequestException as exc:
            log.warning("%s %s failed: %s", method, url, exc)
            return None
