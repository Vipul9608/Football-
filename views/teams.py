"""Team pages: header with favourite star, squad, results, fixtures and a form chart."""
from __future__ import annotations

from html import escape

import pandas as pd
import streamlit as st

from components.cards import empty_state, form_dots, html, kpi
from components.charts import form_chart
from components.media import crest_html, image_url
from services import api
from services.standings import compute_standings, result_for, team_results
from views.common import favorites, match_grid, selected_league_id, toggle_favorite

POSITION_ORDER = {"GK": 0, "DF": 1, "MF": 2, "FW": 3}
POSITION_NAMES = {"GK": "Goalkeeper", "DF": "Defender", "MF": "Midfielder", "FW": "Forward"}


def render() -> None:
    league_id = selected_league_id()
    teams = api.team_map(league_id)
    if not teams:
        empty_state("No teams found for this league.")
        return
    ids = sorted(teams, key=lambda tid: teams[tid]["name"])
    preferred = st.session_state.get("team_id")
    if preferred not in ids:
        preferred = next((tid for tid in ids if tid in favorites()), ids[0])
    team_id = st.selectbox("Team", ids, index=ids.index(preferred), format_func=lambda tid: teams[tid]["name"])
    st.session_state.team_id = team_id
    team = teams[team_id]

    matches = api.matches(league_id)
    table = compute_standings(matches, teams)
    row = next(r for r in table if r["team_id"] == team_id)

    header, star = st.columns([5, 1])
    header.markdown(f'<div class="ps-team-header">{crest_html(team, large=True)}<div><h2>{escape(team["name"])}</h2>'
                    f'<span class="ps-muted">{escape(api.league(league_id)["name"])}</span></div></div>', unsafe_allow_html=True)
    is_fav = team_id in favorites()
    if star.button("★ Favourite" if is_fav else "☆ Add to favourites", type="primary" if is_fav else "secondary",
                   width="stretch", key=f"star-{team_id}"):
        toggle_favorite(team_id)
        st.rerun()

    c1, c2, c3, c4 = st.columns(4)
    c1.markdown(kpi("Position", f"#{row['position']}", f"of {len(table)}"), unsafe_allow_html=True)
    c2.markdown(kpi("Points", str(row["points"]), f"{row['played']} played"), unsafe_allow_html=True)
    c3.markdown(kpi("Goals", f"{row['goals_for']}:{row['goals_against']}", f"GD {row['goal_diff']:+d}"), unsafe_allow_html=True)
    c4.markdown(f'<div class="ps-card ps-kpi"><div class="label">Form</div><div class="value" style="font-size:1rem;padding:.55rem 0">'
                f'{form_dots(row["form"])}</div><div class="sub">last five</div></div>', unsafe_allow_html=True)

    squad_tab, results_tab, fixtures_tab, form_tab = st.tabs(["Squad", "Results", "Fixtures", "Form"])
    with squad_tab:
        render_squad(team_id, league_id)
    with results_tab:
        played = team_results(matches, team_id)[::-1][:6]
        match_grid(played, teams, key=f"team-res-{team_id}") if played else empty_state("No results yet.")
    with fixtures_tab:
        upcoming = sorted((m for m in matches if m["status"] in ("SCHEDULED", "LIVE") and team_id in (m["home_id"], m["away_id"])),
                          key=lambda m: m["kickoff"])[:6]
        match_grid(upcoming, teams, key=f"team-fix-{team_id}") if upcoming else empty_state("No upcoming fixtures.")
    with form_tab:
        render_form(matches, teams, team_id)


def render_squad(team_id: int, league_id: int) -> None:
    with st.spinner("Loading squad…"):
        squad = api.squad(team_id)
        if squad and not squad[0].get("stats"):  # API squads have no stats: borrow them from the league player list
            stats = {p["id"]: p["stats"] for p in api.players(league_id)}
            squad = [p | {"stats": stats.get(p["id"], {})} for p in squad]
    if not squad:
        empty_state("No squad data available for this team.")
        return
    squad = sorted(squad, key=lambda p: (POSITION_ORDER.get(p["position"], 9), p.get("number") or 99))
    df = pd.DataFrame([{"Photo": image_url(p, "player"), "#": p.get("number"), "Name": p["name"],
                        "Position": POSITION_NAMES.get(p["position"], p["position"]), "Age": p.get("age"),
                        "Apps": p["stats"].get("appearances"), "Goals": p["stats"].get("goals"),
                        "Assists": p["stats"].get("assists"), "Rating": p["stats"].get("rating")} for p in squad])
    st.dataframe(df, hide_index=True, width="stretch", height=min(640, 38 + 35 * len(df)),
                 column_config={"Photo": st.column_config.ImageColumn(width="small"),
                                "Rating": st.column_config.ProgressColumn(min_value=0, max_value=10, format="%.2f")})


def render_form(matches: list[dict], teams: dict[int, dict], team_id: int) -> None:
    played = team_results(matches, team_id)
    if not played:
        empty_state("The form chart appears after the first match.")
        return
    rows, total = [], 0
    for m in played:
        home = m["home_id"] == team_id
        outcome = result_for(m, team_id)
        total += {"W": 3, "D": 1, "L": 0}[outcome]
        opponent = teams[m["away_id"] if home else m["home_id"]]["name"]
        rows.append({"label": f"MD{m['matchday']}", "opponent": opponent, "points_total": total,
                     "scored": m["home_goals"] if home else m["away_goals"],
                     "conceded": m["away_goals"] if home else m["home_goals"],
                     "score": f"{m['home_goals']}–{m['away_goals']} ({'H' if home else 'A'}, {outcome})"})
    st.plotly_chart(form_chart(rows), width="stretch", theme=None)
    html('<span class="ps-muted">Bars: goals scored (up) and conceded (down) per match. Line: running points total.</span>')
