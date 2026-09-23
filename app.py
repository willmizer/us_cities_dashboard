import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

st.set_page_config(page_title="US Cities: Elections vs. Census", layout="wide")

AGE_BUCKETS = [
    ("under_5", "0-4"), ("5_9", "5-9"), ("10_14", "10-14"), ("15_17", "15-17"),
    ("18_19", "18-19"), ("20", "20"), ("21", "21"), ("22_24", "22-24"),
    ("25_29", "25-29"), ("30_34", "30-34"), ("35_39", "35-39"), ("40_44", "40-44"),
    ("45_49", "45-49"), ("50_54", "50-54"), ("55_59", "55-59"), ("60_61", "60-61"),
    ("62_64", "62-64"), ("65_66", "65-66"), ("67_69", "67-69"), ("70_74", "70-74"),
    ("75_79", "75-79"), ("80_84", "80-84"), ("85_over", "85+"),
]

SORT_LOW_TO_HIGH = {"poverty", "unemployment", "commute", "home", "no_college"}

RANK_METRICS = {
    "income": "Median Income", "home": "Home Value", "wfh": "Remote Work %",
    "unemployment": "Unemployment Rate", "poverty": "Poverty Rate",
    "commute": "Commute Time", "education": "Bachelor's Degree+",
    "no_college": "No College", "pop": "Population",
}


def parse_series(raw):
    if pd.isna(raw) or raw == "":
        return [], []
    parts = str(raw).split("|")
    return parts, [np.nan if p == "" else float(p) for p in parts]


@st.cache_data
def load_stats():
    df = pd.read_csv("web/dashboard_stats.csv")
    df["pct_poverty"] = np.where(df["Total_Population"] > 0, df["Poverty_Count"] / df["Total_Population"] * 100, np.nan)
    df["pct_wfh"] = np.where(df["Total_Workers"] > 0, df["Worked_From_Home"] / df["Total_Workers"] * 100, np.nan)
    df["commuters"] = df["Total_Workers"] - df["Worked_From_Home"]
    df["pct_unemployment"] = np.where((df["Unemployed_Count"] + df["Total_Workers"]) > 0,
                                       df["Unemployed_Count"] / (df["Unemployed_Count"] + df["Total_Workers"]) * 100, np.nan)
    df["commute_min"] = np.where(df["commuters"] > 0, df["Travel_Time_to_Work"] / df["commuters"], np.nan)
    bach_plus = df[["Edu_Bachelors", "Edu_Masters", "Edu_Professional", "Edu_Doctorate"]].sum(axis=1)
    no_col = df[["Edu_None", "Edu_HighSchool"]].sum(axis=1)
    df["pct_bach_plus"] = np.where(df["Total_Population"] > 0, bach_plus / df["Total_Population"] * 100, np.nan)
    df["pct_no_college"] = np.where(df["Total_Population"] > 0, no_col / df["Total_Population"] * 100, np.nan)
    for race in ["White", "Black", "Hispanic", "Asian"]:
        df[f"pct_{race.lower()}"] = np.where(df["Total_Population"] > 0, df[f"Total_{race}"] / df["Total_Population"] * 100, np.nan)
    other = df["Total_Other_Race"].fillna(0) + df["Total_Two_or_More_Races"].fillna(0)
    df["pct_other"] = np.where(df["Total_Population"] > 0, other / df["Total_Population"] * 100, np.nan)
    return df


@st.cache_data
def load_votes():
    v = pd.read_csv("election_data/final_city_election_data.csv")
    v["city"] = v["city"].astype(str).str.strip()
    v["state_po"] = v["state_po"].astype(str).str.strip()
    v["total"] = v["blue votes"].fillna(0) + v["red votes"].fillna(0)
    v["dem_pct"] = np.where(v["total"] > 0, v["blue votes"] / v["total"] * 100, np.nan)
    v["rep_pct"] = np.where(v["total"] > 0, v["red votes"] / v["total"] * 100, np.nan)
    return v.sort_values("year")


@st.cache_data
def latest_votes(votes: pd.DataFrame):
    return votes.sort_values("year").groupby(["state_po", "city"], as_index=False).last()


stats = load_stats()
votes = load_votes()
latest = latest_votes(votes)
latest_idx = latest.set_index(["state_po", "city"])

states_list = sorted(stats["State"].dropna().unique().tolist())

st.title("US Cities: Elections vs. Census Statistics")
st.caption(
    "Pairs 2000-2024 presidential election results with ACS census statistics "
    "(income, home value, age, race, education, employment) for ~26,800 US cities. "
    "Originally a static HTML/Chart.js dashboard — rebuilt here as an interactive Streamlit app."
)

