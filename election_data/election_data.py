# uses data from this site(need to give credit)-https://dataverse.harvard.edu/dataset.xhtml?persistentId=doi:10.7910/DVN/VOQCHQ
import pandas as pd
import numpy as np

# 1. Define columns
cols = [
    'year', 'state', 'state_po', 'county_name', 'county_fips', 
    'office', 'candidate', 'party', 'candidatevotes', 'totalvotes', 
    'version', 'mode'
]

# 2. Load the data
file_path = 'countypres_2000-2024.tab'
print("Loading data...")
df = pd.read_csv(file_path, sep='\t', header=0, names=cols, keep_default_na=False)

# 3. THE SMART FILTER FIX
#    Goal: Use 'TOTAL' rows if they exist. If not, sum the other modes.

#    A. Create a unique ID for every county in every election
#       (Using Year + State + County Name ensures we target specific elections)
df['jurisdiction_id'] = df['year'].astype(str) + "_" + df['state_po'] + "_" + df['county_name']

#    B. Split the data into two piles
df_totals = df[df['mode'] == 'TOTAL'].copy()
df_details = df[df['mode'] != 'TOTAL'].copy()

#    C. Find out which counties already have a TOTAL row
counties_with_total = set(df_totals['jurisdiction_id'].unique())

#    D. Keep detail rows ONLY if their county is missing from the totals pile
#       (This captures VA, UT, etc., without double-counting others)
df_details_needed = df_details[~df_details['jurisdiction_id'].isin(counties_with_total)]

#    E. Aggregate the detailed rows to look like total rows
#       (Summing votes by candidate)
group_cols = ['year', 'state', 'state_po', 'county_name', 'county_fips', 'office', 'candidate', 'party']
df_details_aggregated = df_details_needed.groupby(group_cols, as_index=False)['candidatevotes'].sum()

#    F. Combine the "Original Totals" and our "Calculated Totals"
df_clean = pd.concat([df_totals, df_details_aggregated], ignore_index=True)

print(f"Data cleaned. Rows before: {len(df)}. Rows after smart-merge: {len(df_clean)}")


# 4. Categorize Votes (Blue/Red/Other)
def categorize_party(party_name):
    if party_name == 'DEMOCRAT':
        return 'blue votes'
    elif party_name == 'REPUBLICAN':
        return 'red votes'
    else:
        return 'other votes'

df_clean['party_category'] = df_clean['party'].apply(categorize_party)

# 5. Pivot
pivot_df = df_clean.pivot_table(
    index=['year', 'state', 'state_po', 'county_name', 'county_fips'],
    columns='party_category',
    values='candidatevotes',
    aggfunc='sum',
    fill_value=0
).reset_index()

# 6. Determine Winner
vote_cols = ['blue votes', 'red votes', 'other votes']
pivot_df['winner'] = pivot_df[vote_cols].idxmax(axis=1)

winner_map = {
    'blue votes': 'Democrat',
    'red votes': 'Republican',
    'other votes': 'Other'
}
pivot_df['winner'] = pivot_df['winner'].map(winner_map)

# 7. Final Output
final_output = pivot_df[[
    'year', 'state', 'state_po', 'county_name', 'county_fips', 
    'blue votes', 'red votes', 'other votes', 'winner'
]]

# 8. Export
output_filename = 'county_election_data.csv'
final_output.to_csv(output_filename, index=False)

print(f"Success. Saved to {output_filename}")
