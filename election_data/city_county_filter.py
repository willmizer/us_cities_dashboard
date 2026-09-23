import pandas as pd

# ==========================================
# PART 1: Process the City Data
# ==========================================
df_cities = pd.read_csv('uscities.csv')

# Filter and sort data
filtered_cities = df_cities[['state_id', 'county_name', 'county_fips', 'city', 'population']]
filtered_cities = filtered_cities.sort_values(by=['state_id', 'county_name', 'population'], ascending=[True, True, False])

# Save the simple list (as you requested)
filtered_cities.to_csv('simple_city_county_list.csv', index=False)
print(f"-> Saved 'simple_city_county_list.csv' with {len(filtered_cities)} cities.")

# ==========================================
# PART 2: Merge with Election Data
# ==========================================
print("\nLoading election data...")
# Load the election file we created in the previous step
df_election = pd.read_csv('county_election_data.csv')

# Standardize 'county_fips' to ensure they match (force both to integers)
# This handles cases where one file might use "1001" (string) and the other 1001 (int)
filtered_cities['county_fips'] = pd.to_numeric(filtered_cities['county_fips'], errors='coerce').fillna(0).astype(int)
df_election['county_fips'] = pd.to_numeric(df_election['county_fips'], errors='coerce').fillna(0).astype(int)

# Merge the City list with the Election Results using 'county_fips'
# how='inner' ensures we only get rows where the county exists in both files
merged_df = pd.merge(
    filtered_cities,
    df_election,
    on='county_fips',
    how='inner',
    suffixes=('_city', '_vote')
)

# ==========================================
# PART 3: Format and Save Final Output
# ==========================================

# Select only the columns you want in the specific order
final_output = merged_df[[
    'year',
    'state_po',         # From Election File (or State_id from city file)
    'city',
    'blue votes',
    'red votes',
    'other votes',
    'winner'
]]


# Sort the final output: Latest Year -> State -> County -> Biggest City
final_output = final_output.sort_values(
    by=['year', 'state_po', 'city'], 
    ascending=[True, True, True]
)

# Save the final mapped file
output_filename = 'final_city_election_data.csv'
final_output.to_csv(output_filename, index=False)

print("Done")