# US Cities: Elections vs. Census Statistics

[![Live Demo](https://img.shields.io/badge/Streamlit-Live_Demo-FF4B4B?style=for-the-badge&logo=streamlit&logoColor=white)](https://us-cities-dashboard.streamlit.app/)
[![Python](https://img.shields.io/badge/Python-3.12-3776AB?style=for-the-badge&logo=python&logoColor=white)]()

**An interactive dashboard pairing US presidential election results with Census demographics, city by city.**

Builds a per-city dataset joining 2000–2024 presidential election results with ACS census statistics (income, home value, age, race, education, employment), then lets you explore, rank, and "match" cities against your own priorities.

---

## Overview

- **City Intel:** pick a state + city and see KPIs (income, home value, poverty, remote work), the latest election result, an income-vs-home-value history, racial demographics, and an age/gender distribution.
- **State Rankings:** state-wide aggregate KPIs plus a sortable, filterable table of every city in the state (by minimum population, party, or ranking metric).
- **Ideal City Matcher:** set target population, political lean, income, home value, remote-work %, poverty cap, and commute time — ranks cities by how closely they match, using percentage-error scoring.

## Tech Stack

- **App:** Python, Streamlit, Plotly
- **Data Collection:** US Census Bureau ACS5 API, `requests`
- **Data Processing:** pandas, NumPy

## Data Pipeline

Run in order — all scripts resolve their own paths, so they can be run from any directory. Outputs are already committed, so you can skip straight to the dashboard.

| Step | Script | Reads | Writes |
| :--- | :--- | :--- | :--- |
| 1 | `election_data/election_data.py` | `election_data/countypres_2000-2024.tab` | `election_data/county_election_data.csv` |
| 2 | `election_data/city_county_filter.py` | `election_data/uscities.csv`, `county_election_data.csv` | `simple_city_county_list.csv`, `final_city_election_data.csv` |
| 3 | `city_statistics/city_data_statistics_2012_2024.py` | Census ACS5 API (needs an API key) | `city_statistics/us_cities_statistics_2012_2024.csv` |
| 4 | `clean_statistics.py` | outputs of steps 2 & 3 | `final_us_cities_statistics.csv` (full, ~130 MB) and `web/dashboard_stats.csv` (slim, ~11 MB, used by the app) |

Steps 1–2 and step 3 are independent; step 4 needs both. Data collection needs a free [Census API key](https://api.census.gov/data/key_signup.html) — copy `.env.example` to `.env` and set `CENSUS_API_KEY=...` (only needed to re-run the pipeline, not to run the dashboard).

`clean_statistics.py` also folds each city's income/home-value history into pipe-joined `Hist_Years`/`Hist_Income`/`Hist_Home` columns and keeps only the latest ACS year per city elsewhere — taking the dashboard's data footprint from ~130 MB / 310k rows down to ~11 MB / 27k rows.

## By the Numbers

- **26,782** cities across **51** states/territories.
- **194,484** city-election-year records spanning 2000–2024.
- Per-city stats cover income, home value, population, race, education, employment, commute time, and a 46-bucket age/gender pyramid.

## Project Structure

```
states_project/
├── app.py                              # Streamlit dashboard (entry point)
├── city_statistics/
│   └── city_data_statistics_2012_2024.py   # Census ACS5 API pull
├── election_data/
│   ├── election_data.py                # County-level election cleaning
│   ├── city_county_filter.py           # Maps counties to cities
│   ├── countypres_2000-2024.tab        # Raw county election results (MIT Election Lab)
│   └── final_city_election_data.csv
├── clean_statistics.py                 # Joins election + census data, builds dashboard export
├── web/
│   ├── index.html                      # Original static HTML/Chart.js dashboard
│   └── dashboard_stats.csv             # Slim per-city export used by both dashboards
└── requirements.txt
```

## Run Locally

```bash
git clone https://github.com/willmizer/us_cities_dashboard.git
cd us_cities_dashboard
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
streamlit run app.py
```

No API key needed to run the dashboard — it reads the already-committed `web/dashboard_stats.csv` and `election_data/final_city_election_data.csv`.

### Original static dashboard

A dependency-free static HTML + Chart.js version is kept in `web/` as the original. It auto-loads the same two CSVs, but browsers block `fetch()` from `file://`, so serve it over HTTP from the repo root:

```bash
python3 -m http.server 8000
# then open http://localhost:8000/web/
```

## Future Improvements

- Add county- and state-level rollups alongside the current city-level view.
- Bring in more recent ACS vintages as they're released.
- Let the Ideal City Matcher weight criteria by importance instead of treating them equally.

## License

This project is shared for portfolio and educational purposes — feel free to explore the code. Please reach out before reusing it commercially.

© 2026 Will Mizer
