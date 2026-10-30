"""Transform the normalized store into the Next.js webapp's v2 data.json.

v2 lens: industry sector -> tech practice -> location -> company -> department
-> tools. The intel is the TOOLS hired for inside each department. No critical /
priority / employment-type / manager fields; no EY editorializing.
"""
from __future__ import annotations

import logging
import re
from collections import Counter, defaultdict
from datetime import date
from pathlib import Path

from .. import config
from ..enrich.skills import PRACTICES
from ..store import io

log = logging.getLogger("accountsignal.output.webapp")

CATS = ("hiring", "vision", "partnerships", "financial", "expansion")
_FIELD_KEY = {"hiring": "hiring", "vision": "vision_strategy", "partnerships": "partnerships",
              "financial": "money_metrics", "expansion": "expansion"}
_FIELD_LABELS = {"hiring": "Hiring", "vision_strategy": "Vision & strategy",
                 "partnerships": "Partnerships", "money_metrics": "Financial performance",
                 "expansion": "Expansion"}
_NEWS_LABEL = {"expansion": "GCC & tech centres", "vision": "Transformation & projects",
               "partnerships": "Tech partnerships & alliances", "financial": "Cost & investment",
               "hiring": "Jobs: adds & cuts"}
_REGIONS = {"BLR": "Bengaluru", "NCR": "Delhi NCR", "West": "Mumbai / Pune",
            "Hyd": "Hyderabad", "South": "Chennai / South", "": "Other India"}
_SENIORITY = {"Manager-Lead": "Manager/Lead"}


def _slug(name: str) -> str:
    s = name.lower().replace("&", " and ")
    return re.sub(r"[^a-z0-9]+", "-", s).strip("-")


def _counts(c: Counter, n: int | None = None) -> list[list]:
    items = c.most_common(n)
    return [[k, v] for k, v in items]


# canonicalize Indian city spellings so counts don't split (Bangalore vs Bengaluru)
_CITY_ALIAS = {
    "bangalore": "Bengaluru", "bengaluru": "Bengaluru", "bangaluru": "Bengaluru",
    "gurgaon": "Gurugram", "gurugram": "Gurugram",
    "bombay": "Mumbai", "mumbai": "Mumbai",
    "calcutta": "Kolkata", "kolkata": "Kolkata",
    "madras": "Chennai", "chennai": "Chennai",
    "new delhi": "Delhi", "delhi": "Delhi",
    "noida": "Noida", "pune": "Pune", "hyderabad": "Hyderabad",
    "gurgaon/gurugram": "Gurugram",
}


# macro-region buckets for the leadership view (North / West / South / East)
_MACRO_REGION = {
    "North": ("delhi", "gurugram", "gurgaon", "noida", "chandigarh", "jaipur", "ncr", "faridabad", "ghaziabad"),
    "West": ("mumbai", "pune", "ahmedabad", "gandhinagar", "nagpur", "surat", "goa"),
    "South": ("bengaluru", "bangalore", "hyderabad", "chennai", "coimbatore", "kochi", "cochin",
              "mysuru", "mysore", "gandipet", "bikkanahalli", "hosahalli", "kakinada", "vijayawada", "trivandrum"),
    "East": ("kolkata", "bhubaneswar", "patna", "guwahati", "ranchi"),
}


def _macro_region(city: str) -> str:
    c = (city or "").lower()
    for region, keys in _MACRO_REGION.items():
        if any(k in c for k in keys):
            return region
    return "Other"


def _norm_city(city: str) -> str:
    """Canonical city label: strip state/country suffixes, unify known spellings."""
    if not city:
        return ""
    head = re.split(r"[,/]", city.strip())[0].strip()
    key = head.lower()
    if key in _CITY_ALIAS:
        return _CITY_ALIAS[key]
    for alias, canon in _CITY_ALIAS.items():
        if alias in key:
            return canon
    return head.title() if head.islower() or head.isupper() else head


