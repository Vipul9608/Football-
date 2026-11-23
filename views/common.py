"""Helpers shared by the views: favourites, navigation, the selected league, match grids."""
from __future__ import annotations

from datetime import datetime

import streamlit as st

from components.cards import html, match_card
from services import api
from services.favorites import toggle


# ---------------------------------------------------------------- favourites (session state)

def favorites() -> set[int]:
    return set(st.session_state.setdefault("favorites", []))


def set_favorites(team_ids: set[int] | list[int]) -> None:
    st.session_state.favorites = sorted(set(team_ids))


def toggle_favorite(team_id: int) -> None:
    set_favorites(toggle(favorites(), team_id))


# ---------------------------------------------------------------- navigation

def navigate(page: str, **state: object) -> None:
    """Jump to another page, optionally passing state such as match_id=123."""
    for key, value in state.items():
        st.session_state[key] = value
    st.session_state.nav_to = page
    st.rerun()


def selected_league_id() -> int:
    ids = [lg["id"] for lg in api.leagues()]
    current = st.session_state.get("league_id")
    return current if current in ids else ids[0]


# ---------------------------------------------------------------- matches

def is_today(match: dict) -> bool:
    kickoff = datetime.fromisoformat(match["kickoff"].replace("Z", "+00:00")).astimezone()
    return kickoff.date() == datetime.now().astimezone().date()


def match_label(match: dict, teams: dict[int, dict]) -> str:
    home, away = teams[match["home_id"]]["name"], teams[match["away_id"]]["name"]
    if match["status"] in ("LIVE", "FINISHED"):
        state = "LIVE " + (match["minute"] or "") if match["status"] == "LIVE" else "FT"
        return f"MD {match['matchday']} · {home} {match['home_goals']}–{match['away_goals']} {away} ({state})"
    return f"MD {match['matchday']} · {home} vs {away}"


def match_grid(matches: list[dict], teams: dict[int, dict], league_name: str = "",
               columns: int = 2, key: str = "grid", button: bool = True) -> None:
    """Match cards in a responsive grid, each with an optional 'Match center' button."""
    favs = favorites()
    for start in range(0, len(matches), columns):
        cols = st.columns(columns)
        for col, match in zip(cols, matches[start:start + columns]):
            home, away = teams.get(match["home_id"]), teams.get(match["away_id"])
            if not home or not away:
                continue
            with col:
                html(match_card(match, home, away, league_name, favs))
                if button and match["status"] != "SCHEDULED":
                    if st.button("Match center →", key=f"{key}-{match['id']}", width="stretch"):
                        navigate("Match Center", match_id=match["id"], league_id=match["league_id"])
                elif button:
                    if st.button("Predict →", key=f"{key}-p-{match['id']}", width="stretch"):
                        navigate("Predictor", predict_home=match["home_id"], predict_away=match["away_id"],
                                 league_id=match["league_id"])
