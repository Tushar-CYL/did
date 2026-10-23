"""Hiring adapter interface + shared helpers (India filter, date parsing)."""
from __future__ import annotations

import re
from datetime import date, datetime, timedelta

from ...store.schema import Role

# Indian cities (word-boundary matched). NOTE: "india"/"ind"/"in:" handled
# separately via regex so we never false-match "Indiana" / "Indianapolis".
_INDIA_CITIES = (
    "bengaluru", "bangalore", "mumbai", "pune", "gurgaon", "gurugram",
    "hyderabad", "chennai", "new delhi", "delhi", "noida", "kolkata", "ahmedabad",
    "jaipur", "chandigarh", "kochi", "cochin", "coimbatore", "indore", "nagpur",
    "vadodara", "mysuru", "mysore", "thiruvananthapuram", "visakhapatnam",
)
# country signals: whole-word "india"/"ind", or "IN:" / ", IND" style codes.
_INDIA_COUNTRY = re.compile(r"\bindia\b|\bind\b|\bin:|,\s*ind\b", re.IGNORECASE)
# explicit guard against US "Indiana" false positives
_NOT_INDIA = re.compile(r"\bindiana\b|indianapolis", re.IGNORECASE)


def is_india(location: str) -> bool:
    if not location:
        return False
    lc = location.lower()
    if _NOT_INDIA.search(lc) and not _INDIA_COUNTRY.search(lc):
        return False
    if _INDIA_COUNTRY.search(lc):
        return True
    return any(re.search(r"\b" + re.escape(c) + r"\b", lc) for c in _INDIA_CITIES)


def india_city(location: str) -> str:
    """Best-effort city extraction from a location string."""
    if not location:
        return ""
    lc = location.lower()
    for c in _INDIA_CITIES:
        if re.search(r"\b" + re.escape(c) + r"\b", lc):
            return c.title()
    # fall back to first comma-separated token
    return location.split(",")[0].strip()


def parse_relative_posted(text: str, today: date | None = None) -> tuple[str, int | None]:
    """'Posted 5 Days Ago' -> (iso_date, days_open). Handles Today/Yesterday/30+."""
    today = today or date.today()
    if not text:
        return "", None
    t = text.lower()
    if "today" in t or "just posted" in t:
        d = 0
    elif "yesterday" in t:
        d = 1
    else:
        m = re.search(r"(\d+)\s*\+?\s*day", t)
        if m:
            d = int(m.group(1))
        else:
            m = re.search(r"(\d+)\s*\+?\s*month", t)
            d = int(m.group(1)) * 30 if m else None
    if d is None:
        return "", None
    return (today - timedelta(days=d)).isoformat(), d


def within_lookback(days_open: int | None, lookback_days: int) -> bool:
    """Keep role if we cannot date it (None) OR it is within the window."""
    if days_open is None:
        return True
    return days_open <= lookback_days


def guess_seniority(title: str) -> str:
    t = (title or "").lower()
    if any(w in t for w in ("chief", "vp ", "vice president", "head of", "director", "president")):
        return "Executive"
    if any(w in t for w in ("manager", "lead", "principal")):
        return "Manager-Lead"
    if any(w in t for w in ("senior", "sr.", "sr ", "staff")):
        return "Senior"
    if any(w in t for w in ("intern", "trainee", "graduate", "apprentice", "junior", "jr.")):
        return "Junior"
    return "Mid"
