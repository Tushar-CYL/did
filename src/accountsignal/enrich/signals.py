"""Per-company factual insight + signals. NO EY editorializing.

Insight = (1) where India hiring concentrates by department, (2) the tools sought
within the top departments (the real intel), (3) concrete expansion / partnership
news. Uses EYQ to tighten the prose when available; deterministic otherwise.
"""
from __future__ import annotations

import json
import logging
from collections import Counter

from ..store.schema import MarketIntel, Role, Signals
from .eyq_client import EYQClient

log = logging.getLogger("accountsignal.enrich.signals")

_SYSTEM = (
    "You are a market-intelligence analyst. Write short, factual, non-duplicated "
    "bullets from the supplied data only. Never invent facts. Do NOT mention EY, "
    "consulting opportunities, or 'managed services' — just state what is happening."
)


def _clean(title: str) -> str:
    return title.split(" - ")[0].strip().rstrip(".") + "."


def _top_tools(roles: list[Role], dept: str | None = None, n: int = 5) -> list[str]:
    c = Counter(t for r in roles if (dept is None or r.department == dept) for t in (r.tools or []))
    return [t for t, _ in c.most_common(n)]


def _factual_insight(company: str, mi: MarketIntel, roles: list[Role]) -> list[str]:
    insight: list[str] = []
    dept_c = Counter(r.department for r in roles if r.department)
    if dept_c:
        tops = dept_c.most_common(3)
        insight.append(
            f"{company}'s India hiring is concentrated in "
            + ", ".join(f"{d} ({n})" for d, n in tops) + "."
        )
        # the key intel: tools sought within the leading departments
        for dept, _ in tops[:2]:
            tools = _top_tools(roles, dept)
            if tools:
                insight.append(f"Within {dept}, postings call for {', '.join(tools)}.")
    # where in India they are hiring
    city_c = Counter(r.city for r in roles if r.city)
    if city_c:
        cities = [c for c, _ in city_c.most_common(3)]
        insight.append("Hiring is concentrated in " + ", ".join(cities) + ".")
    # seniority make-up (manager-and-below emphasis)
    sen_c = Counter(r.seniority for r in roles if r.seniority)
    tot = sum(sen_c.values())
    if tot:
        mb = sum(n for s, n in sen_c.items() if s in ("Junior", "Mid", "Senior", "Manager-Lead", "Manager/Lead"))
        if mb / tot >= 0.6:
            insight.append(f"Roles are mostly manager-level and below ({mb} of {tot}).")
    # concrete expansion / partnership news (factual)
    if mi.expansion.items:
        insight.append(_clean(mi.expansion.items[0].title))
    if mi.partnerships.items:
        insight.append(_clean(mi.partnerships.items[0].title))
    return insight[:7]


def _eyq_insight(client: EYQClient, company: str, mi: MarketIntel, roles: list[Role]) -> list[str]:
    dept_c = Counter(r.department for r in roles if r.department)
    tools_by_dept = {d: _top_tools(roles, d) for d, _ in dept_c.most_common(3)}
    news = {
        "expansion": [i.title for i in mi.expansion.items[:3]],
        "partnerships": [i.title for i in mi.partnerships.items[:3]],
    }
    user = (
        f"Company: {company}\n"
        f"India hiring by department: {dict(dept_c.most_common(5))}\n"
        f"Tools sought per top department: {json.dumps(tools_by_dept)}\n"
        f"Recent news: {json.dumps(news)}\n\n"
        "Return JSON {\"insight\": [ up to 5 short factual bullets ]}: where hiring "
        "concentrates, the tools sought within the top departments, and concrete "
        "expansion/partnership news. No EY / consulting language."
    )
    data = client.chat_json(_SYSTEM, user, max_tokens=400)
    got = data.get("insight") if isinstance(data, dict) else None
    if isinstance(got, list) and got:
        return [str(x).strip() for x in got][:5]
    return _factual_insight(company, mi, roles)


def enrich(company: str, mi: MarketIntel, roles: list[Role], client: EYQClient) -> Signals:
    insight = (_factual_insight(company, mi, roles) if client.mock
               else _eyq_insight(client, company, mi, roles))
    return Signals(
        partnership_signals=[_clean(i.title) for i in mi.partnerships.items[:3]],
        vision_shifts=[_clean(i.title) for i in mi.vision.items[:3]],
        tool_gravitation=_top_tools(roles, None, 8),
        insight=insight,
    )
