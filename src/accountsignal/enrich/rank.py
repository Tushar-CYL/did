"""Internal news relevance ranking. Produces a score per news item used only to
order/select items. The score is NEVER shown in the dashboard (stripped by
CompanyRecord.to_public_dict)."""
from __future__ import annotations

import re
from datetime import date

from ..store.schema import NewsItem

# signals that a headline is substantive market intelligence (not generic noise)
_SIGNAL_WORDS = (
    "acquire", "acquisition", "merger", "partnership", "alliance", "invest",
    "expansion", "launch", "earnings", "revenue", "profit", "results", "ceo",
    "appoint", "strategy", "layoff", "hiring", "facility", "plant", "india",
    "gcc", "capability", "ai", "cloud", "digital", "deal", "contract",
)
_NOISE_WORDS = ("stock", "share price", "buy", "sell", "target price", "rating",
                "best cd", "coupon", "discount", "how to", "vs ", "review")


def _recency_score(iso: str, today: date | None = None) -> float:
    today = today or date.today()
    if not iso:
        return 0.3
    try:
        d = date.fromisoformat(iso)
        age = (today - d).days
        return max(0.0, 1.0 - age / 30.0)  # 1.0 today -> 0.0 at 30 days
    except Exception:
        return 0.3


def score_item(item: NewsItem, company: str) -> float:
    title = (item.title or "").lower()
    comp = company.lower().split()[0]
    score = 0.0
    score += 2.0 if comp in title else 0.0           # names the company
    score += sum(0.4 for w in _SIGNAL_WORDS if w in title)
    score -= sum(0.8 for w in _NOISE_WORDS if w in title)
    score += 1.5 * _recency_score(item.date)
    return round(score, 3)


def rank_company_news(news_by_cat: dict[str, list[NewsItem]], company: str) -> None:
    """Attach _score in place and sort each category best-first."""
    for cat, items in news_by_cat.items():
        for it in items:
            it._score = score_item(it, company)
        items.sort(key=lambda x: x._score, reverse=True)
