"""Mercedes-Benz jobs adapter (MBRDI) — jobs.api.mercedes-benz.com public search.

The API returns global postings sorted by publication date (10/page). We page
from newest and stop once postings fall outside the lookback window, keeping the
India ones. Full JD is read from each India posting's detail page (JSON-LD).
"""
from __future__ import annotations

import json
import logging
import urllib.parse
from datetime import date, datetime

from ...http import Http
from ...store.schema import Role
from . import base

log = logging.getLogger("accountsignal.hiring.mercedes")

_API = "https://jobs.api.mercedes-benz.com/search"
_PAGE = 50        # India-filtered, so a larger page is fine
_MAX_PAGES = 12   # 233 India postings / 50 ≈ 5 pages; headroom
_IN_COUNTRY = 390  # Mercedes country code for India


def _page(first: int, http: Http) -> list[dict]:
    # Query India directly via SearchCriteria (PositionLocation.Country = India).
    # The old approach paginated the global default feed and missed India roles.
    data = {"LanguageCode": "EN",
            "SearchParameters": {"FirstItem": first, "CountItem": _PAGE},
            "SearchCriteria": [{"CriterionName": "PositionLocation.Country",
                                "CriterionValue": [_IN_COUNTRY]}]}
    url = f"{_API}?data=" + urllib.parse.quote(json.dumps(data))
    r = http.get(url, headers={"Accept": "application/json"})
    if r is None or r.status_code != 200 or "json" not in r.headers.get("content-type", ""):
        return []
    return (r.json().get("SearchResult", {}) or {}).get("SearchResultItems", []) or []


def _jd(url: str, http: Http) -> str:
    if not url:
        return ""
    r = http.get(url)
    if r is None or r.status_code != 200:
        return ""
    try:
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(r.text, "lxml")
        for s in soup.find_all("script", type="application/ld+json"):
            try:
                d = json.loads(s.string or "{}")
            except Exception:
                continue
            for b in (d if isinstance(d, list) else [d]):
                if isinstance(b, dict) and b.get("@type") == "JobPosting":
                    return BeautifulSoup(str(b.get("description", "")), "lxml").get_text(" ", strip=True)[:7000]
    except Exception:
        pass
    return ""


def fetch_india_roles(career_url: str, http: Http, lookback_days: int = 30) -> list[Role]:
    roles: list[Role] = []
    seen: set[str] = set()
    first = 1  # Mercedes API is 1-indexed (FirstItem)
    for _ in range(_MAX_PAGES):
        items = _page(first, http)
        if not items:
            break
        first += len(items)
        for it in items:
            m = it.get("MatchedObjectDescriptor", {})
            jid = str(m.get("PositionID") or m.get("ID") or "")
            if jid and jid in seen:
                continue
            dp = m.get("PublicationStartDate", "")
            days_open = None
            if dp:
                try:
                    d = datetime.fromisoformat(str(dp).replace("Z", "+00:00")).date()
                    days_open = (date.today() - d).days
                except Exception:
                    pass
            if not base.within_lookback(days_open, lookback_days):
                continue
            locs = m.get("PositionLocation") or []
            india = any((l.get("CountryCode") == "IN" or "india" in str(l.get("CountryName", "")).lower())
                        for l in locs if isinstance(l, dict))
            if not india:
                continue
            city = ""
            for l in locs:
                if isinstance(l, dict) and (l.get("CountryCode") == "IN" or "india" in str(l.get("CountryName", "")).lower()):
                    # CityName can be a full office address ("Bengaluru, Brigade Tech
                    # Gardens, ...") — keep only the leading city token.
                    city = str(l.get("CityName", "")).split(",")[0].strip()
                    break
            if jid:
                seen.add(jid)
            src = m.get("PositionURI") or m.get("ApplyURI") or ""
            roles.append(Role(
                role=(m.get("PositionTitle") or "").strip(),
                city=city, country="India",
                # OrganizationName here is a postal address, not a team -> drop it.
                team="",
                seniority=base.guess_seniority(m.get("PositionTitle", "")),
                posted_date=str(dp)[:10], days_open=days_open,
                job_id=str(m.get("PositionID") or m.get("ID") or ""),
                source_url=src, description="",
            ))
        if len(items) < _PAGE:
            break  # last page
    # fetch JDs only for the India roles we kept (bounded)
    for r in roles:
        r.description = _jd(r.source_url, http)
    log.info("mercedes: -> %d India roles (last %dd)", len(roles), lookback_days)
    return roles
