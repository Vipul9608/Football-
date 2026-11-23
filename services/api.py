"""Streamlit-facing data layer: picks the data source, caches every call, falls back to demo.

Views call only the functions in this module. If the live API fails (bad key, daily limit,
network), the session switches to demo mode, remembers why, and the app shows a banner.
"""
from __future__ import annotations

import os
from typing import Any, Callable, TypeVar

import streamlit as st

from .data_source import ApiError, ApiFootballSource, DataSource, DemoSource, League, Match, Player, Team

T = TypeVar("T")
DEMO, API = "demo", "api"


# ---------------------------------------------------------------- configuration

def _setting(name: str, default: str = "") -> str:
    """A setting from st.secrets (Streamlit Cloud, local secrets.toml) or the environment (Docker)."""
    try:
        if name in st.secrets:
            return str(st.secrets[name]).strip()
    except Exception:  # no secrets.toml at all
        pass
    return os.environ.get(name, default).strip()


def api_settings() -> dict[str, Any] | None:
    """API-Football settings, or None when no key is configured (then the app runs in demo mode)."""
    key = _setting("API_FOOTBALL_KEY")
    if not key:
        return None
    try:
        leagues = tuple(int(x) for x in _setting("API_FOOTBALL_LEAGUES", "39,140").split(",") if x.strip())
        return {"key": key, "season": int(_setting("API_FOOTBALL_SEASON", "2023")), "leagues": leagues or (39,)}
    except ValueError:  # malformed season or league list
        return None


def mode() -> str:
    """'api' when a key exists and the user has not switched to (or fallen back to) demo."""
    if "data_mode" not in st.session_state:
        st.session_state.data_mode = API if api_settings() else DEMO
    return st.session_state.data_mode


def set_mode(new_mode: str) -> None:
    st.session_state.data_mode = new_mode if (new_mode == DEMO or api_settings()) else DEMO
    st.session_state.pop("fallback_reason", None)


def fallback_reason() -> str | None:
    return st.session_state.get("fallback_reason")


@st.cache_resource(show_spinner=False)
def _demo_source() -> DemoSource:
    return DemoSource()


@st.cache_resource(show_spinner=False)
def _api_source(key: str, season: int, leagues: tuple[int, ...]) -> ApiFootballSource:
    return ApiFootballSource(key, season, list(leagues))


def _source(data_mode: str) -> DataSource:
    settings = api_settings()
    if data_mode == API and settings:
        return _api_source(settings["key"], settings["season"], settings["leagues"])
    return _demo_source()


def _guard(loader: Callable[..., T], *args: Any) -> T:
    """Run a cached loader; on an API failure switch this session to demo mode and rerun."""
    current = mode()
    try:
        return loader(current, *args)
    except ApiError as error:
        if current == DEMO:
            raise
        st.session_state.data_mode = DEMO
        st.session_state.fallback_reason = str(error)
        st.rerun()
        raise  # unreachable: st.rerun() stops the script


# ---------------------------------------------------------------- cached loaders
# The first argument is the data mode, so demo and API results never share a cache entry.

@st.cache_data(ttl=3600, show_spinner=False)
def _leagues(data_mode: str) -> list[League]:
    return _source(data_mode).leagues()


@st.cache_data(ttl=600, show_spinner=False)
def _teams(data_mode: str, league_id: int) -> list[Team]:
    return _source(data_mode).teams(league_id)


@st.cache_data(ttl=60, show_spinner=False)
def _matches(data_mode: str, league_id: int) -> list[Match]:
    return _source(data_mode).matches(league_id)


@st.cache_data(ttl=86400, show_spinner=False)
def _players(data_mode: str, league_id: int) -> list[Player]:
    return _source(data_mode).players(league_id)


@st.cache_data(ttl=86400, show_spinner=False)
def _squad(data_mode: str, team_id: int) -> list[Player]:
    return _source(data_mode).squad(team_id)


@st.cache_data(ttl=60, show_spinner=False)
def _live_detail(data_mode: str, match: Match) -> dict[str, Any]:
    return _source(data_mode).match_detail(match)


@st.cache_data(ttl=86400, show_spinner=False)
def _final_detail(data_mode: str, match: Match) -> dict[str, Any]:
    return _source(data_mode).match_detail(match)


# ---------------------------------------------------------------- public API for the views

def leagues() -> list[League]:
    return _guard(_leagues)


def league(league_id: int) -> League:
    return next((lg for lg in leagues() if lg["id"] == league_id), leagues()[0])


def teams(league_id: int) -> list[Team]:
    return _guard(_teams, league_id)


def team_map(league_id: int) -> dict[int, Team]:
    return {t["id"]: t for t in teams(league_id)}


def all_teams() -> dict[int, Team]:
    """Every team in every configured league, keyed by id."""
    result: dict[int, Team] = {}
    for lg in leagues():
        result |= team_map(lg["id"])
    return result


def matches(league_id: int) -> list[Match]:
    return _guard(_matches, league_id)


def all_matches() -> list[Match]:
    return [m for lg in leagues() for m in matches(lg["id"])]


def players(league_id: int) -> list[Player]:
    return _guard(_players, league_id)


def squad(team_id: int) -> list[Player]:
    return _guard(_squad, team_id)


def match_detail(match: Match) -> dict[str, Any]:
    loader = _live_detail if match["status"] == "LIVE" else _final_detail
    return _guard(loader, match)
