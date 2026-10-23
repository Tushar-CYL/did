"""ATS (Applicant Tracking System) fingerprinting.

Given a careers URL we follow redirects and inspect the final URL + HTML for
known platform signatures. Knowing the ATS lets us call its public JSON API
directly (fast, stable, free) instead of scraping rendered HTML.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from urllib.parse import urlparse

from ...http import Http

# host-substring -> ats id  (checked against the FINAL url after redirects)
_HOST_SIGNATURES: list[tuple[str, str]] = [
    ("myworkdayjobs.com", "workday"),
    ("myworkdaysite.com", "workday"),
    ("greenhouse.io", "greenhouse"),
    ("smartrecruiters.com", "smartrecruiters"),
    ("eightfold.ai", "eightfold"),
    ("phenompeople.com", "phenom"),
    ("icims.com", "icims"),
    ("taleo.net", "taleo"),
    ("oraclecloud.com", "oracle_cloud"),
    ("avature.net", "avature"),
    ("lever.co", "lever"),
    ("ashbyhq.com", "ashby"),
    ("successfactors.com", "successfactors"),
    ("successfactors.eu", "successfactors"),
    ("workable.com", "workable"),
]

# html-body substrings -> ats id (checked when host is inconclusive, e.g. the
# careers page is a custom domain that embeds the ATS)
_BODY_SIGNATURES: list[tuple[str, str]] = [
    ("myworkdayjobs.com", "workday"),
    ("boards.greenhouse.io", "greenhouse"),
    ("job-boards.greenhouse.io", "greenhouse"),
    ("smartrecruiters.com", "smartrecruiters"),
    ("eightfold.ai", "eightfold"),
    ("phenompeople.com", "phenom"),
    ("phApplication", "phenom"),
    (".icims.com", "icims"),
    ("oraclecloud.com", "oracle_cloud"),
    ("avature.net", "avature"),
    ("successfactors", "successfactors"),
    ("jobs.lever.co", "lever"),
]


@dataclass(slots=True)
class Detection:
    ats: str | None
    final_url: str
    tenant: str | None = None   # extracted ATS tenant/board token where possible
    note: str = ""


def _tenant_from_url(ats: str, url: str) -> str | None:
    host = urlparse(url).netloc
    path = urlparse(url).path
    if ats == "workday":
        # e.g. takeda.wd3.myworkdayjobs.com  or  *.myworkdaysite.com
        m = re.match(r"^([^.]+)\.(wd\d+)\.", host)
        if m:
            return f"{m.group(1)}|{m.group(2)}"
    if ats == "greenhouse":
        m = re.search(r"greenhouse\.io/(?:embed/job_board\?for=)?([A-Za-z0-9_-]+)", url)
        if m:
            return m.group(1)
        m = re.search(r"greenhouse\.io/([A-Za-z0-9_-]+)", url)
        if m:
            return m.group(1)
    if ats == "smartrecruiters":
        m = re.search(r"smartrecruiters\.com/([A-Za-z0-9_-]+)", url)
        if m:
            return m.group(1)
    if ats in ("eightfold", "phenom", "icims"):
        m = re.match(r"^([^.]+)\.", host)
        if m:
            return m.group(1)
    if ats == "lever":
        m = re.search(r"lever\.co/([A-Za-z0-9_-]+)", url)
        if m:
            return m.group(1)
    return None


def detect(career_url: str, http: Http) -> Detection:
    if not career_url:
        return Detection(ats=None, final_url="", note="no career_url")
    resp = http.get(career_url, allow_redirects=True)
    if resp is None:
        return Detection(ats=None, final_url=career_url, note="unreachable")
    final = str(resp.url)
    # 1) host signatures on the final (post-redirect) URL
    for sub, ats in _HOST_SIGNATURES:
        if sub in final:
            return Detection(ats=ats, final_url=final, tenant=_tenant_from_url(ats, final))
    # 2) body signatures
    body = resp.text or ""
    body_lc = body.lower()
    for sub, ats in _BODY_SIGNATURES:
        if sub.lower() in body_lc:
            # try to pull a concrete embed URL to extract tenant
            m = re.search(r"https?://[^\"'\s]*" + re.escape(sub) + r"[^\"'\s]*", body)
            probe = m.group(0) if m else final
            return Detection(ats=ats, final_url=final, tenant=_tenant_from_url(ats, probe), note="body")
    return Detection(ats="custom", final_url=final, note="no known signature")
