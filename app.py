import os

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from theme import BLUE, COLORWAY, RED, apply_theme, style_fig

st.set_page_config(
    page_title="US Cities Explorer",
    page_icon=os.path.join(os.path.dirname(__file__), "favicon.png"),
    layout="wide",
)

# Keep the modebar so Streamlit's own fullscreen-expand button (injected into it)
# still shows, but strip every other Plotly tool (zoom, pan, select, download, etc).
PLOTLY_CONFIG = {
    "displaylogo": False,
    "scrollZoom": False,
    "doubleClick": False,
    "modeBarButtonsToRemove": [
        "zoom2d", "pan2d", "select2d", "lasso2d",
        "zoomIn2d", "zoomOut2d", "autoScale2d", "resetScale2d",
        "toImage", "hoverClosestCartesian", "hoverCompareCartesian",
        "toggleSpikelines",
    ],
}


def render_chart(fig, **kwargs):
    """View + fullscreen-expand only: no drag-zoom/pan, no legend toggling, no other controls."""
    style_fig(fig)
    fig.update_layout(dragmode=False, legend=dict(itemclick=False, itemdoubleclick=False))
    st.plotly_chart(fig, config=PLOTLY_CONFIG, **kwargs)

apply_theme(max_width="1320px")

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
    # Education counts are for adults 25+, so the denominator must be the 25+ population
    # (summed from the age buckets), not total population, which understated both rates by ~30%.
    adult_keys = [k for k, _ in AGE_BUCKETS[[k for k, _ in AGE_BUCKETS].index("25_29"):]]
    df["pop_25plus"] = df[[f"{sx}_{k}" for k in adult_keys for sx in ("m", "f")]].sum(axis=1)
    bach_plus = df[["Edu_Bachelors", "Edu_Masters", "Edu_Professional", "Edu_Doctorate"]].sum(axis=1)
    no_col = df[["Edu_None", "Edu_HighSchool"]].sum(axis=1)
    df["pct_bach_plus"] = np.where(df["pop_25plus"] > 0, bach_plus / df["pop_25plus"] * 100, np.nan)
    df["pct_no_college"] = np.where(df["pop_25plus"] > 0, no_col / df["pop_25plus"] * 100, np.nan)
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
    # Some cities (mostly CT) have a second, all-zero row for the same election year that
    # would otherwise be picked as the "latest" result. Keep the row with the most votes.
    v = v.sort_values("total", ascending=False).drop_duplicates(["state_po", "city", "year"])
    # The raw 2024 file has "TOTAL VOTES CAST" pseudo-rows that inflate "other votes", so ~2,900 cities
    # (TX, WI, WV...) were labelled "Other" winners. Decide the winner on Democrat vs Republican only,
    # matching how dem_pct / rep_pct are computed.
    v["winner"] = np.where(v["blue votes"] >= v["red votes"], "Democrat", "Republican")
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
    "Originally a static HTML/Chart.js dashboard, rebuilt here as an interactive Streamlit app."
)

tab_city, tab_state, tab_match = st.tabs(["City Intel", "State Rankings", "Ideal City Matcher"])

