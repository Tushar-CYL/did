"""Coveo adapter (e.g. SLB / careers.slb.com) — Coveo-powered career sites.

Coveo needs a short-lived search token from the page, so we use Playwright to
load the India-filtered listing, capture the search request (token + body) that
returns the most results, then replay it with a large page size and read the job
records. Free + local.
"""
from __future__ import annotations

import json
import logging
from datetime import date, datetime

import requests

from ...http import Http
from ...store.schema import Role
from . import base

log = logging.getLogger("accountsignal.hiring.coveo")


def _capture(career_url: str) -> dict | None:
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        return None
    pairs: list[dict] = []

    def on_response(resp):
        try:
            if "coveo.com/rest/search" not in resp.url or resp.request.method != "POST":
                return
            d = resp.json()
            pairs.append({"total": d.get("totalCount") or 0, "url": resp.url,
                          "auth": resp.request.headers.get("authorization", ""),
                          "body": resp.request.post_data})
        except Exception:
            pass

    try:
        with sync_playwright() as pw:
            b = pw.chromium.launch(headless=True)
            pg = b.new_page()
            pg.on("response", on_response)
            try:
                pg.goto(career_url, wait_until="networkidle", timeout=45000)
            except Exception:
                pass
            pg.wait_for_timeout(5000)
            b.close()
    except Exception as exc:
        log.warning("coveo: capture failed: %s", exc)
        return None
    pairs = [p for p in pairs if p.get("body") and p.get("auth")]
    if not pairs:
        return None
    pairs.sort(key=lambda p: p["total"], reverse=True)
    return pairs[0]


def _jd(url: str, http: Http) -> str:
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
            for bb in (d if isinstance(d, list) else [d]):
                if isinstance(bb, dict) and bb.get("@type") == "JobPosting":
                    return BeautifulSoup(str(bb.get("description", "")), "lxml").get_text(" ", strip=True)[:7000]
        el = soup.select_one('[itemprop="description"], .job-description, #jobdescription')
        return el.get_text(" ", strip=True)[:7000] if el else ""
    except Exception:
        return ""


def fetch_india_roles(career_url: str, http: Http, lookback_days: int = 30, fetch_jd: bool = False) -> list[Role]:
    cap = _capture(career_url)
    if not cap:
        log.info("coveo: no search request captured for %s", career_url)
        return []
    try:
        body = json.loads(cap["body"])
    except Exception:
        return []
    body["numberOfResults"] = 200
    body["firstResult"] = 0
    try:
        r = requests.post(cap["url"], json=body,
                          headers={"Authorization": cap["auth"], "Content-Type": "application/json"}, timeout=30)
    except Exception as exc:
        log.warning("coveo: replay failed: %s", exc)
        return []
    if r.status_code != 200:
        return []
    results = r.json().get("results", [])
    roles: list[Role] = []
    for res in results:
        raw = res.get("raw", {})
        country = raw.get("country")
        country_s = " ".join(country) if isinstance(country, list) else str(country or "")
        if not base.is_india(country_s + " " + str(raw.get("city", ""))):
            continue
        posted_date, days_open = "", None
        ms = raw.get("jobposteddate") or raw.get("date")
        if ms:
            try:
                d = datetime.utcfromtimestamp(int(ms) / 1000).date()
                posted_date, days_open = d.isoformat(), (date.today() - d).days
            except Exception:
                pass
        if not base.within_lookback(days_open, lookback_days):
            continue
        url = res.get("clickUri") or res.get("uri") or ""
        desc = _jd(url, http) if fetch_jd and url else ""
        roles.append(Role(
            role=(res.get("title") or raw.get("title") or "").strip(),
            city=(raw.get("city") or "").strip(), country="India",
            seniority=base.guess_seniority(res.get("title", "")),
            posted_date=posted_date, days_open=days_open,
            job_id=str(raw.get("permanentid") or "")[:30], source_url=url, description=desc,
        ))
    log.info("coveo: %s -> %d India roles", career_url[:40], len(roles))
    return roles
