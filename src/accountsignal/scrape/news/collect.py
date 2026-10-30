"""Collect + dedupe market-intelligence news for a company across all 5 fields.

Relevance model (driven by what BD actually needs):
  * drop stock-market chatter outright (price targets, share purchases, ratings);
  * a "strong" term is on-theme by itself (GCC, capability centre, cost cutting,
    job cuts);
  * a "weak" term (expansion, partnership, deal, investment) only counts when the
    title also carries tech/capability context -- otherwise ordinary retail news
    ("new excitement to meal deals") would masquerade as a tech signal.
Each unique article lands in the single category it fits best.
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

# --- stock-market chatter: never a BD signal -------------------------------
_NOISE_TITLE = re.compile(
    r"price target|analyst|\bshares?\b|holdings in|short interest|(buy|sell|hold) rating|"
    r"outperform|underweight|overweight|market cap|dividend|\bEPS\b|\bstock\b|"
    r"\$[A-Z]{1,5}\b|stake (in|raised|lowered)|position (in|boosted|lowered|trimmed)",
    re.I)
_NOISE_SOURCES = ("marketbeat", "zacks", "simply wall st", "defense world", "etf daily news",
                  "traders union", "insider monkey", "tipranks", "barchart", "stocktwits",
                  "investing.com", "gurufocus", "benzinga")

# --- tech / capability context required by the weak terms ------------------
_TECH_CTX = ("technolog", "tech ", "tech-", "digital", "cloud", "ai ", "artificial intelligence",
             "data ", "software", " it ", "platform", "automation", "sap", "erp", "cyber",
             "engineering", "r&d", "capability cent", "gcc", "innovation", "analytics",
             "machine learning", "genai", "modernis", "moderniz", "centre", "center",
             "campus", "facility", "digitis", "digitiz")

# strong: on-theme alone. weak: only counted when tech context is present.
_STRONG: dict[str, tuple[str, ...]] = {
    "expansion": ("global capability cent", "capability cent", "gcc", "technology cent",
                  "tech cent", "r&d cent", "development cent", "innovation cent",
                  "engineering cent", "delivery cent", "global in-house", "new campus",
                  "new facility", "new plant", "offshore cent"),
    "vision": ("digital transformation", "cloud migration", "technology roadmap", "modernis",
               "moderniz", "erp implementation", "sap implementation", "automation initiative",
               "digital overhaul", "tech overhaul"),
    "partnerships": ("technology partnership", "tech partnership", "strategic alliance",
                     "joint venture", "technology tie-up", "digital partnership"),
    "financial": ("cost cutting", "cost cut", "cost reduction", "cost savings",
                  "technology investment", "tech investment", "capex", "cost optimisation",
                  "cost optimization"),
    "hiring": ("job cuts", "jobs cut", "cut jobs", "cutting jobs", "slash jobs", "job losses",
               "layoff", "lay off", "redundanc", "workforce reduction", "workforce",
               "new jobs", "job addition", "adding jobs", "create jobs", "creates jobs",
               "hiring spree", "headcount", "staff cuts", "downsiz", r"\bjobs\b"),
}
_WEAK: dict[str, tuple[str, ...]] = {
    "expansion": ("expansion", "expand", "opens", "sets up", "set up", "new office"),
    "vision": ("transformation", "restructur", "overhaul", "revamp", "big project",
               "strategic initiative"),
    "partnerships": ("partnership", "partner", "alliance", "collaborat", "tie-up", "deal"),
    "financial": ("investment", "invests", "funding", "acquisition", "acquire"),
    "hiring": ("hiring", "recruit", "talent"),
}


def _is_noise(item: NewsItem) -> bool:
    if _NOISE_TITLE.search(item.title or ""):
        return True
    src = (item.source or "").lower()
    return any(k in src for k in _NOISE_SOURCES)


def _norm_title(t: str) -> str:
    t = re.sub(r"\s+-\s+[^-]+$", "", t)          # drop trailing " - Source"
    t = re.sub(r"[^a-z0-9]+", " ", t.lower())
    return t.strip()


def _hits(lc: str, terms: tuple[str, ...]) -> int:
    n = 0
    for t in terms:
        if t.startswith("\\b"):
            if re.search(t, lc):
                n += 1
        elif t in lc:
            n += 1
    return n


# Only these themes demand tech context for their generic terms: the manager asked
# for *tech* partnerships, *tech centre* expansion and transformation initiatives.
# Cost cuts and job adds/cuts are wanted whatever the wording (stock chatter is
# already removed by _is_noise, so relaxing these does not readmit junk).
_NEEDS_TECH = {"partnerships", "vision", "expansion"}


def _best_category(title: str, fetched: str) -> str:
    """Best-fit theme, or "" when nothing on-theme matched (caller drops it)."""
    lc = (title or "").lower()
    tech = any(c in lc for c in _TECH_CTX)
    best, best_score = "", 0
    for cat in CATEGORIES:
        score = 2 * _hits(lc, _STRONG[cat])
        if tech or cat not in _NEEDS_TECH:
            score += _hits(lc, _WEAK[cat])
        if score > best_score:
            best, best_score = cat, score
    return best


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


def _gather(news_query: str, http: Http, lookback_days: int, quoted: bool,
            gate: bool = True) -> dict[str, NewsItem]:
    seen: dict[str, NewsItem] = {}
    for cat in CATEGORIES:
        for item in gnews.fetch_category(news_query, cat, http, lookback_days, quoted=quoted):
            key = _norm_title(item.title)
            if not key or key in seen:
                continue
            if _is_noise(item):
                continue  # stock chatter is never relevant, gate or no gate
            best = _best_category(item.title, cat)
            if not best:
                if gate:
                    continue  # relevance gate: nothing on-theme in the title
                best = cat
            item.category = best
            seen[key] = item
    return seen


def collect(news_query: str, http: Http, lookback_days: int = 30) -> dict[str, list[NewsItem]]:
    """Return {category: [NewsItem]} -- unique, on-theme articles, most recent first."""
    seen = _gather(news_query, http, lookback_days, quoted=True)
    # An exact-phrase query with a legal suffix ("BP plc", "Adobe Inc") matches very
    # few headlines, so top up from the unquoted query whenever the result is thin.
    if len(seen) < 6:
        log.info("news: '%s' thin (%d) with exact phrase; topping up unquoted",
                 news_query, len(seen))
        seen.update(_gather(news_query, http, lookback_days, quoted=False))
    if not seen:
        # last resort so no tracked company shows zero news: drop the theme gate
        log.info("news: '%s' empty after theme gate; retrying ungated", news_query)
        seen = _gather(news_query, http, lookback_days, quoted=True, gate=False)
        if not seen:
            seen = _gather(news_query, http, lookback_days, quoted=False, gate=False)

    # relevance: keep only items that actually name the company
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
