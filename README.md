# AccountSignal — EY India Account Intelligence Engine

One command scrapes **India hiring** (India only, last month) + **global market
intelligence** (news, strategy, partnerships, financials, expansion — last month)
for 50 target accounts, enriches/ranks it with EY's LLM, and produces a
**Power BI-ready Excel** and a **professional web dashboard**. Fresh every run.
No LinkedIn. No faked data.

## What you get each run
- `out/AccountSignal_<date>.xlsx` — flat sheets (Companies, Hiring_India, News, Signals) for Power BI
- `out/dashboard/index.html` — static dashboard (double-click to open, no login)
- `data/normalized/companies.json` — single source of truth

## Setup (first time, no admin rights needed)
```bash
# 1. create an isolated environment (Python 3.11+ recommended; 3.13 tested)
python -m venv .venv
.venv\Scripts\activate            # Windows
# source .venv/bin/activate       # macOS/Linux

# 2. install
pip install -e .
python -m playwright install chromium   # free browser for JS career sites

# 3. secrets — copy the template and fill in your keys
copy .env.example .env             # Windows  (cp on macOS/Linux)
#   EYQ_INCUBATOR_ENDPOINT / EYQ_INCUBATOR_KEY / EYQ_MODEL  (EY LLM)
#   APIFY_TOKEN                                             (free apify.com token)
```

## Run
```bash
python -m accountsignal.run                 # full pipeline: scrape -> enrich -> excel -> dashboard
python -m accountsignal.run --mock-llm      # build without EY LLM (for testing off-network)
python -m accountsignal.run --only news     # one stage: hiring | news | enrich | excel | ui
python -m accountsignal.run --companies "TIAA,GSK"   # subset (merges into existing data)
```

## Moving to the office laptop
1. Copy the whole folder **except** `.venv/`, `data/`, `out/` (they regenerate).
2. Recreate `.env` with your keys (never commit it).
3. Run the Setup steps above, then `python -m accountsignal.run`.
4. If the office network blocks a site, that company degrades to blank and the
   run still completes — nothing crashes.

## How hiring is captured (free-first cascade)
1. **Workday** public JSON API (direct, authoritative source URLs)
2. **Eightfold** / generic **Playwright** DOM render (free)
3. **Apify** Indeed fallback (`$0.006`/role, only when 1–2 find nothing) — a
   `$4.50` spend guard protects the free $5 tier.

Market-intelligence news comes from **Google News RSS** (free) for all 50.

## Rules enforced in code
- Hiring = India only + last 30 days; everything else = global + last 30 days
- No LinkedIn anywhere; blank only when a site is genuinely unscrapable
- News de-duplicated; internal relevance ranking never shown in the UI

## Tuning (`config/companies.yaml` and `.env`)
- Add/fix a company's `career_url` or `news_query`
- `ACCOUNTSIGNAL_LOOKBACK_DAYS` (default 30), `APIFY_MAX_ITEMS`, `APIFY_MAX_USD`

## Deploy the dashboard to Vercel (auto-deploys on every push)
The website is the static Next.js app in `webapp/`. The committed
[`vercel.json`](vercel.json) tells Vercel to build it (`npm --prefix webapp run
build`) and publish `webapp/out`, so the Vercel project needs **no** settings.

One-time setup:
1. Push this repo to GitHub.
2. Open <https://vercel.com/new>, import the repo, keep **Root Directory empty**
   and Framework Preset **Other**, then click **Deploy**.
3. Every later push to `main` rebuilds and republishes the site automatically.

Refreshing the numbers is therefore just data → git → auto-deploy:
```bash
python app.py                       # refresh the scrape, rewrites webapp/public/data.json
git add webapp/public/data.json
git commit -m "data refresh"
git push origin main                # Vercel redeploys in ~2 min
```
Double-click **`PUBLISH_SITE.bat`** to do that for you. Step-by-step
instructions and troubleshooting live in [`DEPLOY_VERCEL.txt`](DEPLOY_VERCEL.txt).
