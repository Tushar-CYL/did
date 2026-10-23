"""Playwright adapter — renders a company's India-filtered career URL in a real
browser (works on any JS-heavy ATS: Phenom, SuccessFactors/TalentBrew, Eightfold,
custom), collects the job detail links, then reads each detail page's structured
data (JSON-LD JobPosting) for the full JD — so tools/skills can be extracted.

Reliable and local (runs on the office laptop); no third-party actor.
"""
from __future__ import annotations

import json
import logging
import re
from datetime import date, datetime

from ...http import Http
from ...store.schema import Role
from . import base

log = logging.getLogger("accountsignal.hiring.playwright")

_UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
       "(KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36")

# anchor hrefs that are individual job detail pages (not categories/filters)
_JOB_RX = re.compile(r"/(job|jobs|careers/job|position|requisition)/", re.I)
_NOT_JOB_RX = re.compile(r"/c/|/go/[^/]+/\d+/?$|#|/search|/jobcart|/category", re.I)

_COLLECT = r"""
() => {
  const out = {};
  const anchors = [...document.querySelectorAll('a[href]')];
  for (const a of anchors) {
    const h = a.href;
    if (!h) continue;
    out[h] = (a.innerText || '').trim().slice(0, 120);
  }
  return out;
}
"""


def _render_links(url: str, pages: int) -> dict[str, str]:
    """Return {job_url: anchor_text} across a few paginated views."""
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        log.warning("playwright not installed")
        return {}
    links: dict[str, str] = {}
    try:
        with sync_playwright() as pw:
            browser = pw.chromium.launch(headless=True)
            ctx = browser.new_context(user_agent=_UA, ignore_https_errors=True)
            page = ctx.new_page()
            for p in range(pages):
                u = url
                if p:  # try common pagination params
                    sep = "&" if "?" in url else "?"
                    u = f"{url}{sep}pageNumber={p}&p={p}&page={p}"
                try:
                    page.goto(u, wait_until="domcontentloaded", timeout=40000)
                    page.wait_for_timeout(5000)
                    page.mouse.wheel(0, 6000)
                    page.wait_for_timeout(1500)
                except Exception as exc:
                    log.info("playwright goto %s: %s", u[:60], exc)
                    break
                found = page.evaluate(_COLLECT)
                new = 0
                for h, t in found.items():
                    if _JOB_RX.search(h) and not _NOT_JOB_RX.search(h):
                        if h not in links:
                            links[h] = t
                            new += 1
                if new == 0 and p > 0:
                    break
            browser.close()
    except Exception as exc:
        log.warning("playwright render failed: %s", exc)
    return links


def _html_text(h) -> str:
    if not h:
        return ""
    try:
        from bs4 import BeautifulSoup
        return BeautifulSoup(str(h), "lxml").get_text(" ", strip=True)[:7000]
    except Exception:
        return str(h)[:7000]


def _detail(url: str, http: Http) -> dict:
    """Return normalized {title, description, datePosted, country, city} from a job
    detail page — JSON-LD JobPosting first, then itemprop / TalentBrew fallbacks."""
    r = http.get(url)
    if r is None or r.status_code != 200:
        return {}
    from bs4 import BeautifulSoup
    soup = BeautifulSoup(r.text, "lxml")
    # 1) JSON-LD JobPosting
    for s in soup.find_all("script", type="application/ld+json"):
        if not s.string:
            continue
        try:
            d = json.loads(s.string)
        except Exception:
            continue
        for b in (d if isinstance(d, list) else [d]):
            if isinstance(b, dict) and b.get("@type") == "JobPosting":
                return {"title": b.get("title", ""), "description": _html_text(b.get("description", "")),
                        "datePosted": b.get("datePosted", ""), "country": _country(b), "city": _city(b)}
    # 2) itemprop / TalentBrew (data-careersite-propertyid) fallback
    def prop(sel):
        el = soup.select_one(sel)
        return el.get_text(" ", strip=True) if el else ""
    # a page may carry several [itemprop=description] blocks (intro boilerplate,
    # the real JD, an inclusion blurb) — take the longest, which is the JD.
    desc_els = soup.select('[itemprop="description"]')
    desc = max((e.get_text(" ", strip=True) for e in desc_els), key=len, default="")[:7000]
    out = {"title": prop('[itemprop="title"]'),
           "description": desc,
           "datePosted": "", "country": prop('[itemprop="addressCountry"]'),
           "city": prop('[itemprop="addressLocality"]')}
    dp = soup.select_one('[itemprop="datePosted"]')
    if dp:
        out["datePosted"] = dp.get("datetime") or dp.get("content") or dp.get_text(strip=True)
    for el in soup.select("[data-careersite-propertyid]"):
        pid = (el.get("data-careersite-propertyid") or "").lower()
        txt = el.get_text(" ", strip=True)
        if pid in ("date", "postaldate", "jobdate") and not out["datePosted"]:
            out["datePosted"] = txt
        elif pid in ("location", "primarylocation", "city") and not out["city"]:
            out["city"] = txt
        elif pid == "description" and not out["description"]:
            out["description"] = txt[:7000]
    return out


def _country(jp: dict) -> str:
    loc = jp.get("jobLocation")
    locs = loc if isinstance(loc, list) else [loc]
    for l in locs:
        if isinstance(l, dict):
            addr = l.get("address", {})
            if isinstance(addr, dict):
                c = str(addr.get("addressCountry", ""))
                if c:
                    return c
    return ""


def _city(jp: dict) -> str:
    loc = jp.get("jobLocation")
    locs = loc if isinstance(loc, list) else [loc]
    for l in locs:
        if isinstance(l, dict):
            addr = l.get("address", {})
            if isinstance(addr, dict):
                return str(addr.get("addressLocality", "") or addr.get("addressRegion", ""))
    return ""


def fetch_india_roles(career_url: str, http: Http, lookback_days: int = 30, pages: int = 4) -> list[Role]:
    if not career_url:
        return []
    links = _render_links(career_url, pages)
    log.info("playwright: %s -> %d job links", career_url[:50], len(links))
    roles: list[Role] = []
    for url, text in links.items():
        jp = _detail(url, http)
        title = (jp.get("title") or text or "").strip()
        if not title:
            continue
        country = jp.get("country", "")
        city = jp.get("city", "")
        # India filter: country IN/India or an Indian city. When the detail has no
        # location, trust the India-filtered search URL and keep it.
        blob = f"{country} {city}"
        if country and country.upper() not in ("IN", "INDIA") and not base.is_india(blob):
            continue
        desc = jp.get("description", "")
        posted_date, days_open = "", None
        dp = jp.get("datePosted")
        if dp:
            try:
                dd = datetime.fromisoformat(str(dp).replace("Z", "+00:00")).date()
                posted_date, days_open = dd.isoformat(), (date.today() - dd).days
            except Exception:
                posted_date = str(dp)[:10]
        if not base.within_lookback(days_open, lookback_days):
            continue
        roles.append(Role(
            role=title, city=base.india_city(blob) or city, country="India",
            seniority=base.guess_seniority(title),
            posted_date=posted_date, days_open=days_open,
            job_id=re.sub(r"\D", "", url.rsplit("/", 1)[-1])[:20],
            source_url=url, description=desc,
        ))
    log.info("playwright: %s -> %d India roles", career_url[:50], len(roles))
    return roles
