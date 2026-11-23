"""Player explorer: search and filter, then compare two players on a radar chart."""
from __future__ import annotations

import pandas as pd
import streamlit as st

from components.cards import empty_state, html
from components.charts import radar
from components.media import avatar_html, image_url
from components.theme import color
from services import api
from services.player_stats import RADAR_METRICS, metric_value, radar_profile
from views.common import selected_league_id

POSITIONS = {"GK": "Goalkeeper", "DF": "Defender", "MF": "Midfielder", "FW": "Forward"}


def render() -> None:
    st.markdown("## Player explorer")
    leagues = {lg["id"]: lg for lg in api.leagues()}
    teams = api.all_teams()

    with st.container(border=True):
        c1, c2, c3 = st.columns([2, 2, 2])
        league_ids = c1.multiselect("League", list(leagues), default=[selected_league_id()],
                                    format_func=lambda lid: leagues[lid]["name"])
        with st.spinner("Loading players…"):
            pool = [p for lid in league_ids for p in api.players(lid)]
        team_options = sorted({p["team_id"] for p in pool if p["team_id"] in teams}, key=lambda tid: teams[tid]["name"])
        team_ids = c2.multiselect("Team", team_options, format_func=lambda tid: teams[tid]["name"], placeholder="All teams")
        positions = c3.multiselect("Position", list(POSITIONS), format_func=POSITIONS.get, placeholder="All positions")
        c4, c5, c6 = st.columns([2, 2, 2])
        query = c4.text_input("Search by name", placeholder="e.g. Silva")
        ages = [p["age"] for p in pool if p.get("age")] or [16, 40]
        age_range = c5.slider("Age", min(ages), max(ages), (min(ages), max(ages)))
        min_minutes = c6.slider("Minimum minutes", 0, 1200, 270, step=90)

    filtered = [p for p in pool
                if (not team_ids or p["team_id"] in team_ids)
                and (not positions or p["position"] in positions)
                and (not query or query.lower() in p["name"].lower())
                and (not p.get("age") or age_range[0] <= p["age"] <= age_range[1])
                and float(p["stats"].get("minutes") or 0) >= min_minutes]
    if not filtered:
        empty_state("No players match these filters. Try widening the age range or lowering the minutes.")
        return

    list_tab, compare_tab = st.tabs([f"Players ({len(filtered)})", "Compare two players"])
    with list_tab:
        df = pd.DataFrame([{"Photo": image_url(p, "player"), "Name": p["name"],
                            "Team": teams.get(p["team_id"], {}).get("name", "?"), "Pos": p["position"], "Age": p.get("age"),
                            "Mins": int(p["stats"].get("minutes") or 0), "Goals": int(p["stats"].get("goals") or 0),
                            "Assists": int(p["stats"].get("assists") or 0),
                            "G+A /90": round(metric_value(p, "goals", True) + metric_value(p, "assists", True), 2),
                            "Tackles": int(p["stats"].get("tackles") or 0), "Rating": p["stats"].get("rating")}
                           for p in filtered]).sort_values(["Goals", "Assists"], ascending=False)
        st.dataframe(df, hide_index=True, width="stretch", height=520,
                     column_config={"Photo": st.column_config.ImageColumn(width="small"),
                                    "Rating": st.column_config.ProgressColumn(min_value=0, max_value=10, format="%.2f")})
    with compare_tab:
        render_compare(filtered, teams)


def render_compare(pool: list[dict], teams: dict[int, dict]) -> None:
    ranked = sorted(pool, key=lambda p: -(float(p["stats"].get("goals") or 0) + float(p["stats"].get("assists") or 0)))
    label = {p["id"]: f"{p['name']} · {teams.get(p['team_id'], {}).get('short', '?')} · {p['position']}" for p in ranked}
    by_id = {p["id"]: p for p in ranked}
    ids = list(by_id)
    c1, c2 = st.columns(2)
    first = c1.selectbox("Player A", ids, index=0, format_func=label.get)
    second = c2.selectbox("Player B", ids, index=1 if len(ids) > 1 else 0, format_func=label.get)
    a, b = by_id[first], by_id[second]

    for col, player, tint in ((c1, a, color("accent")), (c2, b, "#38BDF8")):
        s = player["stats"]
        team_name = teams.get(player["team_id"], {}).get("name", "")
        col.markdown(
            f'<div class="ps-card" style="border-left:4px solid {tint}"><div class="ps-team">{avatar_html(player)}'
            f'<span class="name">{player["name"]}</span></div><div class="ps-muted" style="margin-top:.3rem">'
            f'{team_name} · {POSITIONS.get(player["position"], "")} · age {player.get("age") or "?"}</div>'
            f'<div style="margin-top:.4rem">⚽ {int(s.get("goals") or 0)} &nbsp; 🅰️ {int(s.get("assists") or 0)} &nbsp; '
            f'⏱ {int(s.get("minutes") or 0)} min &nbsp; ⭐ {s.get("rating") or "–"}</div></div>', unsafe_allow_html=True)

    labels = [label_text for _, label_text, _ in RADAR_METRICS]
    values_a, hover_a = radar_profile(a, pool)
    values_b, hover_b = radar_profile(b, pool)
    st.plotly_chart(radar(labels, [(a["name"], values_a, hover_a, color("accent")), (b["name"], values_b, hover_b, "#38BDF8")]),
                    width="stretch", theme=None)
    html('<span class="ps-muted">Each axis is a percentile against the players in your current filter '
         '(per 90 minutes where it makes sense), so the shape changes as you filter.</span>')
