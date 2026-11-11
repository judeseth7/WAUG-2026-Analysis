from pathlib import Path

import pandas as pd
import streamlit as st

st.set_page_config(page_title="WAUG 2026 Football Analysis", layout="wide")

ROOT = Path(__file__).resolve().parent

matches = pd.read_csv(ROOT / "data/raw-reports/football-matches.csv")
teams = pd.read_csv(ROOT / "reports/team-performances.csv")
defence = pd.read_csv(ROOT / "reports/team-defensive-analysis.csv")

st.title("⚽ WAUG 2026 Football Analysis")
st.caption("SIWES Project | Seth Praise Jude | OAU")
st.write(
    "An analysis of recorded match results, team performance, "
    "shooting efficiency and defensive performance."
)

goals = matches["home_goals"].sum() + matches["away_goals"].sum()

a, b, c, d = st.columns(4)
a.metric("Recorded matches", len(matches))
b.metric("Total goals", int(goals))
c.metric("Goals per match", f"{goals / len(matches):.2f}")
d.metric(
    "Penalty shootouts",
    int(matches["went_to_penalties"].str.lower().eq("yes").sum()),
)

overview, results, shooting, defensive = st.tabs(
    ["Team performance", "Match results", "Shooting", "Defence"]
)

with overview:
    st.subheader("Team performance summary")
    st.caption(
        "Points use 3 per win and 1 per draw across recorded matches. "
        "Shootouts are excluded from W/D/L and points; this is not an official group table."
    )
    st.dataframe(
        teams[["Team", "MP", "W", "D", "L", "GF", "GA", "GD", "Pts"]],
        hide_index=True,
        use_container_width=True,
    )
    st.subheader("Goals scored and conceded")
    st.bar_chart(teams.set_index("Team")[["GF", "GA"]])

with results:
    selected = st.selectbox(
        "Filter by team", ["All teams"] + sorted(teams["Team"].tolist())
    )
    filtered = matches
    if selected != "All teams":
        filtered = matches[
            matches["team_home"].eq(selected)
            | matches["team_away"].eq(selected)
        ]
    st.dataframe(
        filtered[
            [
                "match_date", "stage", "team_home", "home_goals",
                "away_goals", "team_away", "home_penalties",
                "away_penalties", "winner",
            ]
        ],
        hide_index=True,
        use_container_width=True,
    )
    st.caption("Penalty shootout goals are excluded from total goals.")
    st.download_button(
        "Download match dataset",
        matches.to_csv(index=False).encode("utf-8"),
        file_name="waug_2026_matches.csv",
        mime="text/csv",
    )

with shooting:
    st.subheader("Shooting efficiency")
    st.info(
        "Shooting statistics cover only matches with recorded shot data. "
        "Missing observations are not treated as zero."
    )
    available = teams[teams["ShootingMatches"] > 0]
    st.dataframe(
        available[
            [
                "Team", "ShootingMatches", "Shots", "ShotsOnTarget",
                "ShotAccuracyPct", "ConversionPct",
            ]
        ],
        hide_index=True,
        use_container_width=True,
    )
    st.bar_chart(
        available.set_index("Team")[["ShotAccuracyPct", "ConversionPct"]]
    )
    st.caption("Chart values are percentages.")

with defensive:
    st.subheader("Defensive performance")
    st.caption("This section covers matches with available shooting statistics.")
    st.dataframe(defence, hide_index=True, use_container_width=True)
    st.bar_chart(
        defence.set_index("Team")[
            ["ShotsOnTargetConceded", "GoalsConceded"]
        ]
    )

st.divider()
st.caption(
    "Coverage: 8 recorded matches, not a complete tournament dataset. "
    "Source URLs and verification labels are included in the downloadable dataset."
)