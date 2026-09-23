import os
import pandas as pd

# paths are resolved relative to this file so the script runs from any directory
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
votes_file = os.path.join(BASE_DIR, 'election_data', 'final_city_election_data.csv')
stats_file = os.path.join(BASE_DIR, 'city_statistics', 'us_cities_statistics_2012_2024.csv')
out_file = os.path.join(BASE_DIR, 'final_us_cities_statistics.csv')
dashboard_file = os.path.join(BASE_DIR, 'web', 'dashboard_stats.csv')

df_votes = pd.read_csv(votes_file)
df = pd.read_csv(stats_file)

# state abbreviations
us_state_to_abbrev = {
    "Alabama": "AL", "Alaska": "AK", "Arizona": "AZ", "Arkansas": "AR", "California": "CA",
    "Colorado": "CO", "Connecticut": "CT", "Delaware": "DE", "Florida": "FL", "Georgia": "GA",
    "Hawaii": "HI", "Idaho": "ID", "Illinois": "IL", "Indiana": "IN", "Iowa": "IA",
    "Kansas": "KS", "Kentucky": "KY", "Louisiana": "LA", "Maine": "ME", "Maryland": "MD",
    "Massachusetts": "MA", "Michigan": "MI", "Minnesota": "MN", "Mississippi": "MS", "Missouri": "MO",
    "Montana": "MT", "Nebraska": "NE", "Nevada": "NV", "New Hampshire": "NH", "New Jersey": "NJ",
    "New Mexico": "NM", "New York": "NY", "North Carolina": "NC", "North Dakota": "ND", "Ohio": "OH",
    "Oklahoma": "OK", "Oregon": "OR", "Pennsylvania": "PA", "Rhode Island": "RI", "South Carolina": "SC",
    "South Dakota": "SD", "Tennessee": "TN", "Texas": "TX", "Utah": "UT", "Vermont": "VT",
    "Virginia": "VA", "Washington": "WA", "West Virginia": "WV", "Wisconsin": "WI", "Wyoming": "WY",
    "District of Columbia": "DC", "Puerto Rico": "PR"
}

# process stats data
if 'NAME' in df.columns:
    # split name into city/state
    split = df['NAME'].str.rsplit(', ', n=1, expand=True)
    df['City'] = split[0].str.strip()
    
    # handle state mapping
    if split.shape[1] > 1:
        df['State'] = split[1].str.strip().map(us_state_to_abbrev).fillna(split[1].str.strip())
    else:
        df['State'] = ""

    # remove bad rows and original column
    df = df[~df['State'].isin(['Village of Islands village; Florida', 'Moore County metropolitan government; Tennessee'])].drop(columns=['NAME'])

    # reorder columns: state, city, rest
    df = df[['State', 'City'] + [c for c in df.columns if c not in ['State', 'City']]]

# normalize cities
# clean votes data for comparison
df_votes['city'] = df_votes['city'].astype(str).str.strip()
df_votes['state_po'] = df_votes['state_po'].astype(str).str.strip()

# lookup for valid cities per state
votes_map = df_votes.groupby('state_po')['city'].apply(list).to_dict()

def normalize_city(row):
    state, city = row['State'], row['City']
    # sort valid cities by length descending
    valid_cities = sorted(votes_map.get(state, []), key=len, reverse=True)
    
    if city in valid_cities: return city
    for v_city in valid_cities:
        if v_city in city: return v_city
    return city

if not df.empty:
    df['City'] = df.apply(normalize_city, axis=1)

# filter and save
initial_rows = len(df)
valid_locs = set(zip(df_votes['state_po'], df_votes['city']))

# apply filter
df = df[df.apply(lambda x: (x['State'], x['City']) in valid_locs, axis=1)]

# calculate stats
final_rows = len(df)
rows_removed = initial_rows - final_rows

print(f"Initial rows: {initial_rows}")
print(f"Final rows: {final_rows}")
print(f"Rows removed: {rows_removed}")

df.to_csv(out_file, index=False)
print(f"Full dataset saved -> {out_file}")


# ---------------------------------------------------------------------------
# Slim, pre-aggregated file for the web dashboard (web/index.html).
# One row per city = its latest ACS year, plus the income / home-value time
# series folded into pipe-joined Hist_* columns. ~124 MB -> ~11 MB, 310k -> 27k
# rows, so the browser can parse it on page load without freezing.
# ---------------------------------------------------------------------------
age_suffix = ["under_5", "5_9", "10_14", "15_17", "18_19", "20", "21", "22_24",
              "25_29", "30_34", "35_39", "40_44", "45_49", "50_54", "55_59",
              "60_61", "62_64", "65_66", "67_69", "70_74", "75_79", "80_84", "85_over"]
snapshot_cols = [
    "Median_Income", "Median_Home_Value", "Total_Population", "Total_Workers",
    "Poverty_Count", "Worked_From_Home", "Unemployed_Count", "Travel_Time_to_Work",
    "Total_White", "Total_Black", "Total_Hispanic", "Total_Asian",
    "Total_Other_Race", "Total_Two_or_More_Races", "Edu_None", "Edu_HighSchool",
    "Edu_Bachelors", "Edu_Masters", "Edu_Professional", "Edu_Doctorate",
] + [f"{p}_{s}" for s in age_suffix for p in ("m", "f")]

def _ints(series):
    return "|".join("" if pd.isna(x) else str(int(x)) for x in series)

if not df.empty:
    # one row per city-year (normalize_city can collapse several source rows onto one city)
    ordered = df.drop_duplicates(["State", "City", "Year"]).sort_values("Year")
    latest = ordered.groupby(["State", "City"], as_index=False).tail(1)  # actual latest-year row per city

    hist = ordered.groupby(["State", "City"]).agg(
        Hist_Years=("Year", lambda s: "|".join(str(int(y)) for y in s)),
        Hist_Income=("Median_Income", _ints),
        Hist_Home=("Median_Home_Value", _ints),
    ).reset_index()

    keep = [c for c in snapshot_cols if c in latest.columns]
    slim = latest[["State", "City", "Year"] + keep].merge(hist, on=["State", "City"])
    for c in keep + ["Year"]:
        slim[c] = slim[c].map(lambda x: "" if pd.isna(x) else (str(int(x)) if float(x) == int(x) else x))

    os.makedirs(os.path.dirname(dashboard_file), exist_ok=True)
    slim.to_csv(dashboard_file, index=False)
    print(f"Dashboard dataset saved -> {dashboard_file} ({len(slim)} cities)")