"""Workday adapter — uses the public CXS JSON API.

Workday powers many large employers. Even when a company fronts it with a custom
domain (e.g. jobs.carrier.com), the data is served by <tenant>.<wdN>.myworkdayjobs.com
via /wday/cxs/<tenant>/<site>/jobs. We auto-discover tenant/wd/site from the
careers page, then page through jobs filtered to India + the last-month window.
"""
from __future__ import annotations

import logging
import re

from ...http import Http
from ...store.schema import Role
from . import base

log = logging.getLogger("accountsignal.hiring.workday")

_JSON = {"Accept": "application/json", "Content-Type": "application/json"}
_PAGE = 20
_MAX_PAGES = 15  # safety cap (300 postings) per company
# Workday's universal India country reference id (same across all tenants)
_INDIA_ID = "c4f78be1a8f14da0ab49ce1162348a5e"
_INDIA_FACET = {"locationCountry": [_INDIA_ID]}


def _fetch_jd(host: str, tenant: str, site: str, ext: str, http) -> str:
    """Fetch the full job description from the Workday CXS detail endpoint."""
    if not ext:
        return ""
    url = f"https://{host}/wday/cxs/{tenant}/{site}{ext}"
    r = http.get(url, headers=_JSON)
    if r is None or r.status_code != 200 or "json" not in r.headers.get("content-type", ""):
        return ""
    try:
        from bs4 import BeautifulSoup
        html = (r.json().get("jobPostingInfo", {}) or {}).get("jobDescription", "") or ""
        return BeautifulSoup(html, "lxml").get_text(" ", strip=True)[:6000]
    except Exception:
        return ""


def _discover(career_url: str, http: Http) -> tuple[str, str, str] | None:
    """Return (host, tenant, site) or None."""
    resp = http.get(career_url, allow_redirects=True)
    if resp is None or not resp.text:
        return None
    text = resp.text
    final = str(resp.url)
    # pattern A: <tenant>.<wdN>.myworkdayjobs.com/<site>
    m = re.search(r"([A-Za-z0-9-]+)\.(wd\d+)\.myworkdayjobs\.com", final + " " + text)
    if m:
        tenant, wd = m.group(1), m.group(2)
        host = f"{tenant}.{wd}.myworkdayjobs.com"
    else:
        # pattern B: <wdN>.myworkdaysite.com/recruiting/<tenant>/<site>  (e.g. Magna)
        m = re.search(r"(wd\d+)\.myworkdaysite\.com/(?:[a-z]{2}-[A-Z]{2}/)?recruiting/([A-Za-z0-9_-]+)/([A-Za-z0-9_-]+)", final + " " + text)
        if not m:
            return None
        wd, tenant, site = m.group(1), m.group(2), m.group(3)
        return f"{wd}.myworkdaysite.com", tenant, site
    # site id, in priority order of reliability:
    site = ""
    for pat in (
        r"/wday/cxs/" + re.escape(tenant) + r"/([A-Za-z0-9_-]+)/",   # explicit CXS ref
        re.escape(host) + r"/[a-z]{2}-[A-Z]{2}/([A-Za-z0-9_]+)",      # host/en-US/<site>
        re.escape(host) + r"/([A-Za-z0-9_]+)(?:[/\"'?])",            # host/<site>
        r"myworkdayjobs\.com/(?:wday/cxs/[^/]+/)?(?:[a-z]{2}-[A-Z]{2}/)?([A-Za-z0-9_]+)",
    ):
        ms = re.search(pat, text)
        if ms and ms.group(1).lower() not in ("wday", "en-us"):
            site = ms.group(1)
            break
    return host, tenant, site


def _candidate_sites(discovered: str, tenant: str) -> list[str]:
    seen, out = set(), []
    for s in [discovered, "External", "Careers", f"{tenant.capitalize()}Careers",
              tenant.capitalize(), "Search", "jobs"]:
        if s and s not in seen:
            seen.add(s)
            out.append(s)
    return out


def fetch_india_roles(career_url: str, http: Http, lookback_days: int = 30) -> list[Role]:
    disc = _discover(career_url, http)
    if not disc:
        log.info("workday: could not discover tenant for %s", career_url)
        return []
    host, tenant, site_guess = disc

    # find a working CXS site
    base_url = None
    for site in _candidate_sites(site_guess, tenant):
        url = f"https://{host}/wday/cxs/{tenant}/{site}/jobs"
        r = http.post(url, json={"appliedFacets": {}, "limit": 1, "offset": 0, "searchText": ""}, headers=_JSON)
        if r is not None and r.status_code == 200 and "json" in r.headers.get("content-type", ""):
            base_url = url
            break
    if not base_url:
        log.info("workday: no CXS site matched for %s (%s)", tenant, career_url)
        return []

    # pick the query that this tenant accepts: India country facet (preferred) or
    # a text search for "India" — then always post-filter by is_india.
    def _post(offset: int):
        for body in ({"appliedFacets": _INDIA_FACET, "limit": _PAGE, "offset": offset, "searchText": ""},
                     {"appliedFacets": {}, "limit": _PAGE, "offset": offset, "searchText": "India"}):
            r = http.post(base_url, json=body, headers=_JSON)
            if r is not None and r.status_code == 200 and "json" in r.headers.get("content-type", ""):
                d = r.json()
                if d.get("jobPostings"):
                    return d
        return None

    roles: list[Role] = []
    offset = 0
    for _ in range(_MAX_PAGES):
        data = _post(offset)
        if not data:
            break
        postings = data.get("jobPostings", [])
        if not postings:
            break
        for p in postings:
            loc = p.get("locationsText", "") or ""
            if not base.is_india(loc):
                continue
            posted_date, days_open = base.parse_relative_posted(p.get("postedOn", ""))
            if not base.within_lookback(days_open, lookback_days):
                continue
            ext = p.get("externalPath", "") or ""
            src = f"https://{host}{ext}" if ext.startswith("/") else ext
            bullets = p.get("bulletFields") or []
            jd = _fetch_jd(host, tenant, site, ext, http)
            roles.append(Role(
                role=(p.get("title") or "").strip(),
                city=base.india_city(loc),
                country="India",
                seniority=base.guess_seniority(p.get("title", "")),
                posted_date=posted_date,
                days_open=days_open,
                job_id=str(bullets[0]) if bullets else "",
                source_url=src,
                description=jd,
            ))
        total = data.get("total", 0)
        offset += _PAGE
        if offset >= total:
            break
    log.info("workday: %s -> %d India roles (last %dd)", tenant, len(roles), lookback_days)
    return roles
