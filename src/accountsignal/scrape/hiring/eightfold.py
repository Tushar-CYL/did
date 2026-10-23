"""Eightfold adapter — free public JSON API (no key).

List: GET https://<tenant>.eightfold.ai/api/apply/v2/jobs?domain=<domain>&start=&num=10
Detail (full JD): GET .../api/apply/v2/jobs/<id>?domain=<domain>
The server-side location filter is unreliable, so we page through and keep the
India positions, then fetch each one's description for tool extraction.
"""
from __future__ import annotations

import logging
import re
from urllib.parse import urlparse

from ...http import Http
from ...store.schema import Role
from . import base

log = logging.getLogger("accountsignal.hiring.eightfold")

_NUM = 10
_MAX_POS = 400   # cap positions paged per company (40 pages)


def _registered_domain(host: str) -> str:
    """careers.bcg.com -> bcg.com ; careers.elcompanies.com -> elcompanies.com"""
    parts = host.split(".")
    if len(parts) >= 3 and parts[-2] in ("co", "com") and parts[-1] in ("in", "uk"):
        return ".".join(parts[-3:])
    return ".".join(parts[-2:])


# generic Eightfold hosts that are NOT a company tenant
_GENERIC = {"app", "vs-errors", "cdn", "static", "assets", "www", "api", "media"}


def _discover(career_url: str, http: Http) -> tuple[str, str] | None:
    r = http.get(career_url, allow_redirects=True)
    if r is None or not r.text:
        return None
    tenant = None
    for cand in re.findall(r"([a-z0-9-]+)\.eightfold\.ai", r.text):
        if cand not in _GENERIC:
            tenant = cand
            break
    if not tenant:
        host = urlparse(str(r.url)).netloc
        if "eightfold.ai" in host and host.split(".")[0] not in _GENERIC:
            tenant = host.split(".")[0]
    if not tenant:
        # fall back to the registered-domain label (e.g. elcompanies)
        tenant = _registered_domain(urlparse(career_url).netloc).split(".")[0]
    domain = _registered_domain(urlparse(career_url).netloc)
    return tenant, domain


def _is_india(p: dict) -> bool:
    loc = str(p.get("location") or "")
    if base.is_india(loc):
        return True
    for l in (p.get("locations") or []):
        if base.is_india(str(l)):
            return True
    return False


def _jd(tenant: str, domain: str, pid, http: Http) -> str:
    r = http.get(f"https://{tenant}.eightfold.ai/api/apply/v2/jobs/{pid}?domain={domain}",
                 headers={"Accept": "application/json"})
    if r is None or r.status_code != 200 or "json" not in r.headers.get("content-type", ""):
        return ""
    try:
        from bs4 import BeautifulSoup
        d = r.json()
        html = d.get("job_description") or d.get("description") or (d.get("position") or {}).get("job_description") or ""
        return BeautifulSoup(str(html), "lxml").get_text(" ", strip=True)[:7000]
    except Exception:
        return ""


def fetch_india_roles(career_url: str, http: Http, lookback_days: int = 30) -> list[Role]:
    disc = _discover(career_url, http)
    if not disc:
        log.info("eightfold: no tenant for %s", career_url)
        return []
    tenant, domain = disc
    roles: list[Role] = []
    start = 0
    while start < _MAX_POS:
        url = f"https://{tenant}.eightfold.ai/api/apply/v2/jobs?domain={domain}&start={start}&num={_NUM}&query="
        r = http.get(url, headers={"Accept": "application/json"})
        if r is None or r.status_code != 200 or "json" not in r.headers.get("content-type", ""):
            break
        data = r.json()
        positions = data.get("positions") or []
        if not positions:
            break
        for p in positions:
            if not _is_india(p):
                continue
            loc = str(p.get("location") or (p.get("locations") or [""])[0])
            desc = _jd(tenant, domain, p.get("id"), http)
            roles.append(Role(
                role=(p.get("name") or "").strip(),
                city=base.india_city(loc), country="India",
                seniority=base.guess_seniority(p.get("name", "")),
                job_id=str(p.get("id") or ""),
                source_url=p.get("canonicalPositionUrl") or f"https://{tenant}.eightfold.ai/careers/job/{p.get('id')}",
                description=desc,
            ))
        start += _NUM
        if start >= (data.get("count") or 0):
            break
    log.info("eightfold: %s (%s) -> %d India roles", tenant, domain, len(roles))
    return roles