# ---------------------------------------------------------------- City Intel
with tab_city:
    col_f1, col_f2 = st.columns([1, 2])
    with col_f1:
        state_filter = st.selectbox("State", ["All"] + states_list, key="city_state")
    city_pool = stats if state_filter == "All" else stats[stats["State"] == state_filter]
    city_options = sorted((city_pool["City"] + ", " + city_pool["State"]).tolist())
    default_city = "Sarasota, FL"
    default_city_index = city_options.index(default_city) if default_city in city_options else 0
    with col_f2:
        city_choice = st.selectbox("City (type to search)", city_options, index=default_city_index, key="city_pick")

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
            party_color = BLUE if lv["winner"] == "Democrat" else RED
            with c6:
                st.caption(f"Latest Election ({int(lv['year'])})")
                st.markdown(
                    f"<span style='font-size:1.75rem;font-weight:600;color:{party_color};'>"
                    f"{lv['winner']} {pct:.0f}%</span>",
                    unsafe_allow_html=True,
                )
        else:
            c6.metric("Latest Election", "N/A")

        ch1, ch2 = st.columns(2)
        with ch1:
            st.markdown("**Political Trend**")
            if len(v):
                fig = go.Figure()
                fig.add_bar(x=v["year"], y=v["blue votes"], name="Democrat", marker_color=BLUE)
                fig.add_bar(x=v["year"], y=v["red votes"], name="Republican", marker_color=RED)
                fig.update_layout(barmode="stack", height=320, margin=dict(l=10, r=10, t=10, b=10))
                render_chart(fig, use_container_width=True)
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
                fig.add_scatter(x=yrs, y=incomes, name="Income", line=dict(color=COLORWAY[1], width=3))
                fig.add_scatter(x=yrs, y=homes, name="Home Value", line=dict(color=BLUE, width=3))
                fig.update_layout(height=320, margin=dict(l=10, r=10, t=10, b=10))
                render_chart(fig, use_container_width=True)
            else:
                st.info("No historical trend data for this city.")

        ch3, ch4 = st.columns([2, 3])
        with ch3:
            st.markdown("**Racial Demographics**")
            race_vals = [row["Total_White"], row["Total_Black"], row["Total_Hispanic"], row["Total_Asian"],
                         (row["Total_Other_Race"] or 0) + (row["Total_Two_or_More_Races"] or 0)]
            fig = px.pie(names=["White", "Black", "Hispanic", "Asian", "Other"], values=race_vals,
                         color_discrete_sequence=[COLORWAY[6], COLORWAY[0], COLORWAY[2], COLORWAY[1], COLORWAY[3]])
            fig.update_layout(height=320, margin=dict(l=10, r=10, t=10, b=10))
            render_chart(fig, use_container_width=True)
        with ch4:
            st.markdown("**Age & Gender Distribution**")
            labels = [b[1] for b in AGE_BUCKETS]
            m = [row.get(f"m_{b[0]}", 0) or 0 for b in AGE_BUCKETS]
            f = [row.get(f"f_{b[0]}", 0) or 0 for b in AGE_BUCKETS]
            fig = go.Figure()
            fig.add_bar(x=labels, y=m, name="Male", marker_color=BLUE)
            fig.add_bar(x=labels, y=f, name="Female", marker_color=COLORWAY[5])
            fig.update_layout(height=320, margin=dict(l=10, r=10, t=10, b=10))
            render_chart(fig, use_container_width=True)

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
    has_commute = df["commuters"].gt(0) & df["Travel_Time_to_Work"].notna()  # numerator and denominator from the same cities
    commuters_sum, time_sum = df.loc[has_commute, "commuters"].sum(), df.loc[has_commute, "Travel_Time_to_Work"].sum()
    k4.metric("Unemployment", f"{(unemp_sum/lab_sum*100):.1f}%" if lab_sum else "-")
    k5.metric("Remote Work", f"{(wfh_sum/work_sum*100):.1f}%" if work_sum else "-")
    k6.metric("Avg Commute", f"{(time_sum/commuters_sum):.0f}m" if commuters_sum else "-")
    k7.metric("Poverty Rate", f"{(pov_sum/pop_sum*100):.1f}%" if pop_sum else "-")

    f1, f2, f3 = st.columns(3)
    min_pop = f1.number_input("Min Population", min_value=0, value=1000, step=1000, format="%d",
                              help="Steps by 1,000, or type any exact number.")
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
        "City": "City", "Total_Population": "Population", "Median_Income": "Income ($)",
        "Median_Home_Value": "Home Val ($)", "pct_wfh": "Remote Work %", "pct_unemployment": "Unemp %",
        "pct_poverty": "Poverty %", "commute_min": "Commute (min)", "pct_bach_plus": "Bach+ %",
        "pct_no_college": "No College %", "winner": "Latest Vote",
    })
    st.caption(f"{len(table)} cities match, sorted by {RANK_METRICS[metric_key]} "
               f"({'ascending' if metric_key in SORT_LOW_TO_HIGH else 'descending'})")
    st.dataframe(
        show, use_container_width=True, hide_index=True,
        column_config={
            "Population": st.column_config.NumberColumn(format="localized"),
            "Income ($)": st.column_config.NumberColumn(format="localized"),
            "Home Val ($)": st.column_config.NumberColumn(format="localized"),
            "Remote Work %": st.column_config.NumberColumn(format="%.1f"),
            "Unemp %": st.column_config.NumberColumn(format="%.1f"),
            "Poverty %": st.column_config.NumberColumn(format="%.1f"),
            "Commute (min)": st.column_config.NumberColumn(format="%.1f"),
            "Bach+ %": st.column_config.NumberColumn(format="%.1f"),
            "No College %": st.column_config.NumberColumn(format="%.1f"),
        },
    )

