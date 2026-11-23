"""League tables: sortable standings with form guide and zones, plus an animated points race."""
from __future__ import annotations

import pandas as pd
import plotly.express as px
import streamlit as st

from components.cards import html
from components.charts import points_race
from components.media import image_url
from components.table import standings_html
from components.theme import color, style_figure
from services import api
from services.standings import compute_standings, points_by_matchday
from views.common import favorites, selected_league_id

SORT_OPTIONS = {
    "Position": ("position", False), "Points": ("points", True), "Goal difference": ("goal_diff", True),
    "Goals scored": ("goals_for", True), "Goals conceded": ("goals_against", False),
    "Form (last 5)": ("form_points", True), "Wins": ("won", True),
}


def form_points(form: list[str]) -> int:
    return sum({"W": 3, "D": 1, "L": 0}[r] for r in form)


def render() -> None:
    league_id = selected_league_id()
    league = api.league(league_id)
    with st.spinner("Building the table…"):
        teams, matches = api.team_map(league_id), api.matches(league_id)
        rows = compute_standings(matches, teams, {tid: t["name"] for tid, t in teams.items()})
    st.markdown(f"## {league['name']} table")
    table_tab, race_tab, goals_tab = st.tabs(["Standings", "Points race", "Attack vs defence"])

    with table_tab:
        c1, c2 = st.columns([2, 1])
        sort_label = c1.selectbox("Sort by", list(SORT_OPTIONS), key="table_sort")
        flip = c2.toggle("Reverse order", key="table_reverse")
        key, descending = SORT_OPTIONS[sort_label]
        ordered = sorted(rows, key=lambda r: (form_points(r["form"]) if key == "form_points" else r[key], -r["position"] if descending else r["position"]),
                         reverse=descending)
        if flip:
            ordered.reverse()
        html(standings_html(ordered, teams, league["zones"], favorites()))
        with st.expander("Spreadsheet view (click a column header to sort)"):
            df = pd.DataFrame([{"Crest": image_url(teams[r["team_id"]], "team"), "#": r["position"],
                                "Team": teams[r["team_id"]]["name"], "P": r["played"], "W": r["won"], "D": r["drawn"],
                                "L": r["lost"], "GF": r["goals_for"], "GA": r["goals_against"], "GD": r["goal_diff"],
                                "Pts": r["points"], "Form": " ".join(r["form"])} for r in rows])
            st.dataframe(df, hide_index=True, width="stretch",
                         column_config={"Crest": st.column_config.ImageColumn(width="small")})

    with race_tab:
        frames = points_by_matchday(matches, teams)
        if frames:
            st.caption("Press ▶ to watch the season unfold. Drag the slider to jump to a matchday.")
            st.plotly_chart(points_race(frames, teams), width="stretch", theme=None)
        else:
            st.info("The race starts after the first matchday.")

    with goals_tab:
        df = pd.DataFrame([{"Team": teams[r["team_id"]]["name"], "Scored": r["goals_for"], "Conceded": r["goals_against"],
                            "Points": r["points"]} for r in rows])
        fig = px.scatter(df, x="Scored", y="Conceded", text="Team", size="Points", size_max=36,
                         color_discrete_sequence=[color("accent")], hover_data={"Points": True})
        fig.update_traces(textposition="top center", marker={"line": {"width": 1, "color": color("bg")}})
        fig.update_yaxes(autorange="reversed", title="Conceded (fewer is better ↑)")
        st.plotly_chart(style_figure(fig, height=480), width="stretch", theme=None)
