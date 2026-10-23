"""Generic Playwright DOM adapter — universal free fallback.

Renders a careers search page (JS included), scrolls to load more, then reads any
job links from the DOM and keeps the India ones. Works across many platforms
(Eightfold, Phenom, iCIMS, custom) because it keys off job-link hrefs + card text
rather than a platform-specific API. Best-effort: fields beyond title/location/url
are filled where present; missing dates mean the role is kept (cannot be excluded).
"""
from __future__ import annotations

import logging
from urllib.parse import urlparse

from ...store.schema import Role
from . import base

log = logging.getLogger("accountsignal.hiring.generic")

_UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
       "(KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36")

# in-page collector: one record per unique job link (title line + card text)
_EXTRACT = r"""
() => {
  const re = /\/(job|jobs|position|positions|requisition|req|opening)\//i;
  const anchors = [...document.querySelectorAll('a[href]')].filter(a => re.test(a.href));
  const seen = new Set(); const out = [];
  for (const a of anchors) {
    if (seen.has(a.href)) continue; seen.add(a.href);
    const card = a.closest('[data-test-id], li, article, .card, .job, .position-card, div') || a;
    out.push({ href: a.href, text: (card.innerText || a.innerText || '').trim() });
  }
  return out;
}
"""


def _india_variants(career_url: str) -> list[str]:
    """A few URL forms likely to pre-filter to India (keeps results relevant)."""
    u = career_url.rstrip("/")
    variants = [career_url]
    sep = "&" if "?" in career_url else "?"
    variants.append(f"{career_url}{sep}location=India")
    variants.append(f"{career_url}{sep}country=India")
    # de-dup preserving order
    out, seen = [], set()
    for v in variants:
        if v not in seen:
            seen.add(v); out.append(v)
    return out[:2]  # bound render attempts per company


def _parse(text: str, href: str) -> Role | None:
    lines = [ln.strip() for ln in text.split("\n") if ln.strip()]
    if not lines:
        return None
    title = lines[0]
    location = ""
    for ln in lines[1:]:
        if base.is_india(ln) or ("," in ln and len(ln) < 60):
            location = ln
            break
    if not base.is_india(location):
        return None
    posted_date, days_open = "", None
    for ln in lines:
        low = ln.lower()
        if "posted" in low or "ago" in low:
            posted_date, days_open = base.parse_relative_posted(ln)
            break
    return Role(
        role=title[:140], city=base.india_city(location), country="India",
        seniority=base.guess_seniority(title),
        posted_date=posted_date, days_open=days_open,
        job_id=href.rstrip("/").split("/")[-1][:60], source_url=href,
    )


def fetch_india_roles(career_url: str, http=None, lookback_days: int = 30,
                      scrolls: int = 10) -> list[Role]:
    if not career_url:
        return []
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        log.warning("generic: playwright not installed; skipping %s", career_url)
        return []

    host = urlparse(career_url).netloc
    best: dict[str, Role] = {}
    try:
        with sync_playwright() as pw:
            browser = pw.chromium.launch(headless=True)
            context = browser.new_context(user_agent=_UA, ignore_https_errors=True)
            page = context.new_page()
            for url in _india_variants(career_url):
                try:
                    page.goto(url, wait_until="domcontentloaded", timeout=40000)
                    page.wait_for_timeout(4500)
                    last = 0
                    for _ in range(scrolls):
                        page.mouse.wheel(0, 6000)
                        page.wait_for_timeout(1000)
                        n = page.evaluate("document.querySelectorAll('a[href]').length")
                        if n == last:
                            break
                        last = n
                    for c in page.evaluate(_EXTRACT):
                        role = _parse(c.get("text", ""), c.get("href", ""))
                        if role and base.within_lookback(role.days_open, lookback_days):
                            best[role.source_url] = role
                except Exception as exc:
                    log.info("generic: %s attempt failed: %s", url[:60], exc)
                if best:   # got results from this variant; no need to try more
                    break
            browser.close()
    except Exception as exc:
        log.warning("generic: browser failed for %s: %s", host, exc)
        return []

    roles = list(best.values())
    log.info("generic: %s -> %d India roles", host, len(roles))
    return roles
