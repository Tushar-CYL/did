"""Google News RSS collector — free, no key, global coverage, last-month window.

One query per company per market-intelligence category. Google News RSS supports
a `when:<N>d` recency operator; we also hard-filter by publication date.
"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from time import mktime
from urllib.parse import quote_plus

import feedparser

from ...http import Http
from ...store.schema import NewsItem

log = logging.getLogger("accountsignal.news.gnews")

# category -> OR-group of query terms (GLOBAL market intelligence, last month)
CATEGORY_TERMS: dict[str, str] = {
    "hiring": "hiring OR recruitment OR headcount OR workforce OR layoffs OR \"new jobs\" OR \"job cuts\"",
    "vision": "strategy OR leadership OR CEO OR restructuring OR transformation OR \"strategic\" OR reorganisation",
    "partnerships": "partnership OR alliance OR collaboration OR \"joint venture\" OR deal OR agreement OR vendor",
    "financial": "earnings OR revenue OR results OR profit OR acquisition OR funding OR quarterly OR guidance",
    "expansion": "expansion OR \"new facility\" OR investment OR \"capability centre\" OR GCC OR opens OR plant OR factory",
}

_RSS = "https://news.google.com/rss/search?q={q}&hl=en-US&gl=US&ceid=US:en"


def _entry_date(entry) -> str:
    for key in ("published_parsed", "updated_parsed"):
        tp = entry.get(key)
        if tp:
            return datetime.fromtimestamp(mktime(tp), tz=timezone.utc).date().isoformat()
    return ""


def fetch_category(news_query: str, category: str, http: Http, lookback_days: int = 30,
                   quoted: bool = True) -> list[NewsItem]:
    terms = CATEGORY_TERMS[category]
    name = f'"{news_query}"' if quoted else news_query
    q = f'{name} ({terms}) when:{lookback_days}d'
    url = _RSS.format(q=quote_plus(q))
    resp = http.get(url)
    if resp is None or resp.status_code != 200:
        return []
    feed = feedparser.parse(resp.content)
    cutoff = (datetime.now(timezone.utc) - timedelta(days=lookback_days)).date().isoformat()
    items: list[NewsItem] = []
    for e in feed.entries:
        date = _entry_date(e)
        if date and date < cutoff:
            continue
        source = ""
        if e.get("source") and e.source.get("title"):
            source = e.source.title
        items.append(NewsItem(
            title=(e.get("title") or "").strip(),
            url=e.get("link") or "",
            date=date,
            source=source,
            category=category,
        ))
    log.info("gnews %s/%s -> %d items", news_query, category, len(items))
    return items