# ---------------------------------------------------------------- Ideal City Matcher
PICKINESS = {  # how much of the vote the chosen party must win for a "perfect" political match
    "Not too picky (50%+)": 50.0,
    "Pretty picky (65%+)": 65.0,
    "Super picky (75%+)": 75.0,
}
BUCKET_LABELS = ["Lowest", "Low", "Middle", "High", "Highest"]
CAP_LABELS = ["Very low", "Low", "Moderate", "Not picky"]
BUCKET_Q = [0.0, 0.2, 0.4, 0.6, 0.8, 1.0]  # quintile edges
CAP_Q = [0.2, 0.4, 0.6, 0.8]                 # "max" ceilings for poverty
MIN_CITIES_FOR_BUCKETS = 10


def money(x):
    return f"${x/1000:,.0f}k" if x < 1e6 else f"${x/1e6:.2f}M"


def build_buckets(values, fmt, capped=False):
    """Turn a state's city values into labelled (label -> (lo, hi)) buckets using quantiles.

    Range buckets (income, home, remote work, commute) are quintiles of the state's cities.
    Capped buckets (poverty) are ceilings: "at or below" the 20th/40th/60th/80th percentile.
    """
    vals = values.dropna()
    if len(vals) < MIN_CITIES_FOR_BUCKETS:
        return {}
    out = {}
    if capped:
        for lab, q in zip(CAP_LABELS, CAP_Q):
            hi = vals.quantile(q)
            out[f"{lab} (up to {fmt(hi)})"] = (-np.inf, hi)
    else:
        edges = [vals.quantile(q) for q in BUCKET_Q]
        for i, lab in enumerate(BUCKET_LABELS):
            lo, hi = (-np.inf if i == 0 else edges[i]), (np.inf if i == 4 else edges[i + 1])
            if i == 0:
                rng = f"under {fmt(hi)}"
            elif i == 4:
                rng = f"{fmt(lo)}+"
            else:
                rng = f"{fmt(lo)} - {fmt(hi)}"
            out[f"{lab} ({rng})"] = (lo, hi)
    return out


def bucket_penalty(val, lo, hi, spread):
    """0 inside the bucket; outside it grows with distance from the nearest edge, relative to
    the state's typical spread (10th-90th percentile), capped at 1. Missing data = full penalty."""
    if pd.isna(val):
        return 1.0
    if lo <= val <= hi:
        return 0.0
    dist = lo - val if val < lo else val - hi
    return min(1.0, dist / spread) if spread > 0 else 1.0


