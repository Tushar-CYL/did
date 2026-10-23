"""Live career-site Apify actor (santamaria-automations/career-site-jobs-scraper).

Scrapes the actual company career site across 36 ATS platforms (Phenom,
SuccessFactors, Eightfold, iCIMS, Workday, Oracle, Taleo, Avature, …) given a
{platform, company-url} query. Pulls India roles + full JD (detail pages), so
tools/skills can be extracted. Cheap (~$0.001/job). Covers the companies the
index-based ATS actor and free APIs miss.
"""
from __future__ import annotations

import logging
from datetime import date, datetime

from ...store.schema import Role
from . import base

log = logging.getLogger("accountsignal.hiring.apify_live")

ACTOR = "santamaria-automations/career-site-jobs-scraper"


def start_batch(queries: list[dict], token: str, lookback_days: int = 30, max_items: int = 25) -> str | None:
    """Start the actor (async) and return the run id."""
    try:
        from apify_client import ApifyClient
    except ImportError:
        log.warning("apify_live: apify-client not installed")
        return None
    client = ApifyClient(token)
    run_input = {
        "queries": queries, "location": "India", "postedWithinDays": lookback_days,
        "includeDescription": True, "detailCountries": ["India"],
        "maxJobsPerCompany": max_items, "includeSummaryRows": True,
    }
    run = client.actor(ACTOR).start(run_input=run_input)
    rid = run["id"] if isinstance(run, dict) else run.id
    log.info("apify_live: started run %s for %d queries", rid, len(queries))
    return rid


def fetch_run(token: str, run_id: str):
    """Return (status, job_items, cost_usd) for a run."""
    from apify_client import ApifyClient
    client = ApifyClient(token)
    run = client.run(run_id).get()
    status = run["status"] if isinstance(run, dict) else run.status
    cost = (run.get("usageTotalUsd") if isinstance(run, dict) else run.usage_total_usd) or 0.0
    ds = run["defaultDatasetId"] if isinstance(run, dict) else run.default_dataset_id
    items = list(client.dataset(ds).iterate_items())
    jobs = [it for it in items if it.get("_type") != "summary" and it.get("title")]
    return status, jobs, cost


def _posted(iso: str) -> tuple[str, int | None]:
    if not iso:
        return "", None
    try:
        d = datetime.fromisoformat(str(iso).replace("Z", "+00:00")).date()
        return d.isoformat(), (date.today() - d).days
    except Exception:
        return str(iso)[:10], None


def to_role(it: dict, lookback_days: int = 30) -> Role | None:
    country = (it.get("country") or "").upper()
    loc = it.get("location") or ""
    if country not in ("IN", "INDIA") and not base.is_india(loc + " India"):
        return None
    posted_date, days_open = _posted(it.get("created_at") or it.get("updated_at") or "")
    if not base.within_lookback(days_open, lookback_days):
        return None
    return Role(
        role=(it.get("title") or "").strip(),
        city=(it.get("city") or base.india_city(loc)).strip(), country="India",
        team=(it.get("department") or "").strip(),
        seniority=base.guess_seniority(it.get("title", "")),
        posted_date=posted_date, days_open=days_open,
        job_id=str(it.get("ats_job_id") or it.get("id") or ""),
        source_url=it.get("apply_url") or it.get("job_url") or "",
        description=str(it.get("description") or "")[:7000],
    )