def _region(city_counts: Counter) -> str:
    if not city_counts:
        return ""
    top = city_counts.most_common(1)[0][0].lower()
    if any(x in top for x in ("bengaluru", "bangalore")):
        return "BLR"
    if "hyderabad" in top:
        return "Hyd"
    if any(x in top for x in ("mumbai", "pune")):
        return "West"
    if any(x in top for x in ("delhi", "gurgaon", "gurugram", "noida")):
        return "NCR"
    if any(x in top for x in ("chennai", "bangalore", "coimbatore")):
        return "South"
    return ""


def _build_company(rec: dict, sector_map: dict[str, str]) -> tuple[dict, list[dict]]:
    name = rec["company"]
    slug = _slug(name)
    sig = rec.get("signals", {})
    mi = rec["market_intel"]

    roles: list[dict] = []
    dept_c, tool_c, prac_c, sen_c, loc_c, reg_c = (
        Counter(), Counter(), Counter(), Counter(), Counter(), Counter())
    for r in rec.get("hiring_india", []):
        dept = r.get("department", "") or "Other"
        sen = _SENIORITY.get(r.get("seniority", ""), r.get("seniority", "")) or "Mid"
        city = _norm_city(r.get("city", "") or "")
        region = r.get("region") or _macro_region(city)   # prefer the enriched value
        tools = r.get("tools", []) or []
        practices = r.get("practices", []) or []
        roles.append({
            "role_title": r.get("role", ""), "department": dept, "team": r.get("team", ""),
            "seniority": sen, "tools": tools, "practices": practices, "city": city,
            "region": region,
            "location": (city + ", India") if city else "India",
            "posted_date": r.get("posted_date", ""), "aging_days": r.get("days_open"),
            "source_url": r.get("source_url", ""),
        })
        dept_c[dept] += 1
        sen_c[sen] += 1
        if city:
            loc_c[city] += 1
        reg_c[region] += 1
        for t in tools:
            tool_c[t] += 1
        for p in practices:
            prac_c[p] += 1

    fields = {}
    for cat in CATS:
        f = mi[cat]
        fields[_FIELD_KEY[cat]] = {"summary": f.get("summary", ""),
                                   "sources": [i.get("url", "") for i in f["items"][:3]]}

    # flattened, de-duplicated recent-news feed for the deep dive
    news, seen_n = [], set()
    for cat in CATS:
        for it in mi[cat]["items"][:5]:
            key = (it.get("title") or "")[:80].lower()
            if not key or key in seen_n:
                continue
            seen_n.add(key)
            news.append({"category": _NEWS_LABEL[cat], "title": it.get("title", ""),
                         "url": it.get("url", ""), "date": it.get("date", ""),
                         "source": it.get("source", "")})
    news.sort(key=lambda x: x["date"] or "", reverse=True)
    news = news[:14]

    sector = rec.get("sector") or sector_map.get(name) or "Other"
    company = {
        "slug": slug, "name": name, "sector": sector,
        "region": _region(loc_c), "website": rec.get("website", ""),
        "career_url": rec.get("career_url", ""), "ats": rec.get("ats"),
        "total": len(roles),
        "insight": sig.get("insight", []),
        "partnership_signals": sig.get("partnership_signals", []),
        "vision_shifts": sig.get("vision_shifts", []),
        "practices": _counts(prac_c),              # across tech space (ranked)
        "departments": _counts(dept_c),
        "tools": _counts(tool_c),
        "seniority": _counts(sen_c),
        "locations": _counts(loc_c),
        "region_mix": _counts(reg_c),              # [[North, n], [South, n], ...]
        "macro_region": (reg_c.most_common(1)[0][0] if reg_c else ""),
        "fields": fields,
        "news": news,
    }
    return company, roles