with tab_match:
    st.caption(
        "**The Logic:** every choice you make is a *bucket* built from that state's own cities "
        "(so \"High income\" in Mississippi differs from \"High income\" in Connecticut). A city "
        "scores full marks on a metric if it lands inside your bucket, and loses points the further "
        "outside it falls, measured against the state's typical spread. Your match score is 100 minus "
        "the average penalty across everything you select."
    )
    match_state = st.selectbox("State", states_list, key="match_state")
    state_all = stats[stats["State"] == match_state]

    with st.sidebar:
        st.markdown("### Define Ideal City")
        use_pop = st.checkbox("Min Population")
        min_pop_target = st.number_input(
            "Min Population", min_value=0, value=5000, step=100, format="%d",
            key="mp", help="Steps by 100, or type any exact number.",
        ) if use_pop else None

        # bucket edges come from the state's cities that pass the population floor
        bucket_pool = state_all if not use_pop else state_all[state_all["Total_Population"] >= min_pop_target]

        use_pol = st.checkbox("Target Political Lean")
        pol_party = st.selectbox("Party", ["Democrat", "Republican"]) if use_pol else None
        pol_pick = st.selectbox("How picky?", list(PICKINESS.keys())) if use_pol else None
        pol_pct = PICKINESS[pol_pick] if use_pol else None

        st.markdown("**Demographic focus**")
        use_div = st.checkbox("High Diversity (Balanced)")
        use_white = st.checkbox("Higher White Population")
        use_black = st.checkbox("Higher Black Population")
        use_hisp = st.checkbox("Higher Hispanic Population")
        use_asian = st.checkbox("Higher Asian Population")

        st.markdown("**Economic & social**")
        st.caption(f"Buckets are based on {len(bucket_pool):,} cities in {match_state}.")
        # key -> (checkbox label, column, formatter, capped?, dot-label)
        BUCKET_SPECS = {
            "income": ("Target Income", "Median_Income", money, False),
            "home": ("Target Home Value", "Median_Home_Value", money, False),
            "wfh": ("Remote Work %", "pct_wfh", lambda x: f"{x:.1f}%", False),
            "poverty": ("Max Poverty %", "pct_poverty", lambda x: f"{x:.1f}%", True),
            "commute": ("Target Commute", "commute_min", lambda x: f"{x:.0f} min", False),
        }
        targets = {}  # key -> (lo, hi)
        for key, (label, col, fmt, capped) in BUCKET_SPECS.items():
            if st.checkbox(label):
                buckets = build_buckets(bucket_pool[col], fmt, capped)
                if not buckets:
                    st.caption(f"Not enough cities with {label.lower()} data - lower the min population.")
                    continue
                default = list(buckets)[1 if capped else 2]  # Low ceiling / Middle range
                pick = st.selectbox(label, list(buckets), index=list(buckets).index(default), key=f"b_{key}",
                                    label_visibility="collapsed")
                targets[key] = buckets[pick]

        run = st.button("Find Matches", type="primary")

    any_demo = use_div or use_white or use_black or use_hisp or use_asian
    if run:
        if not targets and not use_pol and not any_demo:
            st.warning("Select at least one metric in the sidebar.")
        elif bucket_pool.empty:
            st.warning("No cities meet that population floor.")
        else:
            pool = bucket_pool.copy()
            col_map = {k: v[1] for k, v in BUCKET_SPECS.items()}
            spreads = {k: (bucket_pool[c].quantile(0.9) - bucket_pool[c].quantile(0.1)) for k, c in col_map.items()}

            results = []
            for _, r in pool.iterrows():
                total_diff, count = 0.0, 0
                details = []
                for key, (lo, hi) in targets.items():
                    cval = r[col_map[key]]
                    total_diff += bucket_penalty(cval, lo, hi, spreads[key])
                    count += 1
                    if pd.notna(cval):
                        fmt = f"${cval:,.0f}" if key in ("income", "home") else f"{cval:.1f}"
                        details.append(f"{key.upper()}: {fmt}")

                if use_pol:
                    city_pct = 0.0
                    if (r["State"], r["City"]) in latest_idx.index:
                        last = latest_idx.loc[(r["State"], r["City"])]
                        if last["total"] > 0:
                            city_pct = last["dem_pct"] if pol_party == "Democrat" else last["rep_pct"]
                    # one-sided: meeting or beating the threshold is a perfect match
                    total_diff += max(0.0, pol_pct - city_pct) / pol_pct
                    count += 1
                    details.append(f"POL: {pol_party[:3]} {city_pct:.0f}%")

                if any_demo:
                    pop = r["Total_Population"] or 1
                    if use_div:
                        fracs = [r["Total_White"] / pop, r["Total_Black"] / pop, r["Total_Hispanic"] / pop,
                                 r["Total_Asian"] / pop, ((r["Total_Other_Race"] or 0) + (r["Total_Two_or_More_Races"] or 0)) / pop]
                        diversity = 1 - sum(x * x for x in np.nan_to_num(fracs))
                        total_diff += (1 - diversity)
                        count += 1
                        details.append(f"DivScore: {diversity:.2f}")
                    for flag, col, label in [(use_white, "pct_white", "White"), (use_black, "pct_black", "Black"),
                                              (use_hisp, "pct_hispanic", "Hisp"), (use_asian, "pct_asian", "Asian")]:
                        if flag:
                            val = 0.0 if pd.isna(r[col]) else r[col]
                            total_diff += (100 - val) / 100
                            count += 1
                            details.append(f"{label}: {val:.1f}%")

                if count > 0:
                    score = max(0.0, 100 - total_diff / count * 100)
                    results.append({"City": r["City"], "Population": int(r["Total_Population"]),
                                    "Match Score": round(score, 1), "Details": " | ".join(details)})

            results = sorted(results, key=lambda x: x["Match Score"], reverse=True)[:50]
            st.caption(f"Top {len(results)} matches in {match_state}")
            st.dataframe(
                pd.DataFrame(results), use_container_width=True, hide_index=True,
                column_config={
                    "Population": st.column_config.NumberColumn(format="localized"),
                    "Match Score": st.column_config.ProgressColumn(min_value=0, max_value=100, format="%.1f"),
                },
            )
    else:
        st.info("Configure your ideal city profile in the sidebar, then click **Find Matches**.")
