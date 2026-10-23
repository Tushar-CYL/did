"""iCIMS (Jibe) adapter — free public JSON API on the company's own career host.

Modern iCIMS/Jibe career sites expose GET https://<host>/api/jobs with country
paging and full job descriptions. This is the company's own portal, free, with
JD text (so tools/skills can be extracted). Used for ZS Associates and any other
iCIMS company.
"""
from __future__ import annotations

import logging
from datetime import date, datetime
from urllib.parse import urlparse

from ...http import Http
from ...store.schema import Role
from . import base

log = logging.getLogger("accountsignal.hiring.icims")

_PAGE = 10          # iCIMS/Jibe caps page size at 10 (limit>10 -> HTTP 422)
_MAX_PAGES = 30


def _posted(iso: str) -> tuple[str, int | None]:
    if not iso:
        return "", None
    try:
        d = datetime.fromisoformat(iso.replace("Z", "+00:00").replace("+0000", "+00:00")).date()
        return d.isoformat(), (date.today() - d).days
    except Exception:
        return iso[:10], None


def _strip_html(html: str) -> str:
    if not html:
        return ""
    try:
        from bs4 import BeautifulSoup
        return BeautifulSoup(html, "lxml").get_text(" ", strip=True)
    except Exception:
        return html


def fetch_india_roles(career_url: str, http: Http, lookback_days: int = 30) -> list[Role]:
    if not career_url:
        return []
    host = urlparse(career_url).netloc
    if not host:
        return []
    roles: list[Role] = []
    seen: set[str] = set()
    for page in range(1, _MAX_PAGES + 1):   # iCIMS/Jibe pages are 1-indexed
        url = f"https://{host}/api/jobs?country=India&limit={_PAGE}&page={page}"
        r = http.get(url, headers={"Accept": "application/json"})
        if r is None or r.status_code != 200 or "json" not in r.headers.get("content-type", ""):
            break
        data = r.json()
        jobs = data.get("jobs") or []
        if not jobs:
            break
        for jj in jobs:
            jd = jj.get("data") if isinstance(jj, dict) and "data" in jj else jj
            if not isinstance(jd, dict):
                continue
            if (jd.get("country") or "").lower() not in ("india", "in", ""):
                continue
            rid = str(jd.get("req_id") or jd.get("slug") or jd.get("title"))
            if rid in seen:
                continue
            seen.add(rid)
            posted_date, days_open = _posted(jd.get("posted_date") or jd.get("create_date") or "")
            if not base.within_lookback(days_open, lookback_days):
                continue
            cats = jd.get("categories") or []
            team = ""
            if isinstance(cats, list) and cats and isinstance(cats[0], dict):
                team = str(cats[0].get("name") or "")
            desc = _strip_html(str(jd.get("description") or ""))
            roles.append(Role(
                role=(jd.get("title") or "").strip(),
                city=(jd.get("city") or "").strip(), country="India",
                team=team or str(jd.get("department") or ""),
                seniority=base.guess_seniority(jd.get("title", "")),
                posted_date=posted_date, days_open=days_open,
                job_id=str(jd.get("req_id") or ""),
                source_url=jd.get("apply_url") or "",
                description=desc[:7000],
            ))
        total = data.get("totalCount") or data.get("count") or 0
        if len(seen) >= total or len(jobs) < _PAGE:
            break
    log.info("icims: %s -> %d India roles", host, len(roles))
    return roles
