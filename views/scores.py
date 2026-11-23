"""Live & recent scores, grouped by league, auto-refreshing every 60 seconds."""
from __future__ import annotations

from datetime import datetime

import streamlit as st

from components.animations import celebrate
from components.cards import empty_state, html, kpi, section_title, skeleton
from services import api
from services.favorites import favorite_goals, score_snapshot
from views.common import favorites, is_today, match_grid, selected_league_id

REFRESH_SECONDS = 60


def render() -> None:
    st.markdown("## Scores")
    live_tab, results_tab, fixtures_tab = st.tabs(["🔴 Live & today", "Results", "Fixtures"])
    with live_tab:
        live_board()
    with results_tab:
        matchday_board(finished=True)
    with fixtures_tab:
        matchday_board(finished=False)


@st.fragment(run_every=REFRESH_SECONDS)
def live_board() -> None:
    """Today's games for every league. Re-runs on its own every 60 s, without reloading the page."""
    placeholder = st.empty()
    placeholder.markdown(skeleton(3), unsafe_allow_html=True)
    leagues = api.leagues()
    by_league = {lg["id"]: [m for m in api.matches(lg["id"]) if m["status"] == "LIVE" or is_today(m)] for lg in leagues}
    teams = api.all_teams()
    placeholder.empty()

    every = [m for ms in by_league.values() for m in ms]
    _celebrate_new_goals(every, teams)

    live = [m for m in every if m["status"] == "LIVE"]
    goals = sum((m["home_goals"] or 0) + (m["away_goals"] or 0) for m in every if m["status"] != "SCHEDULED")
    c1, c2, c3 = st.columns(3)
    c1.markdown(kpi("Live now", str(len(live)), "matches in play"), unsafe_allow_html=True)
    c2.markdown(kpi("Today", str(len(every)), "matches across leagues"), unsafe_allow_html=True)
    c3.markdown(kpi("Goals today", str(goals), "so far"), unsafe_allow_html=True)

    top = st.columns([3, 1])
    top[0].caption(f"Auto-refreshes every {REFRESH_SECONDS}s · last update {datetime.now().strftime('%H:%M:%S')}")
    if top[1].button("↻ Refresh now", width="stretch"):
        api._matches.clear()
        st.rerun(scope="fragment")

    if not every:
        empty_state("No matches today. Check the Results and Fixtures tabs.")
    order = {"LIVE": 0, "SCHEDULED": 1, "FINISHED": 2, "POSTPONED": 3}
    for lg in leagues:
        games = sorted(by_league[lg["id"]], key=lambda m: (order.get(m["status"], 9), m["kickoff"]))
        if games:
            live_count = sum(m["status"] == "LIVE" for m in games)
            section_title(lg["name"], f"{live_count} live" if live_count else lg["country"])
            match_grid(games, teams, lg["name"], key=f"today-{lg['id']}")


def _celebrate_new_goals(matches: list[dict], teams: dict[int, dict]) -> None:
    previous = st.session_state.get("score_snapshot")
    if previous is not None:
        for match, team_id in favorite_goals(previous, matches, favorites()):
            celebrate(teams[team_id]["name"], f"{match['home_goals']}–{match['away_goals']}")
    st.session_state.score_snapshot = score_snapshot(matches)


def matchday_board(finished: bool) -> None:
    """The last (or next) two matchdays of the league chosen in the sidebar."""
    league_id = selected_league_id()
    league = api.league(league_id)
    with st.spinner("Loading matches…"):
        matches, teams = api.matches(league_id), api.team_map(league_id)
    wanted = "FINISHED" if finished else "SCHEDULED"
    matchdays = sorted({m["matchday"] for m in matches if m["status"] == wanted}, reverse=finished)[:2]
    if not matchdays:
        empty_state("Nothing to show yet.")
        return
    for matchday in matchdays:
        games = sorted((m for m in matches if m["matchday"] == matchday and m["status"] == wanted), key=lambda m: m["kickoff"])
        section_title(f"{league['name']} · Matchday {matchday}")
        match_grid(games, teams, league["name"], key=f"{'res' if finished else 'fix'}-{matchday}")
    html("<div style='height:.5rem'></div>")
