"""Enrich hiring roles: department (from title) + tools/practices (from the full
JD, via skills.extract). No LLM cost; runs on all roles. Nothing is invented.
"""
from __future__ import annotations

from ..store.schema import Role
from . import skills as skills_mod

# department <- keywords in the role title (business-domain buckets from the brief)
_DEPARTMENTS: list[tuple[str, tuple[str, ...]]] = [
    ("Finance", ("finance", "accounting", "controller", "fp&a", "treasury", "audit", "tax")),
    ("Supply Chain", ("supply chain", "logistics", "procurement", "sourcing", "planning", "warehouse", "inventory")),
    ("Clinical / R&D", ("clinical", "r&d", "regulatory affairs", "pharmacovig", "drug safety", "biolog", "chemist", "research scientist", "laboratory", "preclinical")),
    ("Risk & Compliance", ("risk", "compliance", "legal", "governance", "fraud", "aml", "security")),
    ("Manufacturing", ("manufactur", "production", "plant", "quality", "maintenance", "operator", "assembly")),
    ("Commercial & Marketing", ("sales", "marketing", "commercial", "brand", "category", "trade", "account manager", "business development")),
    ("HR & People", ("hr", "human resource", "talent", "recruit", "people", "learning")),
    ("Technology / IT", ("engineer", "developer", "software", "data", "it ", "devops", "cloud", "analyst", "architect", "cyber", "ml", "ai ", "sap", "platform", "qa", "test")),
]


def _department(title: str) -> str:
    t = title.lower()
    for dept, kws in _DEPARTMENTS:
        if any(k in t for k in kws):
            return dept
    return ""


def classify(role: Role) -> Role:
    title = role.role or ""
    if not role.department:
        role.department = _department(title)
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
