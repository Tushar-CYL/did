===============================================================
 ACCOUNTSIGNAL — SETUP & RUN STEPS
===============================================================

WHAT YOU NEED FIRST
-------------------
- Python 3.11 or newer installed  (check:  python --version)
- Internet access


ONE-TIME INSTALL
----------------
1. Open a terminal / command prompt in this project folder
   (the folder that contains app.py).

2. Create and activate a virtual environment:

      python -m venv .venv
      .venv\Scripts\activate

3. Install the project and its dependencies:

      pip install -e .

4. Install the browser used for some career sites:

      python -m playwright install chromium

5. Create your secrets file:
   - Make a copy of  .env.example  and name it  .env
   - Open  .env  and fill in the values:

        EYQ_INCUBATOR_ENDPOINT = (the EY LLM endpoint)
        EYQ_INCUBATOR_KEY      = (the EY LLM key)
        EYQ_MODEL              = gpt-5.2
        APIFY_TOKEN            = (your apify.com API token)


RUN IT (ONE CLICK)
------------------
From the project folder (with the venv activated):

      python app.py

This does everything in order:
      scrape  ->  rank / enrich  ->  Excel  ->  dashboard  ->  webapp data

Useful options:

      python app.py --skip-scrape      (reuse last data, just rebuild reports - fast)
      python app.py --eyq              (use the real EY LLM for the write-ups)
      python app.py --companies "TIAA,GSK"   (only these accounts)


WHERE THE RESULTS ARE
---------------------
- Excel (for Power BI):   out\AccountSignal_<date>.xlsx
- Simple dashboard:       out\dashboard\index.html   (double-click to open)
- Data file:              data\normalized\companies.json


VIEW THE FULL WEB APP
---------------------
1. After running app.py, start the web app server:

      python webapp\serve_nocache.py

2. Open a browser to:

      http://localhost:3000


NOTES
-----
- Every run is fresh - it re-scrapes and rebuilds all reports.
- If a website is blocked or unavailable, that account is just left
  blank and the run still finishes.
- Re-run any time with  python app.py  to refresh everything.

- Corporate network / SSL:
  The install includes pip-system-certs, which makes Python trust the
  machine's certificate store (so SSL-inspected networks work).
  If you still see "CERTIFICATE_VERIFY_FAILED", set this before running:
        set ACCOUNTSIGNAL_VERIFY_SSL=false
        python app.py
===============================================================
