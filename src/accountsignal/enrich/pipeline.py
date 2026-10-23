"""Enrichment orchestrator: rank news, write detailed market-intel summaries,
classify hiring, derive strategic signals + EY takeaways. Reads and rewrites the
normalized store so it can run as its own stage (--only enrich)."""
from __future__ import annotations

import logging
from dataclasses import asdict, fields

from ..config import Settings
from ..store import io
from ..store.schema import MarketIntel, NewsItem, Role, Signals
from . import classify_hiring, market_intel, rank, signals
from .eyq_client import EYQClient

log = logging.getLogger("accountsignal.enrich")

_NEWS_FIELDS = {f.name for f in fields(NewsItem)}
_ROLE_FIELDS = {f.name for f in fields(Role)}


def _news_from_dict(d: dict) -> NewsItem:
    return NewsItem(**{k: v for k, v in d.items() if k in _NEWS_FIELDS})


def _role_from_dict(d: dict) -> Role:
    return Role(**{k: v for k, v in d.items() if k in _ROLE_FIELDS})


def enrich_all(settings: Settings, mock: bool = False, companies_filter: list[str] | None = None) -> None:
    client = EYQClient(settings.eyq_endpoint, settings.eyq_key, settings.eyq_model, mock=mock)
    log.info("Enrichment mode: %s", "MOCK" if client.mock else f"EYQ ({settings.eyq_model})")

    data = io.read_json(io.normalized_path())
    for rec in data:
        name = rec["company"]
        if companies_filter and not any(w in name.lower() for w in companies_filter):
            continue

        # 1) reconstruct news, rank (internal), write detailed summaries
        news_by_cat = {cat: [_news_from_dict(x) for x in rec["market_intel"][cat]["items"]]
                       for cat in market_intel.CATEGORIES}
        rank.rank_company_news(news_by_cat, name)
        mi = market_intel.enrich(name, news_by_cat, client)

        # 2) classify hiring roles (department, skills, critical flag)
        roles = [classify_hiring.classify(_role_from_dict(r)) for r in rec["hiring_india"]]

        # 3) strategic signals + EY takeaways
        sig = signals.enrich(name, mi, roles, client)

        # 4) write back
        rec["hiring_india"] = [asdict(r) for r in roles]
        rec["market_intel"] = {cat: {"summary": getattr(mi, cat).summary,
                                      "items": [asdict(i) for i in getattr(mi, cat).items]}
                               for cat in market_intel.CATEGORIES}
        rec["signals"] = asdict(sig)
        log.info("enriched %s (%d roles, %d insight bullets)",
                 name, len(roles), len(sig.insight))

    io.write_json(io.normalized_path(), data)
    log.info("Enrichment complete -> %s", io.normalized_path())
