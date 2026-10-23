"""Turn ranked headlines into clean, detailed, de-duplicated market-intelligence
summaries per category. Uses EYQ when available; otherwise a deterministic mock
that composes readable sentences from the top headlines."""
from __future__ import annotations

import logging

from ..store.schema import MarketField, MarketIntel, NewsItem
from .eyq_client import EYQClient

log = logging.getLogger("accountsignal.enrich.market_intel")

CATEGORIES = ("hiring", "vision", "partnerships", "financial", "expansion")
_LABEL = {
    "hiring": "workforce & recruitment",
    "vision": "strategy & leadership",
    "partnerships": "partnerships & alliances",
    "financial": "financial performance",
    "expansion": "expansion & investment",
}
_KEEP = 8  # items retained per category after ranking

_SYSTEM = (
    "You are a market-intelligence analyst. Write clean, factual, non-duplicated "
    "prose from the supplied headlines only; never invent facts. Keep sentences "
    "straight and readable. Do NOT mention EY, consulting, or 'managed services'."
)


def _mock_summary(category: str, items: list[NewsItem], company: str) -> str:
    if not items:
        return ""
    heads = []
    seen = set()
    for it in items[:4]:
        h = it.title.split(" - ")[0].strip()
        key = h.lower()
        if key in seen:
            continue
        seen.add(key)
        heads.append(h)
    label = _LABEL[category]
    lead = f"Recent {label} developments at {company} (last month): "
    return lead + "; ".join(heads) + "."


def _eyq_summary(client: EYQClient, category: str, items: list[NewsItem], company: str) -> str:
    bullets = "\n".join(f"- {it.title} ({it.date}, {it.source})" for it in items[:_KEEP])
    user = (
        f"Company: {company}\nCategory: {_LABEL[category]} (GLOBAL, last month)\n"
        f"Headlines:\n{bullets}\n\n"
        "Write 2-4 sentences summarizing the key developments in this category. "
        "No duplication across sentences. Be specific and factual."
    )
    try:
        text = client.chat_text(_SYSTEM, user, max_tokens=300)
        return text.strip() or _mock_summary(category, items, company)
    except Exception as exc:
        log.info("eyq summary failed (%s/%s): %s", company, category, exc)
        return _mock_summary(category, items, company)


def enrich(company: str, news_by_cat: dict[str, list[NewsItem]], client: EYQClient) -> MarketIntel:
    mi = MarketIntel()
    for cat in CATEGORIES:
        items = news_by_cat.get(cat, [])[:_KEEP]
        summary = _mock_summary(cat, items, company) if client.mock else _eyq_summary(client, cat, items, company)
        setattr(mi, cat, MarketField(summary=summary, items=items))
    return mi