tab_city, tab_state, tab_match = st.tabs(["City Intel", "State Rankings", "Ideal City Matcher"])

# ---------------------------------------------------------------- City Intel
with tab_city:
    col_f1, col_f2 = st.columns([1, 2])
    with col_f1:
        state_filter = st.selectbox("State", ["All"] + states_list, key="city_state")
    city_pool = stats if state_filter == "All" else stats[stats["State"] == state_filter]
    city_options = sorted((city_pool["City"] + ", " + city_pool["State"]).tolist())
    with col_f2:
        city_choice = st.selectbox("City (type to search)", city_options, key="city_pick")

    if city_choice:
        city_name, state_po = city_choice.rsplit(", ", 1)
        row = city_pool[(city_pool["City"] == city_name) & (city_pool["State"] == state_po)].iloc[0]

        v = votes[(votes["city"] == city_name) & (votes["state_po"] == state_po)].sort_values("year")
        lv = v.iloc[-1] if len(v) else None

        st.markdown(f"## {city_name}, {state_po}")
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Population", f"{int(row['Total_Population']):,}" if pd.notna(row["Total_Population"]) else "-")
        c2.metric("Median Income", f"${row['Median_Income']:,.0f}" if pd.notna(row["Median_Income"]) else "-")
        c3.metric("Home Value", f"${row['Median_Home_Value']:,.0f}" if pd.notna(row["Median_Home_Value"]) else "-")
        c4.metric("Poverty Rate", f"{row['pct_poverty']:.1f}%" if pd.notna(row["pct_poverty"]) else "-")

        c5, c6 = st.columns(2)
        c5.metric("Remote Work", f"{row['pct_wfh']:.1f}%" if pd.notna(row["pct_wfh"]) else "-")
        if lv is not None and lv["total"] > 0:
            pct = lv["dem_pct"] if lv["winner"] == "Democrat" else lv["rep_pct"]
            c6.metric(f"Latest Election ({int(lv['year'])})", f"{lv['winner']} {pct:.0f}%")
        else:
            c6.metric("Latest Election", "N/A")

        ch1, ch2 = st.columns(2)
        with ch1:
            st.markdown("**Political Trend**")
            if len(v):
                fig = go.Figure()
                fig.add_bar(x=v["year"], y=v["blue votes"], name="Democrat", marker_color="#3b82f6")
                fig.add_bar(x=v["year"], y=v["red votes"], name="Republican", marker_color="#ef4444")
                fig.update_layout(barmode="stack", height=320, margin=dict(l=10, r=10, t=10, b=10))
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("No election data for this city.")
        with ch2:
            st.markdown("**Income vs Home Value (history)**")
            years, income_series = parse_series(row.get("Hist_Years", "")), None
            yrs, incomes = parse_series(row.get("Hist_Years", ""))
            _, homes = parse_series(row.get("Hist_Home", ""))
            _, incomes = parse_series(row.get("Hist_Income", ""))
            if yrs:
                fig = go.Figure()
                fig.add_scatter(x=yrs, y=incomes, name="Income", line=dict(color="#10b981", width=3))
                fig.add_scatter(x=yrs, y=homes, name="Home Value", line=dict(color="#3b82f6", width=3))
                fig.update_layout(height=320, margin=dict(l=10, r=10, t=10, b=10))
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("No historical trend data for this city.")

        ch3, ch4 = st.columns([2, 3])
        with ch3:
            st.markdown("**Racial Demographics**")
            race_vals = [row["Total_White"], row["Total_Black"], row["Total_Hispanic"], row["Total_Asian"],
                         (row["Total_Other_Race"] or 0) + (row["Total_Two_or_More_Races"] or 0)]
            fig = px.pie(names=["White", "Black", "Hispanic", "Asian", "Other"], values=race_vals,
                         color_discrete_sequence=["#e4e4e7", "#6366f1", "#f59e0b", "#10b981", "#ef4444"])
            fig.update_layout(height=320, margin=dict(l=10, r=10, t=10, b=10))
            st.plotly_chart(fig, use_container_width=True)
        with ch4:
            st.markdown("**Age & Gender Distribution**")
            labels = [b[1] for b in AGE_BUCKETS]
            m = [row.get(f"m_{b[0]}", 0) or 0 for b in AGE_BUCKETS]
            f = [row.get(f"f_{b[0]}", 0) or 0 for b in AGE_BUCKETS]
            fig = go.Figure()
            fig.add_bar(x=labels, y=m, name="Male", marker_color="#3b82f6")
            fig.add_bar(x=labels, y=f, name="Female", marker_color="#d946ef")
            fig.update_layout(height=320, margin=dict(l=10, r=10, t=10, b=10))
            st.plotly_chart(fig, use_container_width=True)

