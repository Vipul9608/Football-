"""Landing page: hero, today's numbers, and the personalised 'My teams' dashboard."""
from __future__ import annotations

from html import escape

import streamlit as st

from components.animations import celebrate, lottie
from components.cards import empty_state, form_dots, html, kickoff_label, kpi, match_card, section_title
from components.media import crest_html
from services import api
from services.standings import compute_standings, team_results
from views.common import favorites, is_today, navigate, set_favorites


def render() -> None:
    hero, animation = st.columns([3, 1])
    with hero:
        html('<div class="ps-hero"><h1>Every match.<br><em>Every moment.</em></h1>'
             '<p>Live scores, tables, match centres and a predictor for the leagues you follow. '
             'Star your teams to build your own dashboard.</p></div>')
    with animation:
        lottie("ball", height=210, key="hero-ball")

    every = api.all_matches()
    today = [m for m in every if is_today(m) or m["status"] == "LIVE"]
    live = [m for m in today if m["status"] == "LIVE"]
    c1, c2, c3, c4 = st.columns(4)
    c1.markdown(kpi("Live now", str(len(live)), "matches in play"), unsafe_allow_html=True)
    c2.markdown(kpi("Today", str(len(today)), "matches"), unsafe_allow_html=True)
    c3.markdown(kpi("Leagues", str(len(api.leagues())), "followed"), unsafe_allow_html=True)
    c4.markdown(kpi("My teams", str(len(favorites())), "starred"), unsafe_allow_html=True)
    if live and st.button("🔴 Go to live scores", type="primary"):
        navigate("Scores")

    st.write("")
    render_favorites()


def _sync_favorites() -> None:
    set_favorites(st.session_state.favorites_widget)


def render_favorites() -> None:
    teams = api.all_teams()
    section_title("My teams", "personal dashboard")
    st.session_state.favorites_widget = [tid for tid in favorites() if tid in teams]
    st.multiselect("Choose your favourite teams", sorted(teams, key=lambda t: teams[t]["name"]),
                   format_func=lambda tid: teams[tid]["name"], key="favorites_widget", on_change=_sync_favorites,
                   placeholder="Search teams…")
    chosen = [tid for tid in favorites() if tid in teams]
    if not chosen:
        empty_state("No favourites yet. Pick teams above, or press ☆ on any team page.")
        return

    leagues = {lg["id"]: lg for lg in api.leagues()}
    for start in range(0, len(chosen), 2):
        cols = st.columns(2)
        for col, team_id in zip(cols, chosen[start:start + 2]):
            with col:
                _favorite_card(teams[team_id], leagues[teams[team_id]["league_id"]], teams)

    with st.expander("🎉 Test the goal celebration"):
        st.caption("When a favourite team scores during a live game, the Scores page celebrates like this.")
        if st.button("Simulate a goal"):
            celebrate(teams[chosen[0]]["name"], "(test)")


def _favorite_card(team: dict, league: dict, teams: dict[int, dict]) -> None:
    matches = api.matches(league["id"])
    league_teams = {tid: t for tid, t in teams.items() if t["league_id"] == league["id"]}
    table = compute_standings(matches, league_teams)
    row = next((r for r in table if r["team_id"] == team["id"]), None)
    last = (team_results(matches, team["id"]) or [None])[-1]
    current = next((m for m in matches if m["status"] == "LIVE" and team["id"] in (m["home_id"], m["away_id"])), None)
    upcoming = next((m for m in sorted(matches, key=lambda m: m["kickoff"])
                     if m["status"] == "SCHEDULED" and team["id"] in (m["home_id"], m["away_id"])), None)

    def versus(m: dict) -> str:
        other = m["away_id"] if m["home_id"] == team["id"] else m["home_id"]
        return f"{'vs' if m['home_id'] == team['id'] else '@'} {teams[other]['name']}"

    last_line = (f"{versus(last)} · {last['home_goals']}–{last['away_goals']}" if last else "–")
    next_line = (f"{versus(upcoming)} · {kickoff_label(upcoming['kickoff'])}" if upcoming else "–")
    position = f"#{row['position']} · {row['points']} pts" if row else ""
    html(f'<div class="ps-card"><div class="ps-team-header">{crest_html(team, large=True)}<div>'
         f'<div class="ps-display" style="font-size:1.25rem;font-weight:700">{escape(team["name"])}</div>'
         f'<div class="ps-muted">{escape(league["name"])} · {position}</div>'
         f'<div style="margin-top:.35rem">{form_dots(row["form"] if row else [])}</div></div></div>'
         f'<div style="margin-top:.8rem;font-size:.88rem"><div><span class="ps-muted">Last:</span> {escape(last_line)}</div>'
         f'<div><span class="ps-muted">Next:</span> {escape(next_line)}</div></div></div>')
    if current:
        html(match_card(current, teams[current["home_id"]], teams[current["away_id"]], league["name"], favorites()))
    if st.button("Open team page", key=f"fav-open-{team['id']}", width="stretch"):
        navigate("Teams", team_id=team["id"], league_id=league["id"])
