# https://www.census.gov/data/developers/data-sets.html - credit
import os
import requests
import pandas as pd
import numpy as np
from functools import reduce
from concurrent.futures import ThreadPoolExecutor, as_completed
from dotenv import load_dotenv

load_dotenv()

# setup
api_key = os.environ.get("CENSUS_API_KEY")
if not api_key:
    raise RuntimeError(
        "Set the CENSUS_API_KEY environment variable (get a free key at "
        "https://api.census.gov/data/key_signup.html). Locally, put it in a "
        ".env file (see .env.example) and it will be picked up automatically."
    )
dataset = "acs/acs5"

# --- variables & mapping ---
core_vars = [
    "NAME", "B19013_001E", "B25077_001E", "B11001_001E", "B01002_001E", "B01003_001E", 
    "B01001_002E", "B01001_026E", "B03002_003E", "B03002_004E", "B03002_006E", 
    "B03002_012E", "B03002_005E", "B03002_007E", "B03002_008E", "B03002_009E", 
    "B05002_013E", "B07003_004E", "B15003_021E", "B15003_022E", "B15003_023E", 
    "B15003_024E", "B15003_025E", "B17001_002E", "B23025_005E", "B08006_001E", 
    "B08006_017E", "B08013_001E",
    # education vars (k-12)
    "B15003_004E", "B15003_005E", "B15003_006E", "B15003_007E", "B15003_008E",
    "B15003_009E", "B15003_010E", "B15003_011E", "B15003_012E", "B15003_013E",
    "B15003_014E", "B15003_015E", "B15003_016E", "B15003_017E"
]

rename_map = {
    "B19013_001E": "Median_Income", "B25077_001E": "Median_Home_Value",
    "B11001_001E": "Total_Households", "B01002_001E": "Median_Age",
    "B01003_001E": "Total_Population", "B01001_002E": "Total_Males",
    "B01001_026E": "Total_Females", "B03002_003E": "Total_White",
    "B03002_004E": "Total_Black", "B03002_006E": "Total_Asian",
    "B03002_012E": "Total_Hispanic", "B03002_005E": "Total_American_Indian",
    "B03002_007E": "Total_Native_Hawaiian", "B03002_008E": "Total_Other_Race",
    "B03002_009E": "Total_Two_or_More_Races", "B05002_013E": "Total_Foreign_Born",
    "B07003_004E": "Total_Moved_Within_1_Year", "B15003_017E": "Edu_HighSchool",
    "B15003_021E": "Edu_Associates", "B15003_022E": "Edu_Bachelors",
    "B15003_023E": "Edu_Masters", "B15003_024E": "Edu_Professional",
    "B15003_025E": "Edu_Doctorate", "B17001_002E": "Poverty_Count",
    "B23025_005E": "Unemployed_Count", "B08006_001E": "Total_Workers",
    "B08006_017E": "Worked_From_Home", "B08013_001E": "Travel_Time_to_Work",
    # temp mapping for summation
    "B15003_004E": "temp_K", "B15003_005E": "temp_1", "B15003_006E": "temp_2",
    "B15003_007E": "temp_3", "B15003_008E": "temp_4", "B15003_009E": "temp_5",
    "B15003_010E": "temp_6", "B15003_011E": "temp_7", "B15003_012E": "temp_8",
    "B15003_013E": "temp_9", "B15003_014E": "temp_10", "B15003_015E": "temp_11",
    "B15003_016E": "temp_12_no_dip",
}

# generate age/sex vars and map dynamically
age_labels = [
    "under_5", "5_9", "10_14", "15_17", "18_19", "20", "21", "22_24", 
    "25_29", "30_34", "35_39", "40_44", "45_49", "50_54", "55_59", 
    "60_61", "62_64", "65_66", "67_69", "70_74", "75_79", "80_84", "85_over"
]

male_vars = [f"B01001_{i+3:03d}E" for i in range(len(age_labels))]
female_vars = [f"B01001_{i+27:03d}E" for i in range(len(age_labels))]

for i, lbl in enumerate(age_labels):
    rename_map[male_vars[i]] = f"m_{lbl}"
    rename_map[female_vars[i]] = f"f_{lbl}"

all_vars = core_vars + male_vars + female_vars
batch_size = 48
var_batches = [all_vars[i:i + batch_size] for i in range(0, len(all_vars), batch_size)]

print(f"Total variables: {len(all_vars)}")

# --- data collection ---
state_fips = [
    "01", "02", "04", "05", "06", "08", "09", "10", "11", "12", "13", "15", "16", 
    "17", "18", "19", "20", "21", "22", "23", "24", "25", "26", "27", "28", "29", 
    "30", "31", "32", "33", "34", "35", "36", "37", "38", "39", "40", "41", "42", 
    "44", "45", "46", "47", "48", "49", "50", "51", "53", "54", "55", "56", "72"
]

def fetch_data(year, state):
    base_url = f"https://api.census.gov/data/{year}/{dataset}"
    dfs = []
    try:
        for batch in var_batches:
            url = f"{base_url}?get={','.join(batch)}&for=place:*&in=state:{state}&key={api_key}"
            r = requests.get(url)
            if r.status_code != 200: return None
            
            data = r.json()
            dfs.append(pd.DataFrame(data[1:], columns=data[0]))
        
        # merge batches
        merged = reduce(lambda l, r: pd.merge(l, r, on=['state', 'place']), dfs)
        merged['Year'] = year
        return merged
    except:
        return None

results = []
print("Starting multithreaded collection...")

with ThreadPoolExecutor(max_workers=10) as ex:
    futures = {ex.submit(fetch_data, y, s): (y, s) for y in range(2012, 2024) for s in state_fips}
    for f in as_completed(futures):
        res = f.result()
        if res is not None: results.append(res)

# --- clean & save ---
if results:
    df = pd.concat(results, ignore_index=True)
    df.rename(columns=rename_map, inplace=True)
    
    # convert numeric, handle errors
    num_cols = [c for c in df.columns if c not in ['NAME', 'state', 'place', 'Year']]
    for c in num_cols:
        df[c] = pd.to_numeric(df[c], errors='coerce')
        df.loc[df[c] < 0, c] = np.nan # handle census error codes

    # filter population < 100
    orig_len = len(df)
    df = df[df['Total_Population'] >= 100]
    print(f"Removed {orig_len - len(df)} tiny cities.")

    # custom calc: sum no diploma
    temp_cols = [c for c in df.columns if c.startswith('temp_')]
    df['Edu_None'] = df[temp_cols].sum(axis=1)
    df.drop(columns=temp_cols, inplace=True)

    # reorder columns
    edu_group = [
        'Edu_None', 'Edu_HighSchool', 'Edu_Associates', 'Edu_Bachelors', 
        'Edu_Masters', 'Edu_Professional', 'Edu_Doctorate'
    ]
    
    # move metadata to end, insert edu group correctly
    meta = ['Year', 'state', 'place']
    cols = [c for c in df.columns if c not in meta + edu_group]
    
    if 'Total_Moved_Within_1_Year' in cols:
        idx = cols.index('Total_Moved_Within_1_Year') + 1
        cols[idx:idx] = edu_group
    else:
        cols.extend(edu_group)
        
    df = df[cols + meta].sort_values(by=['Year', 'state', 'place'])
    
    df.to_csv("us_cities_statistics_2012_2024.csv", index=False)
    print(f"Done. Saved {len(df)} rows.")
else:
    print("No data collected.")