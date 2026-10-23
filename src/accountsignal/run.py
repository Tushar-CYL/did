"""AccountSignal — one-command pipeline orchestrator.

    python -m accountsignal.run                 full pipeline
    python -m accountsignal.run --only news     single stage
    python -m accountsignal.run --companies "Tesco,Nike"
    python -m accountsignal.run --mock-llm       build enrichment without EYQ

Phase 1 (this file for now) covers scrape -> store. Enrichment and outputs are
wired in as their modules land; each stage is guarded so partial runs work.
"""
from __future__ import annotations

import argparse
import logging
import sys
from dataclasses import asdict
from datetime import datetime, timezone

from . import config
from .http import Http
from .scrape.hiring.dispatch import scrape_hiring
from .scrape.news import collect as news_collect
from .store import io
from .store.schema import CompanyRecord, MarketField, MarketIntel

log = logging.getLogger("accountsignal.run")


def _setup_logging() -> None:
    try:  # Windows consoles default to cp1252; force UTF-8 so titles print
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")


def _market_intel_from_news(news: dict[str, list]) -> MarketIntel:
    mi = MarketIntel()
    for cat, items in news.items():
        setattr(mi, cat, MarketField(summary="", items=items))
    return mi


def scrape_company(company: config.Company, http: Http, settings: config.Settings,
                   do_hiring: bool, do_news: bool) -> CompanyRecord:
    rec = CompanyRecord(
        company=company.name,
        website=company.website,
        career_url=company.career_url,
        ats=company.ats,
        sector=company.sector,
        run_ts=datetime.now(timezone.utc).isoformat(),
    )
    if do_hiring:
        try:
            roles, ats, note = scrape_hiring(company, http, settings)
            rec.hiring_india = roles
            rec.ats = ats
            rec.scrape_errors.append(f"hiring: {note}")
        except Exception as exc:  # never let one company abort the run
            log.warning("hiring failed for %s: %s", company.name, exc)
            rec.scrape_errors.append(f"hiring: ERROR {exc}")
    if do_news:
        try:
            news = news_collect.collect(company.news_query, http, settings.lookback_days)
            rec.market_intel = _market_intel_from_news(news)
            total = sum(len(v) for v in news.values())
            rec.scrape_errors.append(f"news: {total} items")
        except Exception as exc:
            log.warning("news failed for %s: %s", company.name, exc)
            rec.scrape_errors.append(f"news: ERROR {exc}")
    # persist raw per company (only the stages we actually ran)
    if do_hiring:
        io.write_json(io.raw_path(company.slug, "hiring"), [asdict(r) for r in rec.hiring_india])
    if do_news:
        io.write_json(io.raw_path(company.slug, "news"),
                      {c: [asdict(i) for i in getattr(rec.market_intel, c).items] for c in news_collect.CATEGORIES})
    return rec


def main(argv: list[str] | None = None) -> int:
    _setup_logging()
    p = argparse.ArgumentParser(prog="accountsignal")
    p.add_argument("--only", choices=["hiring", "news", "enrich", "excel", "ui"], help="run a single stage")
    p.add_argument("--companies", help="comma-separated subset by name (substring match)")
    p.add_argument("--mock-llm", action="store_true", help="enrichment without EYQ (testing)")
    p.add_argument("--skip-scrape", action="store_true",
                   help="reuse existing scraped data; run enrich + excel + ui only")
    args = p.parse_args(argv)

    settings = config.load_settings()
    companies = settings.companies
    if args.companies:
        wanted = [w.strip().lower() for w in args.companies.split(",") if w.strip()]
        companies = [c for c in companies if any(w in c.name.lower() for w in wanted)]

    do_hiring = args.only in (None, "hiring")
    do_news = args.only in (None, "news")
    do_enrich = args.only in (None, "enrich")
    do_excel = args.only in (None, "excel")
    do_ui = args.only in (None, "ui")
    if args.skip_scrape:
        do_hiring = do_news = False

    http = Http(timeout=settings.request_timeout)
    records: list[CompanyRecord] = []

    if do_hiring or do_news:
        log.info("Scraping %d companies (hiring=%s, news=%s, lookback=%dd)",
                 len(companies), do_hiring, do_news, settings.lookback_days)
        for i, company in enumerate(companies, 1):
            log.info("[%d/%d] %s", i, len(companies), company.name)
            rec = scrape_company(company, http, settings, do_hiring, do_news)
            records.append(rec)

        # write the normalized single-source-of-truth.
        # For a partial run (--only / --companies) merge into the existing file so
        # a stage can be refreshed without discarding the other stage's data.
        new_dicts = {r.company: r.to_dict() for r in records}
        partial = bool(args.only) or bool(args.companies)
        if partial and io.normalized_path().exists():
            merged = io.read_json(io.normalized_path())
            by_name = {c["company"]: c for c in merged}
            for name, nd in new_dicts.items():
                base_rec = by_name.get(name, nd)
                if do_hiring:
                    base_rec["hiring_india"] = nd["hiring_india"]
                    base_rec["ats"] = nd["ats"]
                if do_news:
                    base_rec["market_intel"] = nd["market_intel"]
                base_rec["run_ts"] = nd["run_ts"]
                base_rec["scrape_errors"] = nd["scrape_errors"]
                by_name[name] = base_rec
            out_list = list(by_name.values())
        else:
            out_list = [r.to_dict() for r in records]
        io.write_json(io.normalized_path(), out_list)
        log.info("Wrote %s (%d companies)", io.normalized_path(), len(out_list))

        hires = sum(len(r.hiring_india) for r in records)
        news_tot = sum(sum(len(getattr(r.market_intel, c).items) for c in news_collect.CATEGORIES) for r in records)
        log.info("DONE scrape: %d India roles, %d news items across %d companies", hires, news_tot, len(records))
        if do_hiring:
            from .scrape.hiring import apify_jobs
            log.info("Apify spend this run: $%.2f", apify_jobs.spent_this_run())

    if do_enrich:
        from .enrich.pipeline import enrich_all
        cf = [w.strip().lower() for w in args.companies.split(",")] if args.companies else None
        enrich_all(settings, mock=args.mock_llm, companies_filter=cf)

    if do_excel:
        from .output.excel import build as build_excel
        build_excel()

    if do_ui:
        from .output.dashboard import build as build_dashboard
        from .output.webapp import build as build_webapp
        build_dashboard()
        build_webapp()  # feeds the Next.js webapp (webapp/public/data.json)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
