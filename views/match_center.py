"""Match center: scoreboard, line-ups on a pitch, event timeline and team stats."""
from __future__ import annotations

from html import escape

import streamlit as st

from components.cards import empty_state, html, kickoff_label, live_badge
from components.charts import event_timeline, stat_bars
from components.media import crest_html
from components.pitch import pitch_figure
from services import api
from views.common import match_label, navigate, selected_league_id

EVENT_ICONS = {"goal": "⚽", "penalty": "⚽ (P)", "own_goal": "⚽ (OG)", "sub": "🔁"}


def render() -> None:
    st.markdown("## Match center")
    league_id = selected_league_id()
    matches, teams = api.matches(league_id), api.team_map(league_id)
    candidates = sorted((m for m in matches if m["status"] in ("LIVE", "FINISHED")),
                        key=lambda m: (m["status"] != "LIVE", m["kickoff"]), reverse=False)
    live_first = [m for m in candidates if m["status"] == "LIVE"] + \
                 sorted((m for m in candidates if m["status"] == "FINISHED"), key=lambda m: m["kickoff"], reverse=True)
    if not live_first:
        empty_state("No live or finished matches in this league yet.")
        return
    ids = [m["id"] for m in live_first]
    wanted = st.session_state.get("match_id")
    index = ids.index(wanted) if wanted in ids else 0
    by_id = {m["id"]: m for m in live_first}
    match_id = st.selectbox("Match", ids, index=index, format_func=lambda mid: match_label(by_id[mid], teams))
    st.session_state.match_id = match_id
    match = by_id[match_id]
    run_every = 60 if match["status"] == "LIVE" else None
    st.fragment(run_every=run_every)(_match_body)(match_id, league_id)


def _match_body(match_id: int, league_id: int) -> None:
    """Re-runs every 60 s while the match is live."""
    match = next(m for m in api.matches(league_id) if m["id"] == match_id)
    teams = api.team_map(league_id)
    home, away = teams[match["home_id"]], teams[match["away_id"]]
    with st.spinner("Loading match details…"):
        detail = api.match_detail(match)

    status = live_badge(match["minute"]) if match["status"] == "LIVE" else '<span class="ps-pill">Full time</span>'
    html(f'<div class="ps-card"><div class="ps-match"><div class="meta"><span>{escape(api.league(league_id)["name"])} · '
         f'Matchday {match["matchday"]} · {escape(kickoff_label(match["kickoff"]))}</span>{status}</div>'
         f'<div class="ps-team home">{crest_html(home, large=True)}<span class="name" style="font-size:1.2rem">{escape(home["name"])}</span></div>'
         f'<div class="ps-score {"live" if match["status"] == "LIVE" else ""}" style="font-size:2.4rem">'
         f'{match["home_goals"]} – {match["away_goals"]}</div>'
         f'<div class="ps-team away">{crest_html(away, large=True)}<span class="name" style="font-size:1.2rem">{escape(away["name"])}</span></div>'
         f'</div></div>')
    st.write("")

    lineup_tab, timeline_tab, stats_tab = st.tabs(["Line-ups", "Timeline", "Stats"])
    with lineup_tab:
        if detail.get("lineups"):
            st.plotly_chart(pitch_figure(detail["lineups"], home, away), width="stretch", theme=None)
            c1, c2 = st.columns(2)
            for col, side, team in ((c1, "home", home), (c2, "away", away)):
                bench = detail["lineups"][side]["bench"]
                col.markdown(f"**{team['name']} bench**")
                col.caption(" · ".join(f"{p.get('number') or ''} {p['name']}" for p in bench) or "–")
        else:
            empty_state("Line-ups are not available for this match.")
    with timeline_tab:
        events = detail.get("events", [])
        if events:
            minute_now = 90 if match["status"] == "FINISHED" else max((e["minute"] for e in events), default=0)
            if match["status"] == "LIVE" and (match["minute"] or "").rstrip("'").isdigit():
                minute_now = int(match["minute"].rstrip("'"))
            st.plotly_chart(event_timeline(events, home["name"], away["name"], minute_now), width="stretch", theme=None)
            html(_timeline_html(events))
        else:
            empty_state("No events yet.")
    with stats_tab:
        stats = detail.get("stats") or {}
        if stats:
            away_color = away["primary"] if away["primary"].lower() != home["primary"].lower() else away["secondary"]
            st.plotly_chart(stat_bars(stats, home["name"], away["name"], home["primary"], away_color), width="stretch", theme=None)
        else:
            empty_state("Team statistics are not available for this match.")
    if st.button("Predict the return fixture →"):
        navigate("Predictor", predict_home=match["away_id"], predict_away=match["home_id"], league_id=league_id)


def _timeline_html(events: list[dict]) -> str:
    rows = []
    for e in sorted(events, key=lambda e: (e["minute"], e.get("extra") or 0)):
        if e["type"] in ("yellow", "red"):
            icon = f'<span class="ps-card-icon {e["type"]}"></span>'
        else:
            icon = f'<span class="icon">{EVENT_ICONS.get(e["type"], "•")}</span>'
        extra = ""
        if e["type"] == "sub" and e.get("assist"):
            extra = f'<div class="sub">off: {escape(e["assist"])}</div>'
        elif e.get("assist"):
            extra = f'<div class="sub">assist: {escape(e["assist"])}</div>'
        body = f'{icon}<span class="who">{escape(e["player"])}</span>{extra}'
        minute = f'{e["minute"]}{"+" + str(e["extra"]) if e.get("extra") else ""}\''
        home_cell, away_cell = (body, "") if e["side"] == "home" else ("", body)
        rows.append(f'<div class="ps-event"><div class="home">{home_cell}</div><div class="min">{minute}</div>'
                    f'<div class="away">{away_cell}</div></div>')
    return f'<div class="ps-card ps-timeline">{"".join(rows)}</div>'