def build(out_path: Path | None = None) -> Path:
    out_path = out_path or config.WEBAPP_DATA
    data = io.read_json(io.normalized_path())
    sector_map = config._load_sectors()
    today = date.today().isoformat()

    companies, roles_by_company, names = [], {}, {}
    sector_roles: dict[str, int] = Counter()
    sector_companies: dict[str, list] = defaultdict(list)
    practice_roles: Counter = Counter()
    city_roles: Counter = Counter()
    # sector x practice demand grid: cell = India roles (across sector companies)
    # whose JD maps to that practice. Rows/cols ranked by total below.
    sector_practice: dict[str, Counter] = defaultdict(Counter)
    # region -> total roles, and region -> accounts hiring there (with counts)
    region_roles: Counter = Counter()
    region_accounts: dict[str, list] = defaultdict(list)

    for rec in data:
        company, roles = _build_company(rec, sector_map)
        slug = company["slug"]
        companies.append(company)
        roles_by_company[slug] = roles
        names[slug] = company["name"]
        sec = company["sector"]
        sector_roles[sec] += company["total"]
        sector_companies[sec].append({"slug": slug, "name": company["name"], "roles": company["total"]})
        for p, n in company["practices"]:
            practice_roles[p] += n
            sector_practice[sec][p] += n
        for city, n in company["locations"]:
            city_roles[city] += n
        for reg, n in company["region_mix"]:
            region_roles[reg] += n
            # status: these are accounts we already track AND that have live India
            # demand -> "Existing". New / White-space are set once the BD target
            # list is supplied (we never fabricate relationship status).
            region_accounts[reg].append({"slug": slug, "name": company["name"],
                                         "sector": sec, "roles": n, "status": "Existing"})

    sectors = [{"name": s, "roles": sector_roles[s],
                "companies": sorted(sector_companies[s], key=lambda x: -x["roles"])}
               for s in sorted(sector_roles, key=lambda s: -sector_roles[s])]
    practices = [{"name": p, "roles": n} for p, n in practice_roles.most_common()]
    locations = [{"city": c, "roles": n} for c, n in city_roles.most_common(12)]
    tech_radar = [{"practice": p, "value": practice_roles.get(p, 0)} for p in PRACTICES]

    # demand_matrix: sectors (rows, by total demand) x practices (cols, by total
    # demand). Each cell is the India-role count mapping to that practice within
    # the sector, so the Summary can show WHERE each capability is being built.
    dm_sectors = [s for s in sorted(sector_practice, key=lambda s: -sum(sector_practice[s].values()))
                  if sum(sector_practice[s].values()) > 0]
    dm_practices = [p for p, _ in practice_roles.most_common() if practice_roles[p] > 0]
    demand_matrix = {
        "sectors": [{"name": s, "total": sum(sector_practice[s].values())} for s in dm_sectors],
        "practices": [{"name": p, "total": practice_roles[p]} for p in dm_practices],
        "cells": [[si, pi, sector_practice[s].get(p, 0)]
                  for si, s in enumerate(dm_sectors)
                  for pi, p in enumerate(dm_practices)],
    }

    # region_summary: North/West/South/East (then Other), each with its total and
    # the accounts hiring there, ranked. Feeds the Summary region chart + table.
    _REGION_ORDER = ["North", "West", "South", "East", "Other"]
    region_summary = [
        {"name": r, "roles": region_roles[r],
         "accounts": sorted(region_accounts[r], key=lambda x: -x["roles"])}
        for r in _REGION_ORDER if region_roles.get(r)
    ]

    totals = {"companies": len(companies), "roles": sum(c["total"] for c in companies),
              "sectors": len(sectors), "with_roles": sum(1 for c in companies if c["total"])}

    payload = {
        "generated": today,
        "month_label": f"India open roles · last 30 days (as of {today})",
        "window": 30, "totals": totals, "names": names, "regions": _REGIONS,
        "field_labels": _FIELD_LABELS,
        "sectors": sectors, "practices": practices, "locations": locations,
        "region_summary": region_summary,
        "demand_matrix": demand_matrix, "tech_radar": tech_radar,
        "companies": companies, "roles_by_company": roles_by_company,
    }

    out_path.parent.mkdir(parents=True, exist_ok=True)
    io.write_json(out_path, payload)
    export_data = config.WEBAPP_DIR / "out" / "data.json"
    if export_data.parent.exists():
        io.write_json(export_data, payload)
    log.info("webapp v2 data.json -> %s (%d companies, %d roles)",
             out_path, len(companies), sum(len(v) for v in roles_by_company.values()))
    return out_path
