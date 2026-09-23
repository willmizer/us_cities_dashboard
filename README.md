# US Cities: Elections vs. Census Statistics

Builds a per-city dataset that pairs 2000–2024 presidential election results with
ACS census statistics (income, home value, age, race, education, employment…),
and a browser dashboard to explore and "match" cities by those metrics.

## Setup

```bash
python3.12 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Data collection (`city_statistics/city_data_statistics_2012_2024.py`) needs a free
[Census API key](https://api.census.gov/data/key_signup.html). Copy `.env.example`
to `.env` and fill in `CENSUS_API_KEY=...` — not needed to run the dashboard itself,
only to re-run the data pipeline.

## Data pipeline (run in order)

| Step | Script | Reads | Writes |
| --- | --- | --- | --- |
| 1 | `election_data/election_data.py` | `election_data/countypres_2000-2024.tab` | `election_data/county_election_data.csv` |
| 2 | `election_data/city_county_filter.py` | `election_data/uscities.csv`, `county_election_data.csv` | `election_data/simple_city_county_list.csv`, `election_data/final_city_election_data.csv` |
| 3 | `city_statistics/city_data_statistics_2012_2024.py` | US Census ACS5 API (needs an API key, hard-coded in the file) | `city_statistics/us_cities_statistics_2012_2024.csv` |
| 4 | `clean_statistics.py` | `election_data/final_city_election_data.csv`, `city_statistics/us_cities_statistics_2012_2024.csv` | `final_us_cities_statistics.csv` (full, ~124 MB) **and** `web/dashboard_stats.csv` (slim, for the dashboard) |

Steps 1–2 and 3 are independent; step 4 needs both. All scripts resolve their own
paths, so they can be run from any directory. Outputs are already committed, so you
can skip straight to the dashboard.

## Streamlit dashboard (`app.py`)

[Live demo](https://us-cities-dashboard.streamlit.app/)

```bash
pip install -r requirements.txt
streamlit run app.py
```

Three views, same underlying data as the original static dashboard below:
- **City Intel** — pick a state + city; KPIs (income, home value, poverty, remote
  work), latest election result, a political-vote trend chart, an income-vs-home-value
  history chart, racial demographics, and an age/gender distribution.
- **State Rankings** — state-wide aggregate KPIs plus a sortable, filterable table of
  every city in the state (min population, party, and ranking-metric filters).
- **Ideal City Matcher** — set target population, political lean, income, home value,
  remote-work %, poverty cap, commute time, and demographic preferences; ranks cities
  in a state by how closely they match, using the same percentage-error scoring as the
  original JS matcher.

Reads `web/dashboard_stats.csv` (slim, one row per city) and
`election_data/final_city_election_data.csv` — both already committed, no API key
needed to run it.

## Original static dashboard (`web/`)

Static HTML + CDN JS (Chart.js, PapaParse, Bootstrap) — the app.py Streamlit
dashboard above supersedes this for interactive use, but it's kept as the original,
dependency-free version. On open it **auto-loads**
`election_data/final_city_election_data.csv` and `web/dashboard_stats.csv`.
Because browsers block `fetch()` from `file://`, serve the project over HTTP from
the **`states_project/` directory**:

```bash
python3 -m http.server 8000
# then open http://localhost:8000/web/
```

If the fetch fails, the page falls back to manual file pickers for those same two files.

### `web/dashboard_stats.csv`

The dashboard reads ~23 census fields plus a 46-bucket age pyramid, and only the
latest year for everything except the income / home-value trend lines. So
`clean_statistics.py` also emits this slim file: **one row per city** (its latest
ACS year), with the income/home-value history folded into pipe-joined `Hist_Years`
/ `Hist_Income` / `Hist_Home` columns. That takes the load from ~124 MB / 310k rows
down to ~11 MB / 27k rows. Regenerate it by re-running `clean_statistics.py`.
