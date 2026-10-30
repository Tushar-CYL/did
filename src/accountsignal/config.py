"""Configuration & paths. Everything resolves relative to the repo root so the
whole folder is portable (copy to the office laptop, re-create .env, run)."""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

import yaml
from dotenv import load_dotenv

# repo root = three levels up from this file: src/accountsignal/config.py -> repo
ROOT = Path(__file__).resolve().parents[2]
CONFIG_DIR = ROOT / "config"
DATA_DIR = ROOT / "data"
RAW_DIR = DATA_DIR / "raw"
NORMALIZED_DIR = DATA_DIR / "normalized"
OUT_DIR = ROOT / "out"
DASHBOARD_DIR = OUT_DIR / "dashboard"
WEBAPP_DIR = ROOT / "webapp"
WEBAPP_DATA = WEBAPP_DIR / "public" / "data.json"

load_dotenv(ROOT / ".env")


@dataclass(slots=True)
class Company:
    name: str
    website: str = ""
    career_url: str = ""
    ats: str | None = None
    news_query: str = ""
    ticker: str | None = None
    sector: str = ""

    @property
    def slug(self) -> str:
        """Filesystem-safe id, e.g. 'Procter & Gamble' -> 'procter-and-gamble'."""
        s = self.name.lower().replace("&", " and ")
        out = []
        for ch in s:
            out.append(ch if ch.isalnum() else "-")
        slug = "".join(out)
        while "--" in slug:
            slug = slug.replace("--", "-")
        return slug.strip("-")


@dataclass(slots=True)
class Settings:
    lookback_days: int = 30          # hiring window
    news_lookback_days: int = 120    # news window (4 months)
    request_timeout: int = 30
    eyq_endpoint: str = ""
    eyq_key: str = ""
    eyq_model: str = "gpt-5.2"
    apify_token: str = ""
    apify_max_usd: float = 4.5          # hard spend guard for the free $5 tier
    apify_max_items: int = 15           # India jobs per company via Apify
    companies: list[Company] = field(default_factory=list)


def _load_sectors() -> dict[str, str]:
    p = CONFIG_DIR / "sectors.yaml"
    if not p.exists():
        return {}
    data = yaml.safe_load(p.read_text(encoding="utf-8")) or {}
    return data.get("sectors", {}) or {}


def load_companies(path: Path | None = None) -> list[Company]:
    path = path or (CONFIG_DIR / "companies.yaml")
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    sectors = _load_sectors()
    out: list[Company] = []
    for row in data.get("companies", []):
        name = row["name"]
        out.append(Company(
            name=name,
            website=row.get("website") or "",
            career_url=row.get("career_url") or "",
            ats=row.get("ats"),
            news_query=row.get("news_query") or name,
            ticker=row.get("ticker"),
            sector=row.get("sector") or sectors.get(name, "Other"),
        ))
    return out


def load_settings() -> Settings:
    return Settings(
        lookback_days=int(os.getenv("ACCOUNTSIGNAL_LOOKBACK_DAYS", "30")),
        news_lookback_days=int(os.getenv("ACCOUNTSIGNAL_NEWS_LOOKBACK_DAYS", "120")),
        request_timeout=int(os.getenv("ACCOUNTSIGNAL_REQUEST_TIMEOUT", "30")),
        eyq_endpoint=os.getenv("EYQ_INCUBATOR_ENDPOINT", "").rstrip("/"),
        eyq_key=os.getenv("EYQ_INCUBATOR_KEY", ""),
        eyq_model=os.getenv("EYQ_MODEL", "gpt-5.2"),
        apify_token=os.getenv("APIFY_TOKEN", ""),
        apify_max_usd=float(os.getenv("APIFY_MAX_USD", "4.5")),
        apify_max_items=int(os.getenv("APIFY_MAX_ITEMS", "15")),
        companies=load_companies(),
    )