# ---------------------------------------------------------------- State Rankings
with tab_state:
    state_pick = st.selectbox("Target State", states_list, key="state_pick")
    df = stats[stats["State"] == state_pick].copy()

    def weighted(num_col, pop_col="Total_Population"):
        w = df[df[num_col].notna() & (df[pop_col] > 0)]
        return (w[num_col] * w[pop_col]).sum() / w[pop_col].sum() if len(w) else np.nan

    k1, k2, k3, k4, k5, k6, k7 = st.columns(7)
    k1.metric("Avg City Pop", f"{df['Total_Population'].mean():,.0f}" if len(df) else "-")
    k2.metric("Avg Income", f"${weighted('Median_Income'):,.0f}" if len(df) else "-")
    k3.metric("Avg Home Price", f"${weighted('Median_Home_Value'):,.0f}" if len(df) else "-")
    pop_sum, pov_sum = df["Total_Population"].sum(), df["Poverty_Count"].sum()
    lab_sum, unemp_sum = (df["Unemployed_Count"] + df["Total_Workers"]).sum(), df["Unemployed_Count"].sum()
    work_sum, wfh_sum = df["Total_Workers"].sum(), df["Worked_From_Home"].sum()
    commuters_sum, time_sum = df["commuters"].sum(), (df["Travel_Time_to_Work"] * (df["commuters"] > 0)).sum()
    k4.metric("Unemployment", f"{(unemp_sum/lab_sum*100):.1f}%" if lab_sum else "-")
    k5.metric("Remote Work", f"{(wfh_sum/work_sum*100):.1f}%" if work_sum else "-")
    k6.metric("Avg Commute", f"{(time_sum/commuters_sum):.0f}m" if commuters_sum else "-")
    k7.metric("Poverty Rate", f"{(pov_sum/pop_sum*100):.1f}%" if pop_sum else "-")

    f1, f2, f3 = st.columns(3)
    min_pop = f1.number_input("Min Population", min_value=0, value=0, step=1000)
    party = f2.selectbox("Party Filter", ["Show All", "Republican Only", "Democrat Only"])
    metric_key = f3.selectbox("Primary Ranking Metric", list(RANK_METRICS.keys()),
                               format_func=lambda k: RANK_METRICS[k])

    lv = latest.merge(df[["City", "State"]], left_on=["city", "state_po"], right_on=["City", "State"], how="inner")
    lv = lv.set_index("city")["winner"] if len(lv) else pd.Series(dtype=object)

    df["winner"] = df["City"].map(lv)
    table = df[df["Total_Population"] >= min_pop].copy()
    if party == "Republican Only":
        table = table[table["winner"] == "Republican"]
    elif party == "Democrat Only":
        table = table[table["winner"] == "Democrat"]

    metric_col = {
        "income": "Median_Income", "home": "Median_Home_Value", "wfh": "pct_wfh",
        "unemployment": "pct_unemployment", "poverty": "pct_poverty", "commute": "commute_min",
        "education": "pct_bach_plus", "no_college": "pct_no_college", "pop": "Total_Population",
    }[metric_key]
    table = table[table[metric_col].notna()]
    table = table.sort_values(metric_col, ascending=metric_key in SORT_LOW_TO_HIGH).head(100)

    show = table[["City", "Total_Population", "Median_Income", "Median_Home_Value", "pct_wfh",
                  "pct_unemployment", "pct_poverty", "commute_min", "pct_bach_plus", "pct_no_college", "winner"]]
    show = show.rename(columns={
        "City": "City", "Total_Population": "Population", "Median_Income": "Income",
        "Median_Home_Value": "Home Val", "pct_wfh": "Remote Work %", "pct_unemployment": "Unemp %",
        "pct_poverty": "Poverty %", "commute_min": "Commute (min)", "pct_bach_plus": "Bach+ %",
        "pct_no_college": "No College %", "winner": "Latest Vote",
    })
    st.caption(f"{len(table)} cities match — sorted by {RANK_METRICS[metric_key]} "
               f"({'ascending' if metric_key in SORT_LOW_TO_HIGH else 'descending'})")
    st.dataframe(show, use_container_width=True, hide_index=True)

