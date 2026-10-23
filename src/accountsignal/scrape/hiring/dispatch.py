"""Hiring source cascade — every free method first, Apify as a supplement.

Per company, in order (stop at the first that yields India roles):
  1. Workday CXS JSON API      (free, direct, full JDs)        — Workday sites
  2. iCIMS / Jibe JSON API      (free, direct, full JDs)        — iCIMS sites
  3. Playwright render          (free, local browser)           — Phenom, SuccessFactors,
     + JSON-LD / itemprop JD       any JS-heavy / custom ATS       Eightfold, TalentBrew, custom
  4. Apify ATS actor            (free tier, cloud)              — anything still missing

All of 1-3 run locally with no paid service, so they work on a restricted office
laptop; 4 uses the Apify free tier via its API token.
"""
from __future__ import annotations

import logging

from ...config import Company, Settings
from ...http import Http
from ...store.schema import Role
from . import apify_jobs, coveo, icims, mercedes, playwright_jobs, workday
from .detect import detect

log = logging.getLogger("accountsignal.hiring.dispatch")


def scrape_hiring(company: Company, http: Http, settings: Settings) -> tuple[list[Role], str | None, str]:
    """Return (roles, ats, note). Never raises."""
    career_url = company.career_url
    lookback = settings.lookback_days
    tried: list[str] = []

    def _try(name, fn):
        tried.append(name)
        try:
            roles = fn()
            if roles:
                return roles
        except Exception as exc:
            log.info("hiring %s failed for %s: %s", name, company.name, exc)
        return []

    ats = None
    roles: list[Role] = []
    source = None
    if career_url:
        det = detect(career_url, http)
        ats = det.ats

    # 1) free direct portal APIs
    if ats == "workday":
        roles = _try("workday", lambda: workday.fetch_india_roles(career_url, http, lookback))
        if roles:
            source = "workday"
    elif ats == "icims":
        roles = _try("icims", lambda: icims.fetch_india_roles(career_url, http, lookback))
        if roles:
            source = "icims"

    # 2) free local Playwright render — handles the JS-heavy ATS (Phenom/SF/Eightfold/custom)
    if not roles and career_url:
        roles = _try("playwright", lambda: playwright_jobs.fetch_india_roles(career_url, http, lookback))
        if roles:
            source = "playwright"

    # 2b) Coveo-powered sites (e.g. SLB) — capture the search token + replay
    if not roles and career_url and ("coveo" in career_url.lower() or "slb.com" in career_url.lower()):
        roles = _try("coveo", lambda: coveo.fetch_india_roles(career_url, http, lookback))
        if roles:
            source = "coveo"

    # 2c) Mercedes-Benz jobs API (MBRDI)
    if not roles and career_url and "mercedes-benz.com" in career_url.lower():
        roles = _try("mercedes", lambda: mercedes.fetch_india_roles(career_url, http, lookback))
        if roles:
            source = "mercedes"

    # 3) Apify fallback (free tier) for anything still empty
    if not roles and settings.apify_token:
        roles = _try("apify", lambda: apify_jobs.fetch_india_roles(
            company.name, settings.apify_token, lookback,
            settings.apify_max_items, settings.apify_max_usd))
        if roles:
            source = "apify"

    note = f"ats={ats}; src={source or 'none'}; tried={'>'.join(tried) or 'none'}; roles={len(roles)}"
    return roles, ats, note
