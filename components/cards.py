"""Small HTML building blocks: match cards, KPI tiles, form dots, banners, skeletons."""
from __future__ import annotations

from datetime import datetime
from html import escape

import streamlit as st

from components.media import crest_html


def html(markup: str) -> None:
    """Render trusted, already-escaped HTML."""
    st.markdown(markup, unsafe_allow_html=True)


def kickoff_label(iso: str, with_date: bool = True) -> str:
    """'Sat 14 Dec · 15:00' in the viewer's (server's) local time."""
    moment = datetime.fromisoformat(iso.replace("Z", "+00:00")).astimezone()
    return moment.strftime("%a %d %b · %H:%M") if with_date else moment.strftime("%H:%M")


RESULT_NAMES = {"W": "Win", "D": "Draw", "L": "Loss"}


def form_dots(form: list[str]) -> str:
    dots = "".join(f'<span class="ps-dot {r}" title="{RESULT_NAMES[r]}">{r}</span>' for r in form)
    return f'<span class="ps-form">{dots or "<span class=ps-muted>–</span>"}</span>'


def live_badge(minute: str | None) -> str:
    return f'<span class="ps-live">LIVE {escape(minute or "")}</span>'


def match_card(match: dict, home: dict, away: dict, league_name: str = "", favorites: set[int] | None = None) -> str:
    """One match as a card: status line, both teams with crests, and the score or kickoff time."""
    favorites = favorites or set()
    status = match["status"]
    if status == "LIVE":
        right = live_badge(match["minute"])
        score = f'<div class="ps-score live">{match["home_goals"]} – {match["away_goals"]}</div>'
    elif status == "FINISHED":
        right = '<span class="ps-pill">FT</span>'
        score = f'<div class="ps-score">{match["home_goals"]} – {match["away_goals"]}</div>'
    elif status == "POSTPONED":
        right = '<span class="ps-pill">Postponed</span>'
        score = '<div class="ps-score upcoming">–</div>'
    else:
        right = f'<span class="ps-pill">{escape(kickoff_label(match["kickoff"]))}</span>'
        score = f'<div class="ps-score upcoming">{escape(kickoff_label(match["kickoff"], with_date=False))}</div>'
    meta_left = escape(league_name) + (f" · MD {match['matchday']}" if match.get("matchday") else "")

    def team(t: dict, side: str) -> str:
        fav = " fav" if t["id"] in favorites else ""
        return f'<div class="ps-team {side}{fav}">{crest_html(t)}<span class="name">{escape(t["name"])}</span></div>'

    live_class = " is-live" if status == "LIVE" else ""
    return (f'<div class="ps-card{live_class}"><div class="ps-match">'
            f'<div class="meta"><span>{meta_left}</span>{right}</div>'
            f'{team(home, "home")}{score}{team(away, "away")}</div></div>')


def kpi(label: str, value: str, sub: str = "") -> str:
    return (f'<div class="ps-card ps-kpi"><div class="label">{escape(label)}</div>'
            f'<div class="value">{escape(value)}</div><div class="sub">{escape(sub)}</div></div>')


def section_title(text: str, pill: str = "") -> None:
    pill_html = f'<span class="ps-pill">{escape(pill)}</span>' if pill else ""
    html(f'<div class="ps-section-title">{escape(text)} {pill_html}</div>')


def banner(markup: str, warn: bool = False) -> None:
    html(f'<div class="ps-banner{" warn" if warn else ""}">{markup}</div>')


def skeleton(count: int = 3) -> str:
    return "".join('<div class="ps-skeleton"></div>' for _ in range(count))


def empty_state(text: str) -> None:
    html(f'<div class="ps-card" style="text-align:center;color:var(--muted)">{escape(text)}</div>')