# ---------------------------------------------------------------- Ideal City Matcher
with tab_match:
    st.caption(
        "**The Logic:** for each metric you target, we compute how far a city's actual number "
        "deviates from your target on a percentage basis; the lower the average deviation, the "
        "higher the match score. Small deviations in rates (poverty, unemployment) count more "
        "heavily than the same percentage deviation in dollar amounts."
    )
    match_state = st.selectbox("State", states_list, key="match_state")

    with st.sidebar:
        st.markdown("### Define Ideal City")
        use_pop = st.checkbox("Min Population")
        min_pop_target = st.number_input("Min Population", value=5000, disabled=not use_pop, key="mp") if use_pop else None

        use_pol = st.checkbox("Target Political Lean")
        pol_party = st.selectbox("Party", ["Democrat", "Republican"], disabled=not use_pol) if use_pol else None
        pol_pct = st.number_input("Target %", value=50.0, disabled=not use_pol, key="pp") if use_pol else None

        st.markdown("**Demographic focus**")
        use_div = st.checkbox("High Diversity (Balanced)")
        use_white = st.checkbox("Higher White Population")
        use_black = st.checkbox("Higher Black Population")
        use_hisp = st.checkbox("Higher Hispanic Population")
        use_asian = st.checkbox("Higher Asian Population")

        st.markdown("**Economic & social**")
        targets = {}
        if st.checkbox("Target Income ($)"):
            targets["income"] = st.number_input("Income target", value=75000)
        if st.checkbox("Target Home ($)"):
            targets["home"] = st.number_input("Home target", value=350000)
        if st.checkbox("Remote Work %"):
            targets["wfh"] = st.number_input("Remote work target %", value=15.0)
        if st.checkbox("Max Poverty %"):
            targets["poverty"] = st.number_input("Poverty target %", value=10.0)
        if st.checkbox("Target Commute (min)"):
            targets["commute"] = st.number_input("Commute target (min)", value=20.0)

        run = st.button("Find Matches", type="primary")

    any_demo = use_div or use_white or use_black or use_hisp or use_asian
    if run:
        if not targets and not use_pol and not any_demo:
            st.warning("Select at least one metric in the sidebar.")
        else:
            pool = stats[stats["State"] == match_state].copy()
            if use_pop:
                pool = pool[pool["Total_Population"] >= min_pop_target]

            col_map = {"income": "Median_Income", "home": "Median_Home_Value", "wfh": "pct_wfh",
                       "poverty": "pct_poverty", "commute": "commute_min"}

            results = []
            for _, r in pool.iterrows():
                total_diff, count = 0.0, 0
                details = []
                for key, tval in targets.items():
                    cval = r[col_map[key]]
                    if pd.notna(cval):
                        denom = tval if tval != 0 else 1
                        diff = abs(cval - tval) / denom
                        total_diff += diff
                        count += 1
                        fmt = f"${cval:,.0f}" if key in ("income", "home") else f"{cval:.1f}"
                        details.append(f"{key.upper()}: {fmt}")
                    else:
                        total_diff += 2.0
                        count += 1

                if use_pol:
                    rv = votes[(votes["city"] == r["City"]) & (votes["state_po"] == r["State"])]
                    city_pct = 0.0
                    if len(rv):
                        last = rv.sort_values("year").iloc[-1]
                        if last["total"] > 0:
                            city_pct = last["dem_pct"] if pol_party == "Democrat" else last["rep_pct"]
                    total_diff += abs(city_pct - pol_pct) / 100
                    count += 1
                    details.append(f"POL: {pol_party[:3]} {city_pct:.0f}%")

                if any_demo:
                    if use_div:
                        pop = r["Total_Population"] or 1
                        fracs = [r["Total_White"] / pop, r["Total_Black"] / pop, r["Total_Hispanic"] / pop,
                                 r["Total_Asian"] / pop, ((r["Total_Other_Race"] or 0) + (r["Total_Two_or_More_Races"] or 0)) / pop]
                        diversity = 1 - sum(x * x for x in fracs)
                        total_diff += (1 - diversity)
                        count += 1
                        details.append(f"DivScore: {diversity:.2f}")
                    for flag, col, label in [(use_white, "pct_white", "White"), (use_black, "pct_black", "Black"),
                                              (use_hisp, "pct_hispanic", "Hisp"), (use_asian, "pct_asian", "Asian")]:
                        if flag:
                            val = r[col] or 0
                            total_diff += (100 - val) / 100
                            count += 1
                            details.append(f"{label}: {val:.1f}%")

                if count > 0:
                    avg_diff = total_diff / count
                    score = max(0.0, 100 - avg_diff * 100)
                    results.append({"City": r["City"], "Match Score": round(score, 1), "Details": " | ".join(details)})

            results = sorted(results, key=lambda x: x["Match Score"], reverse=True)[:50]
            st.caption(f"{len(results)} matches")
            st.dataframe(pd.DataFrame(results), use_container_width=True, hide_index=True)
    else:
        st.info("Configure your ideal city profile in the sidebar, then click **Find Matches**.")
