# Minsk Property Agent

Autonomous research pipeline for **Minsk region** flat listings on [realt.by](https://realt.by): extract structured data, enrich with OSM proximity, compute a **desirability score**, and emit `property_data_final.csv` plus interactive `minsk_investor_report.html`.

## Setup

```bash
cd Minsk-Property-Agent
python3 -m venv .venv
source .venv/bin/activate
pip install -U pip setuptools wheel
pip install -r requirements.txt
pip install -r requirements-dev.txt
playwright install chromium
cp .env.example .env
```

If `python3 -m venv .venv` fails on an external/exFAT volume, create the virtualenv on a local APFS path (for example `/tmp/minsk-venv`) and point `PYTHONPATH` at this repo’s `src` when running tests.

For an editable install including **Playwright** and **pytest**:

```bash
pip install -e ".[dev]"
playwright install chromium
```

## Deploy on Streamlit Community Cloud

1. Create a **new empty repository** on GitHub (e.g. `minsk-property-agent`) — **do not** paste `src/...` as the repo URL.
2. Push **this whole project folder** to that repo (so the root contains `requirements.txt`, `streamlit_app.py`, **`pyproject.toml`**, and the full **`src/`** tree — run `git ls-files src/minsk_agent | head` locally; it must list `explorer_app.py` and other modules). Root **`requirements.txt` omits Playwright** so Community Cloud can install deps reliably (Playwright is only in **`requirements-dev.txt`** for local scraping).
3. On [share.streamlit.io](https://share.streamlit.io) → **New app**:
   - **Repository:** `https://github.com/YOUR_USERNAME/YOUR_REPO_NAME` (a normal GitHub URL only).
   - **Branch:** `main` (use `master` only if that is what your GitHub repo actually uses).
   - **Main file path:** `streamlit_app.py` (root file we provide), **or** `src/minsk_agent/explorer_app.py` if you prefer.
4. **Secrets / data:** Community Cloud does not include your local `property_data_final.csv` unless you commit it or load it from elsewhere. Options: commit a **sample** CSV, add **[Streamlit secrets](https://docs.streamlit.io/deploy/streamlit-community-cloud/deploy-your-app/secrets-management)** with a download URL, or extend the app with `st.file_uploader` so viewers upload a CSV.

## Interactive map (Streamlit)

After you have run the pipeline and generated `property_data_final.csv`:

```bash
pip install -r requirements.txt
minsk-agent explorer
```

Or:

```bash
streamlit run src/minsk_agent/explorer_app.py
```

Then open the URL Streamlit prints (usually `http://localhost:8501`). Use the sidebar to filter by **price, area, rooms, max distance to metro/park/water, desirability, district, days on market**; the **map** shows filtered listings (click markers for links).

Optional: set `STREAMLIT_DATA_CSV=/path/to/other.csv` to open a different file by default.

To share it **on the internet** (not only localhost), use a hoster such as [Streamlit Community Cloud](https://streamlit.io/cloud) or any VPS: point the app at `src/minsk_agent/explorer_app.py`, upload or sync `property_data_final.csv`, and set `STREAMLIT_DATA_CSV` if the file is not in the repo.

## Run

```bash
minsk-agent run
minsk-agent run --show
# or
python -m minsk_agent run
python -m minsk_agent run --show
```

Environment variables are documented in [.env.example](.env.example). Set `SHOW_DASHBOARD=1` to always open the HTML report in your browser after each run, or pass `--show` once.

## Archived listings and turnover

The public listing HTML exposes active inventory via `__NEXT_DATA__`. A dedicated **archive index URL** is not reliably available without authenticated or internal APIs. For **Turnover_Ratio** (archived / active per district), supply optional **`data/archived_by_district.csv`**:

```csv
district_key,archived_count
"Минск",120
"Ждановичи",15
```

`district_key` must match the pipeline’s `district_key` column (`townName` when present, else `stateDistrictName`).

## Compliance

Respect [realt.by robots.txt](https://realt.by/robots.txt), use conservative rate limits, and do not circumvent CAPTCHAs or authentication. Increase `REQUEST_DELAY_SEC` if you see throttling.

## Tests

```bash
pytest tests/
# needs: pip install -r requirements-dev.txt
```
