"""Collect + dedupe market-intelligence news for a company across all 5 fields.

Each unique article is assigned to the single category it fits best (by keyword
overlap in the title), so the same event never repeats across cards and later
categories are not starved by first-wins dedup.
"""
from __future__ import annotations

import logging
import re

from ...http import Http
from ...store.schema import NewsItem
from . import google_news_rss as gnews

log = logging.getLogger("accountsignal.news.collect")

CATEGORIES = ("hiring", "vision", "partnerships", "financial", "expansion")
_PER_CATEGORY_CAP = 40  # raw storage cap; enrichment/ranking later trims to top-N

# keyword lists for best-category scoring (derived from the RSS query terms)
_SCORE_TERMS: dict[str, tuple[str, ...]] = {
    "hiring": ("hiring", "recruit", "headcount", "workforce", "layoff", "job cut", "jobs", "talent", "staff"),
    "vision": ("strategy", "strategic", "leadership", "ceo", "restructur", "transformation", "reorganis", "reorganiz", "vision"),
    "partnerships": ("partner", "alliance", "collaborat", "joint venture", "deal", "agreement", "vendor", "tie-up", "tie up"),
    "financial": ("earnings", "revenue", "results", "profit", "acquisition", "acquire", "funding", "quarter", "guidance", "merger"),
    "expansion": ("expansion", "expand", "facility", "investment", "invest", "capability centre", "capability center", "gcc", "opens", "plant", "factory", "centre", "center"),
}


def _norm_title(t: str) -> str:
    t = re.sub(r"\s+-\s+[^-]+$", "", t)          # drop trailing " - Source"
    t = re.sub(r"[^a-z0-9]+", " ", t.lower())
    return t.strip()


def _best_category(title: str, fetched: str) -> str:
    lc = title.lower()
    best, best_score = fetched, -1
    for cat, terms in _SCORE_TERMS.items():
        score = sum(1 for term in terms if term in lc)
        if score > best_score:
            best, best_score = cat, score
    return best if best_score > 0 else fetched


# generic words dropped when deriving a company's distinctive name tokens
_STOP = {"associates", "inc", "plc", "ltd", "limited", "international", "company",
         "companies", "corporation", "corp", "global", "services", "service", "group",
         "holdings", "co", "the", "and", "india", "research", "development", "centre",
         "center", "innovation", "capability"}


def _distinctive_tokens(news_query: str) -> list[str]:
    toks = re.findall(r"[a-z0-9&-]+", news_query.lower())
    return [t for t in toks if len(t) >= 2 and t not in _STOP]


def _mentions(title: str, tokens: list[str]) -> bool:
    lc = title.lower()
    return any(re.search(r"\b" + re.escape(t) + r"\b", lc) for t in tokens)


def _gather(news_query: str, http: Http, lookback_days: int, quoted: bool) -> dict[str, NewsItem]:
    seen: dict[str, NewsItem] = {}
    for cat in CATEGORIES:
        for item in gnews.fetch_category(news_query, cat, http, lookback_days, quoted=quoted):
            key = _norm_title(item.title)
            if not key or key in seen:
                continue
            item.category = _best_category(item.title, cat)
            seen[key] = item
    return seen


def collect(news_query: str, http: Http, lookback_days: int = 30) -> dict[str, list[NewsItem]]:
    """Return {category: [NewsItem]} — unique articles, each in its best field,
    sorted most-recent first and capped per field. Falls back to an unquoted
    query when the exact-phrase query yields nothing (handles long entity names)."""
    seen = _gather(news_query, http, lookback_days, quoted=True)
    if not seen:
        log.info("news: '%s' empty with exact phrase; retrying unquoted", news_query)
        seen = _gather(news_query, http, lookback_days, quoted=False)

    # relevance: keep only items that actually name the company (drops tangential
    # pieces, e.g. generic pharma news surfacing under 'ZS Associates'). If the
    # strict filter leaves nothing, keep the original rather than show an empty
    # account.
    tokens = _distinctive_tokens(news_query)
    if tokens:
        filtered = {k: v for k, v in seen.items() if _mentions(v.title, tokens)}
        if filtered:
            seen = filtered

    out: dict[str, list[NewsItem]] = {c: [] for c in CATEGORIES}
    for item in seen.values():
        out[item.category].append(item)
    for cat in CATEGORIES:
        out[cat].sort(key=lambda it: it.date or "", reverse=True)
        out[cat] = out[cat][:_PER_CATEGORY_CAP]

    total = sum(len(v) for v in out.values())
    log.info("news: %s -> %d unique items across %d fields", news_query, total, len(CATEGORIES))
    return out
