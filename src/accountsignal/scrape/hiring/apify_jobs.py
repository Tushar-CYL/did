"""Apify hiring source — company OWN career-site / ATS data.

Uses the "Fantastic Jobs ATS API" actor, which aggregates postings directly from
companies' own Applicant Tracking Systems (Workday, Phenom, Eightfold, iCIMS,
SuccessFactors, Greenhouse, Lever, …) — not a job board. Filtered per company
(organizationSearch) + India, it returns the real open roles with full JD text,
so we get authentic coverage and can extract the tools/skills intel.

Cost: ~$0.012 per job (free tier). A month-to-date spend guard protects the $5
free ceiling. Requires APIFY_TOKEN + apify-client.
"""
from __future__ import annotations

import logging
from datetime import date, datetime, timedelta

import requests

from ...store.schema import Role
from . import base

log = logging.getLogger("accountsignal.hiring.apify")

_ACTOR = "fantastic-jobs/career-site-job-listing-api"

_SENIORITY_MAP = {
    "internship": "Junior", "entry level": "Junior", "associate": "Mid",
    "mid-senior level": "Senior", "mid senior level": "Senior", "director": "Executive",
    "executive": "Executive",
}

_run_spend_usd = 0.0


def spent_this_run() -> float:
    return _run_spend_usd


def month_usage_usd(token: str) -> float | None:
    try:
        r = requests.get("https://api.apify.com/v2/users/me/usage/monthly",
                         headers={"Authorization": f"Bearer {token}"}, timeout=20)
        if r.status_code == 200:
            msu = r.json()["data"].get("monthlyServiceUsage", {}) or {}
            return sum(v.get("amountAfterVolumeDiscountUsd", 0) for v in msu.values())
    except Exception as exc:
        log.info("apify: usage check failed: %s", exc)
    return None


def _city(it: dict) -> str:
    for key in ("cities_derived", "locations_derived", "locations"):
        v = it.get(key)
        if isinstance(v, list) and v:
            return str(v[0]).split(",")[0].strip()
        if isinstance(v, str) and v:
            return v.split(",")[0].strip()
    return ""


def _seniority(it: dict) -> str:
    lvl = (it.get("ai_experience_level") or "").lower()
    return _SENIORITY_MAP.get(lvl, base.guess_seniority(it.get("title", "")))


def _posted(it: dict) -> tuple[str, int | None]:
    raw = it.get("date_posted") or ""
    try:
        d = datetime.fromisoformat(raw.replace("Z", "+00:00")).date()
        return d.isoformat(), (date.today() - d).days
    except Exception:
        return (raw[:10] if raw else ""), None


def fetch_india_roles(company_name: str, token: str, lookback_days: int = 30,
                      max_items: int = 25, budget_usd: float = 4.5) -> list[Role]:
    if not token:
        return []
    try:
        from apify_client import ApifyClient
    except ImportError:
        log.warning("apify: apify-client not installed; skipping %s", company_name)
        return []

    global _run_spend_usd
    used = month_usage_usd(token)
    if used is not None and used >= budget_usd:
        log.warning("apify: budget guard hit (month-to-date $%.2f >= $%.2f); skipping %s",
                    used, budget_usd, company_name)
        return []

    since = (date.today() - timedelta(days=lookback_days)).isoformat()
    run_input = {
        "organizationSearch": [company_name], "locationSearch": ["India"],
        "limit": max(int(max_items), 10), "descriptionType": "text",
        "datePostedAfter": since, "removeAgency": True,
    }
    client = ApifyClient(token)
    try:
        run = client.actor(_ACTOR).call(run_input=run_input)
        run = client.run(run.id).get()
    except Exception as exc:
        log.warning("apify: run failed for %s: %s", company_name, exc)
        return []
    _run_spend_usd += float(getattr(run, "usage_total_usd", 0) or 0.0)
    if run.status != "SUCCEEDED":
        log.warning("apify: run %s for %s", run.status, company_name)
        return []

    roles: list[Role] = []
    for it in client.dataset(run.default_dataset_id).iterate_items():
        city = _city(it)
        loc_blob = " ".join(str(x) for x in (it.get("locations_derived") or [])) or city
        if not base.is_india(loc_blob + " India"):  # actor already filters India; keep anyway
            pass
        posted_date, days_open = _posted(it)
        if not base.within_lookback(days_open, lookback_days):
            continue
        # seed the tools text with AI-extracted key skills so classify.extract catches them
        ai_skills = it.get("ai_key_skills") or []
        desc = (it.get("description_text") or "")
        if ai_skills:
            desc = desc + " \nKey skills: " + ", ".join(str(s) for s in ai_skills)
        roles.append(Role(
            role=(it.get("title") or "").strip(),
            city=city, country="India",
            team=_team(it), seniority=_seniority(it),
            posted_date=posted_date, days_open=days_open,
            job_id=str(it.get("id") or ""),
            source_url=it.get("url") or "",
            description=desc[:7000],
        ))
    log.info("apify(ATS): %s -> %d India roles (run spend so far $%.2f)",
             company_name, len(roles), _run_spend_usd)
    return roles


def _team(it: dict) -> str:
    tax = it.get("ai_taxonomies_a")
    if isinstance(tax, list) and tax:
        first = tax[0]
        if isinstance(first, dict):
            return str(first.get("name") or first.get("value") or "")[:60]
        return str(first)[:60]
    return ""
