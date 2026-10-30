"""Enrich hiring roles: department (from title) + tools/practices (from the full
JD, via skills.extract). No LLM cost; runs on all roles. Nothing is invented.
"""
from __future__ import annotations

import re

from ..store.schema import Role
from . import skills as skills_mod

# canonical Indian city spellings so counts/insights don't split the same city
_CITY_ALIAS = {
    "bangalore": "Bengaluru", "bengaluru": "Bengaluru", "bangaluru": "Bengaluru",
    "gurgaon": "Gurugram", "gurugram": "Gurugram", "bombay": "Mumbai",
    "calcutta": "Kolkata", "madras": "Chennai", "new delhi": "Delhi",
    "trivandrum": "Thiruvananthapuram", "cochin": "Kochi",
}


# macro-region buckets (leadership view: North / West / South / East)
_MACRO_REGION = {
    "North": ("delhi", "gurugram", "gurgaon", "noida", "chandigarh", "jaipur", "ncr",
              "faridabad", "ghaziabad"),
    "West": ("mumbai", "pune", "ahmedabad", "gandhinagar", "nagpur", "surat", "goa", "thane"),
    "South": ("bengaluru", "bangalore", "hyderabad", "chennai", "coimbatore", "kochi",
              "mysuru", "mysore", "kakinada", "vijayawada", "thiruvananthapuram", "madurai"),
    "East": ("kolkata", "bhubaneswar", "patna", "guwahati", "ranchi"),
}


def _macro_region(city: str) -> str:
    c = (city or "").lower()
    for region, keys in _MACRO_REGION.items():
        if any(k in c for k in keys):
            return region
    return "Other"


def _canon_city(city: str) -> str:
    """Leading city token, canonical spelling (drops any address tail)."""
    if not city:
        return ""
    head = re.split(r"[,/]", str(city).strip())[0].strip()
    key = head.lower()
    if key in _CITY_ALIAS:
        return _CITY_ALIAS[key]
    for alias, canon in _CITY_ALIAS.items():
        if alias in key:
            return canon
    return head.title() if (head.islower() or head.isupper()) else head

# department <- keywords in the role title (business-domain buckets from the brief)
_DEPARTMENTS: list[tuple[str, tuple[str, ...]]] = [
    ("Finance", ("finance", "accounting", "controller", "fp&a", "treasury", "audit", "tax", "cost ", "costing", "pricing", "price book")),
    ("Supply Chain", ("supply chain", "logistics", "logistique", "procurement", "sourcing", "planning", "warehouse", "inventory", "vmi")),
    ("Clinical / R&D", ("clinical", "r&d", "regulatory affairs", "pharmacovig", "drug safety", "biolog", "chemist", "research", "scientist", "laboratory", "preclinical", "geolog", "innovation", "science")),
    ("Risk & Compliance", ("risk", "compliance", "legal", "governance", "fraud", "aml", "security")),
    ("Manufacturing", ("manufactur", "production", "plant", "quality", "maintenance", "operator", "assembly")),
    ("Commercial & Marketing", ("sales", "marketing", "commercial", "brand", "category", "trade", "account manager", "business development", "activation")),
    ("HR & People", ("hr", "human resource", "talent", "recruit", "people", "learning", "reward", "compensation", "benchmarking", "payroll")),
    ("Operations & PMO", ("operations", "operational", "program management", "programme management", "project management", "delivery manager", "delivery lead", "pmo", "coordinator")),
    ("Technology / IT", ("engineer", "developer", "software", "data", "it ", "devops", "cloud", "analyst", "architect", "cyber", "ml", "ai ", "sap", "platform", "qa", "test", "technical", "technology", "application")),
    ("Early Careers", ("trainee", "intern", "apprentice", "graduate", "student")),
]


def _department(title: str) -> str:
    t = title.lower()
    for dept, kws in _DEPARTMENTS:
        if any(k in t for k in kws):
            return dept
    return ""


def classify(role: Role) -> Role:
    title = role.role or ""
    # canonicalize the city (dedupe Bengaluru/Bangalore, strip address tails)
    if role.city:
        role.city = _canon_city(role.city)
    role.region = _macro_region(role.city)
    if not role.department:
        role.department = _department(title)
    # when the title doesn't map to a known bucket, use the ATS-provided job
    # family (the real department name) instead of leaving it blank -> "Other".
    if not role.department and (role.team or "").strip():
        role.department = role.team.strip()
    # tools/practices are the intel: scan the full JD + title
    text = f"{role.description or ''} {title}"
    tools, practices = skills_mod.extract(text)
    role.tools = tools
    role.practices = practices
    role.skills = tools  # keep legacy `skills` aligned to extracted tools
    # clamp impossible future dates (some portals return a valid-through date):
    # a posting cannot have negative aging.
    if role.days_open is not None and role.days_open < 0:
        from datetime import date
        role.days_open = 0
        role.posted_date = date.today().isoformat()
    return role
