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

# category -> OR-group of query terms. Targeted at the signals EY BD cares about:
# GCC / tech-centre expansion, tech investment, cost cuts, job adds & cuts, tech
# partnerships/alliances, transformation initiatives and big projects.
CATEGORY_TERMS: dict[str, str] = {
    # GCC & tech-centre expansion
    "expansion": "\"global capability centre\" OR \"global capability center\" OR GCC OR \"capability centre\" "
                 "OR \"technology centre\" OR \"tech centre\" OR \"technology center\" OR \"R&D centre\" "
                 "OR \"development centre\" OR \"innovation centre\" OR \"new facility\" OR \"new campus\" OR expansion",
    # transformation initiatives & big projects
    "vision": "\"digital transformation\" OR transformation OR modernisation OR modernization OR \"big project\" "
              "OR \"technology roadmap\" OR \"strategic initiative\" OR restructuring OR \"cloud migration\"",
    # tech partnerships & alliances
    "partnerships": "\"technology partnership\" OR partnership OR alliance OR collaboration OR \"joint venture\" "
                    "OR \"tie-up\" OR \"strategic partner\" OR deal",
    # cost cuts & tech investment
    "financial": "\"cost cutting\" OR \"cost cut\" OR \"cost reduction\" OR \"technology investment\" OR invests "
                 "OR investment OR \"capex\" OR funding OR acquisition",
    # job additions & job cuts
    "hiring": "\"new jobs\" OR \"job additions\" OR \"adding jobs\" OR hiring OR \"hiring spree\" OR headcount "
              "OR layoffs OR \"job cuts\" OR \"workforce reduction\"",
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
