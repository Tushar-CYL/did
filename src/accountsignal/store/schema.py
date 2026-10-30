"""Normalized data model — the single source of truth consumed by Excel + UI.

Uses plain dataclasses (stdlib only) so there is no pydantic dependency to
install on the office laptop. `to_dict` / `from_dict` handle (de)serialization.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass(slots=True)
class Role:
    """One open India role (hiring = India only, posted last month)."""
    role: str = ""
    city: str = ""
    region: str = ""               # North / West / South / East / Other
    country: str = "India"
    department: str = ""            # Finance, Supply Chain, Clinical/R&D, ...
    team: str = ""                  # org/sub-team where the posting states it
    tools: list[str] = field(default_factory=list)   # tools/skills from the JD (the intel)
    practices: list[str] = field(default_factory=list)  # practice buckets the tools map to
    skills: list[str] = field(default_factory=list)  # legacy: title-derived skills
    seniority: str = ""             # Executive / Manager-Lead / Senior / Mid / Junior
    experience_years: str = ""      # free text where stated, else ""
    posted_date: str = ""           # ISO date
    days_open: int | None = None    # aging = today - posted_date
    job_id: str = ""
    source_url: str = ""
    description: str = ""           # full JD text (used to extract tools; trimmed in outputs)


@dataclass(slots=True)
class NewsItem:
    title: str = ""
    url: str = ""
    date: str = ""                  # ISO date
    source: str = ""
    category: str = ""              # hiring/vision/partnerships/financial/expansion
    summary: str = ""               # one clean sentence (filled by enrichment)
    _score: float = 0.0             # INTERNAL relevance rank — never rendered


@dataclass(slots=True)
class MarketField:
    summary: str = ""               # clean paragraph, no duplication
    items: list[NewsItem] = field(default_factory=list)


@dataclass(slots=True)
class MarketIntel:
    hiring: MarketField = field(default_factory=MarketField)
    vision: MarketField = field(default_factory=MarketField)
    partnerships: MarketField = field(default_factory=MarketField)
    financial: MarketField = field(default_factory=MarketField)
    expansion: MarketField = field(default_factory=MarketField)


@dataclass(slots=True)
class Signals:
    partnership_signals: list[str] = field(default_factory=list)  # factual partnership news
    vision_shifts: list[str] = field(default_factory=list)        # factual strategy/expansion news
    tool_gravitation: list[str] = field(default_factory=list)     # top tools the company hires for
    insight: list[str] = field(default_factory=list)              # factual "what they're hiring for" bullets


@dataclass(slots=True)
class CompanyRecord:
    company: str = ""
    website: str = ""
    career_url: str = ""
    ats: str | None = None
    sector: str = ""
    run_ts: str = ""
    hiring_india: list[Role] = field(default_factory=list)
    market_intel: MarketIntel = field(default_factory=MarketIntel)
    signals: Signals = field(default_factory=Signals)
    scrape_errors: list[str] = field(default_factory=list)  # what failed (transparency)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    def to_public_dict(self) -> dict[str, Any]:
        """Dashboard payload: strips every internal ranking field (_score)."""
        d = self.to_dict()
        for mf in d.get("market_intel", {}).values():
            for item in mf.get("items", []):
                item.pop("_score", None)
        return d
