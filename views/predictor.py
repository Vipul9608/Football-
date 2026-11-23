"""Match predictor: Poisson model on recent form, probability gauges and what-if sliders."""
from __future__ import annotations

import streamlit as st

from components.cards import html, kpi
from components.charts import probability_bar, probability_gauges, scoreline_heatmap
from services import api
from services.predictor import default_home_advantage, predict, team_strength
from views.common import selected_league_id


def render() -> None:
    st.markdown("## Match predictor")
    league_id = selected_league_id()
    teams, matches = api.team_map(league_id), api.matches(league_id)
    ids = sorted(teams, key=lambda tid: teams[tid]["name"])
    if len(ids) < 2:
        st.info("Need at least two teams to predict a match.")
        return

    upcoming = sorted((m for m in matches if m["status"] == "SCHEDULED"), key=lambda m: m["kickoff"])[:10]
    if upcoming:
        options = [None] + [m["id"] for m in upcoming]
        by_id = {m["id"]: m for m in upcoming}
        pick = st.selectbox("Quick pick an upcoming fixture", options, key="predict_pick",
                            format_func=lambda mid: "—" if mid is None else
                            f"MD {by_id[mid]['matchday']} · {teams[by_id[mid]['home_id']]['name']} vs {teams[by_id[mid]['away_id']]['name']}")
        if pick and st.session_state.get("predict_last_pick") != pick:
            st.session_state.predict_home, st.session_state.predict_away = by_id[pick]["home_id"], by_id[pick]["away_id"]
        st.session_state.predict_last_pick = pick

    home_default = st.session_state.get("predict_home") if st.session_state.get("predict_home") in ids else ids[0]
    away_default = st.session_state.get("predict_away") if st.session_state.get("predict_away") in ids else ids[1]
    c1, c2 = st.columns(2)
    home_id = c1.selectbox("Home team", ids, index=ids.index(home_default), format_func=lambda t: teams[t]["name"])
    away_choices = [t for t in ids if t != home_id]
    away_id = c2.selectbox("Away team", away_choices,
                           index=away_choices.index(away_default) if away_default in away_choices else 0,
                           format_func=lambda t: teams[t]["name"])
    st.session_state.predict_home, st.session_state.predict_away = home_id, away_id
    home, away = teams[home_id]["name"], teams[away_id]["name"]

    with st.expander("🎛️ What-if: tweak the inputs", expanded=True):
        w1, w2 = st.columns(2)
        window = w1.slider("Recent matches to use", 3, 20, 10, help="How many recent games define each team's form.")
        default_ha = round(default_home_advantage(matches) * 100)
        home_adv = w2.slider("Home advantage (%)", 0, 60, default_ha, help=f"League average is {default_ha} %.") / 100
        s1, s2, s3, s4 = st.columns(4)
        home_attack = s1.slider(f"{teams[home_id]['short']} attack", 0.5, 1.5, 1.0, 0.05, help="1.0 = current form. Try 0.8 for an injured striker.")
        home_defence = s2.slider(f"{teams[home_id]['short']} defence", 0.5, 1.5, 1.0, 0.05, help="Above 1.0 = tighter defence.")
        away_attack = s3.slider(f"{teams[away_id]['short']} attack", 0.5, 1.5, 1.0, 0.05)
        away_defence = s4.slider(f"{teams[away_id]['short']} defence", 0.5, 1.5, 1.0, 0.05)

    base = predict(matches, home_id, away_id, window=window)
    what_if = predict(matches, home_id, away_id, window=window, home_advantage=home_adv, home_attack=home_attack,
                      home_defence=home_defence, away_attack=away_attack, away_defence=away_defence)

    st.plotly_chart(probability_gauges(home, away, what_if.home_win, what_if.draw, what_if.away_win), width="stretch", theme=None)
    st.plotly_chart(probability_bar(home, away, what_if.home_win, what_if.draw, what_if.away_win), width="stretch", theme=None)

    k1, k2, k3, k4 = st.columns(4)
    k1.markdown(kpi(f"{teams[home_id]['short']} expected goals", f"{what_if.home_xg:.2f}", f"model alone: {base.home_xg:.2f}"), unsafe_allow_html=True)
    k2.markdown(kpi(f"{teams[away_id]['short']} expected goals", f"{what_if.away_xg:.2f}", f"model alone: {base.away_xg:.2f}"), unsafe_allow_html=True)
    k3.markdown(kpi(f"{teams[home_id]['short']} win change", f"{(what_if.home_win - base.home_win) * 100:+.1f} pts", "vs model alone"), unsafe_allow_html=True)
    top = what_if.top_scorelines(1)[0]
    k4.markdown(kpi("Most likely score", f"{top[0]}–{top[1]}", f"{top[2]:.1%} chance"), unsafe_allow_html=True)

    left, right = st.columns([3, 2])
    with left:
        st.plotly_chart(scoreline_heatmap(what_if.matrix, home, away), width="stretch", theme=None)
    with right:
        html('<div class="ps-section-title">Top 5 scorelines</div>')
        for h, a, p in what_if.top_scorelines(5):
            st.progress(min(1.0, p / max(0.0001, top[2])), text=f"{home} {h}–{a} {away} · {p:.1%}")
        hs, as_ = team_strength(matches, home_id, window), team_strength(matches, away_id, window)
        st.caption(f"Form strengths (1.0 = league average). {home}: attack {hs.attack:.2f}, defence {hs.defence:.2f} "
                   f"over {hs.games} games. {away}: attack {as_.attack:.2f}, defence {as_.defence:.2f} over {as_.games} games.")

    with st.expander("How does the model work?"):
        st.markdown(
            "- Each team's **attack** = goals scored per game in its recent matches, divided by the league average. "
            "**Defence** = goals conceded per game, divided by the league average (lower is better).\n"
            "- Small samples are pulled toward average, so one freak result doesn't dominate.\n"
            "- **Expected goals** = league average × own attack × opponent's defence, adjusted for home advantage.\n"
            "- Each team's goals follow a **Poisson distribution**; combining both gives the chance of every scoreline, "
            "and summing those gives win/draw/loss.\n"
            "- It's a teaching model: it ignores injuries, schedule and transfers. Use the sliders to add what it can't see.")
