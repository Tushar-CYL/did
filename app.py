#!/usr/bin/env python
"""
AccountSignal — ONE-CLICK RUNNER
================================
Runs the whole automation end to end:

    scrape (India hiring + global news)  ->  rank + enrich (reports)
        ->  Excel (Power BI)  ->  dashboard  ->  webapp data

Usage (from this folder):

    python app.py                 # full run: re-scrape everything, then build all reports
    python app.py --skip-scrape   # reuse last scrape; just rebuild reports/Excel/UI (fast)
    python app.py --eyq           # use the real EY LLM (EYQ) for the write-ups
    python app.py --companies "TIAA,GSK"   # only these accounts
    python app.py --no-open       # don't open the dashboard in a browser at the end

Defaults: full scrape + mock write-ups (no EYQ calls). Add --eyq on the office
laptop (or wherever the EYQ endpoint is reachable) for richer prose.
"""
from __future__ import annotations

import argparse
import sys
import time
import webbrowser
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "src"))  # run without `pip install -e .`


def _banner(text: str) -> None:
    line = "=" * 64
    print(f"\n{line}\n  {text}\n{line}", flush=True)


def main() -> int:
    ap = argparse.ArgumentParser(description="AccountSignal one-click runner")
    ap.add_argument("--skip-scrape", action="store_true", help="reuse last scrape; rebuild reports only")
    ap.add_argument("--eyq", action="store_true", help="use the real EY LLM (EYQ) for write-ups")
    ap.add_argument("--companies", help="comma-separated subset of accounts")
    ap.add_argument("--no-open", action="store_true", help="do not open the dashboard at the end")
    args = ap.parse_args()

    # Build the argv for the core pipeline (accountsignal.run)
    run_argv: list[str] = []
    if args.skip_scrape:
        run_argv.append("--skip-scrape")
    if not args.eyq:
        run_argv.append("--mock-llm")          # default: no EYQ calls
    if args.companies:
        run_argv += ["--companies", args.companies]

    _banner("AccountSignal — EY India Account Intelligence Engine")
    print("  Stages : scrape -> rank/enrich -> Excel -> dashboard -> webapp")
    print(f"  Mode   : {'RE-SCRAPE' if not args.skip_scrape else 'SKIP SCRAPE (reuse data)'} | "
          f"LLM: {'EYQ (real)' if args.eyq else 'mock'}"
          + (f" | accounts: {args.companies}" if args.companies else " | all 50 accounts"))
    if not args.skip_scrape:
        print("  Note   : a full scrape renders many career sites + calls Apify; "
              "allow ~15-30 min and a few $ of Apify credit.")

    from accountsignal.run import main as run_main
    from accountsignal import config
    from accountsignal.store import io

    t0 = time.time()
    rc = run_main(run_argv)
    if rc != 0:
        print("\nPipeline reported a non-zero exit code.", flush=True)
        return rc

    # ---- final summary ----
    _banner("DONE")
    try:
        data = io.read_json(io.normalized_path())
        cats = ("hiring", "vision", "partnerships", "financial", "expansion")
        roles = sum(len(c["hiring_india"]) for c in data)
        with_roles = sum(1 for c in data if c["hiring_india"])
        news = sum(len(c["market_intel"][k]["items"]) for c in data for k in cats)
        print(f"  Accounts        : {len(data)}")
        print(f"  India roles     : {roles}  (across {with_roles} accounts)")
        print(f"  News items kept : {news}")
    except Exception as exc:
        print(f"  (could not read summary: {exc})")

    xlsx = sorted(config.OUT_DIR.glob("AccountSignal_*.xlsx"))
    dash = config.DASHBOARD_DIR / "index.html"
    print("\n  Outputs:")
    if xlsx:
        print(f"   - Excel (Power BI) : {xlsx[-1]}")
    print(f"   - Dashboard        : {dash}")
    print(f"   - Webapp data      : {config.WEBAPP_DATA}")
    print(f"   - Source of truth  : {io.normalized_path()}")
    print("\n  Webapp: run  python webapp/serve_nocache.py  then open http://localhost:3000")

    if not args.no_open and dash.exists():
        try:
            webbrowser.open(dash.resolve().as_uri())
        except Exception:
            pass

    print(f"\n  Total time: {time.time() - t0:0.0f}s\n", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
