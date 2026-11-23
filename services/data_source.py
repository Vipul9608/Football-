"""Data sources: the offline demo dataset and API-Football.

Both sources return the same plain-dict shapes (see the TypedDicts below), so the views never
care where the data came from. This module does not import Streamlit, so it is unit-testable;
caching lives in services/api.py.
"""
from __future__ import annotations

import hashlib
import json
import re
import time as clock
from datetime import datetime, time, timedelta, timezone
from pathlib import Path
from typing import Any, Callable, Protocol, TypedDict

import requests

DEMO_PATH = Path(__file__).resolve().parent.parent / "data" / "sample" / "demo.json"
API_BASE_URL = "https://v3.football.api-sports.io"
HALF_TIME_BREAK_MIN = 15
FULL_MATCH_SPAN_MIN = 90 + HALF_TIME_BREAK_MIN

# Status vocabulary used everywhere in the app.
SCHEDULED, LIVE, FINISHED, POSTPONED = "SCHEDULED", "LIVE", "FINISHED", "POSTPONED"


class League(TypedDict):
    id: int
    name: str
    country: str
    logo: str | None
    zones: dict[str, int]  # how many places are "top", "europe" and "relegation"


class Team(TypedDict):
    id: int
    name: str
    short: str
    league_id: int
    crest: str | None
    primary: str
    secondary: str


class Match(TypedDict):
    id: int
    league_id: int
    matchday: int
    kickoff: str  # ISO 8601, UTC
    status: str
    minute: str | None  # "34'", "HT", or None
    home_id: int
    away_id: int
    home_goals: int | None
    away_goals: int | None


class Player(TypedDict):
    id: int
    name: str
    team_id: int
    position: str  # GK, DF, MF, FW
    number: int | None
    age: int | None
    nationality: str | None
    photo: str | None
    stats: dict[str, float]


class DataSource(Protocol):
    """What every data source must provide."""

    name: str

    def leagues(self) -> list[League]: ...
    def teams(self, league_id: int) -> list[Team]: ...
    def matches(self, league_id: int) -> list[Match]: ...
    def players(self, league_id: int) -> list[Player]: ...
    def squad(self, team_id: int) -> list[Player]: ...
    def match_detail(self, match: Match) -> dict[str, Any]: ...


class ApiError(RuntimeError):
    """The live API failed (bad key, rate limit, network). The app falls back to demo data."""


# ---------------------------------------------------------------- shared helpers

def match_clock(elapsed_min: float) -> tuple[str, int]:
    """Turn minutes since kickoff into a clock label and the last minute that has been played.

    0-45 -> first half, 45-60 -> half time, then the second half (capped at 90).
    """
    if elapsed_min <= 45:
        minute = max(1, int(elapsed_min) + 1)
        return f"{minute}'", minute
    if elapsed_min < 45 + HALF_TIME_BREAK_MIN:
        return "HT", 45
    minute = min(90, int(elapsed_min - HALF_TIME_BREAK_MIN) + 1)
    return f"{minute}'", minute


def team_colors(team_id: int) -> tuple[str, str]:
    """A stable colour pair for teams that have no colours in the API."""
    palette = ["#D7263D", "#1B98E0", "#2A9D8F", "#F4A261", "#6A0572", "#E76F51", "#3A86FF", "#06D6A0"]
    digest = int(hashlib.md5(str(team_id).encode()).hexdigest(), 16)
    return palette[digest % len(palette)], "#FFFFFF"


def short_name(name: str) -> str:
    """Three-letter code from a club name: 'Harbor City' -> 'HAR'."""
    letters = re.sub(r"[^A-Za-z]", "", name)
    return (letters[:3] or "???").upper()


# ---------------------------------------------------------------- demo source

class DemoSource:
    """The bundled fictional dataset. Live games advance in real time from app start."""

    name = "demo"

    def __init__(self, path: Path = DEMO_PATH, now: Callable[[], datetime] | None = None,
                 started_at: datetime | None = None) -> None:
        self._data = json.loads(path.read_text(encoding="utf-8"))
        self._now = now or (lambda: datetime.now(timezone.utc))
        self._started_at = started_at or self._now()
        self._raw_matches = {m["id"]: m for m in self._data["matches"]}

    def leagues(self) -> list[League]:
        return list(self._data["leagues"])

    def teams(self, league_id: int) -> list[Team]:
        return [t for t in self._data["teams"] if t["league_id"] == league_id]

    def matches(self, league_id: int) -> list[Match]:
        return [self._resolve(m) for m in self._data["matches"] if m["league_id"] == league_id]

    def players(self, league_id: int) -> list[Player]:
        team_ids = {t["id"] for t in self.teams(league_id)}
        return [p for p in self._data["players"] if p["team_id"] in team_ids]

    def squad(self, team_id: int) -> list[Player]:
        return [p for p in self._data["players"] if p["team_id"] == team_id]

    def match_detail(self, match: Match) -> dict[str, Any]:
        raw = self._raw_matches[match["id"]]
        if "lineups" not in raw or match["status"] == SCHEDULED:
            return {"lineups": None, "events": [], "stats": {}}
        played = self._played_minutes(raw)
        players = {p["id"]: p for p in self._data["players"]}
        lineups = {side: _demo_lineup(raw["lineups"][side], players) for side in ("home", "away")}
        events = [e | {"extra": None} for e in raw["events"] if e["minute"] <= played]
        share = played / 90
        stats = {key: ([round(v * share) for v in pair] if key != "possession" else pair)
                 for key, pair in raw["stats"].items()}
        return {"lineups": lineups, "events": events, "stats": stats}

    # -- internals

    def _kickoff(self, raw: dict) -> datetime:
        if "start_offset_min" in raw:
            return self._started_at + timedelta(minutes=raw["start_offset_min"])
        hour, minute = (int(x) for x in raw["time"].split(":"))
        day = self._started_at.date() + timedelta(days=raw["day_offset"])
        return datetime.combine(day, time(hour, minute), tzinfo=timezone.utc)

    def _played_minutes(self, raw: dict) -> int:
        elapsed = (self._now() - self._kickoff(raw)).total_seconds() / 60
        if elapsed < 0:
            return 0
        if elapsed >= FULL_MATCH_SPAN_MIN:
            return 90
        return match_clock(elapsed)[1]

    def _resolve(self, raw: dict) -> Match:
        kickoff = self._kickoff(raw)
        elapsed = (self._now() - kickoff).total_seconds() / 60
        status, minute, played = SCHEDULED, None, 0
        if "events" in raw and elapsed >= FULL_MATCH_SPAN_MIN:
            status, played = FINISHED, 90
        elif "events" in raw and elapsed >= 0:
            status = LIVE
            minute, played = match_clock(elapsed)
        goals = {"home": None, "away": None}
        if status != SCHEDULED:
            scoring = [e for e in raw["events"] if e["type"] in ("goal", "penalty", "own_goal") and e["minute"] <= played]
            goals = {side: sum(1 for e in scoring if e["side"] == side) for side in ("home", "away")}
        return {"id": raw["id"], "league_id": raw["league_id"], "matchday": raw["matchday"],
                "kickoff": kickoff.isoformat(), "status": status, "minute": minute,
                "home_id": raw["home_id"], "away_id": raw["away_id"],
                "home_goals": goals["home"], "away_goals": goals["away"]}


def _demo_lineup(lineup: dict, players: dict[int, dict]) -> dict:
    def entry(pid: int) -> dict:
        p = players[pid]
        return {"id": pid, "name": p["name"], "number": p["number"], "position": p["position"]}
    return {"formation": lineup["formation"],
            "start_xi": [entry(pid) for pid in lineup["start_xi"]],
            "bench": [entry(pid) for pid in lineup["bench"]]}


# ---------------------------------------------------------------- API-Football source

KNOWN_LEAGUES = {
    39: ("Premier League", "England"), 140: ("La Liga", "Spain"), 78: ("Bundesliga", "Germany"),
    135: ("Serie A", "Italy"), 61: ("Ligue 1", "France"), 88: ("Eredivisie", "Netherlands"),
    94: ("Primeira Liga", "Portugal"),
}
LIVE_CODES = {"1H", "HT", "2H", "ET", "BT", "P", "LIVE", "INT"}
FINISHED_CODES = {"FT", "AET", "PEN"}
SCHEDULED_CODES = {"NS", "TBD"}
POSITION_CODES = {"Goalkeeper": "GK", "Defender": "DF", "Midfielder": "MF", "Attacker": "FW",
                  "G": "GK", "D": "DF", "M": "MF", "F": "FW"}
MAX_PLAYER_PAGES = 3  # each page is 20 players and costs one request


def map_fixture_status(short: str) -> str:
    if short in LIVE_CODES:
        return LIVE
    if short in FINISHED_CODES:
        return FINISHED
    if short in SCHEDULED_CODES:
        return SCHEDULED
    return POSTPONED


def parse_matchday(round_name: str) -> int:
    """'Regular Season - 15' -> 15. Rounds without a number count as 0."""
    found = re.search(r"(\d+)\s*$", round_name or "")
    return int(found.group(1)) if found else 0


def map_fixture(item: dict) -> Match:
    """One API-Football fixture -> our Match shape."""
    fixture, status = item["fixture"], item["fixture"]["status"]
    mapped = map_fixture_status(status["short"])
    minute = None
    if mapped == LIVE:
        minute = "HT" if status["short"] == "HT" else f"{status.get('elapsed') or 0}'"
    return {"id": fixture["id"], "league_id": item["league"]["id"],
            "matchday": parse_matchday(item["league"].get("round", "")),
            "kickoff": fixture["date"], "status": mapped, "minute": minute,
            "home_id": item["teams"]["home"]["id"], "away_id": item["teams"]["away"]["id"],
            "home_goals": item["goals"]["home"], "away_goals": item["goals"]["away"]}


def map_event(item: dict, home_id: int) -> dict | None:
    """One API-Football event -> our event shape (or None for VAR notes and the like)."""
    kind, detail = item.get("type"), item.get("detail") or ""
    if kind == "Goal":
        event_type = "own_goal" if "Own" in detail else "penalty" if "Penalty" in detail else "goal"
        if "Missed" in detail:
            return None
    elif kind == "Card":
        event_type = "red" if "Red" in detail else "yellow"
    elif kind == "subst":
        event_type = "sub"
    else:
        return None
    return {"minute": item["time"]["elapsed"] or 0, "extra": item["time"].get("extra"),
            "side": "home" if item["team"]["id"] == home_id else "away", "type": event_type,
            "player": (item.get("player") or {}).get("name") or "Unknown",
            "assist": (item.get("assist") or {}).get("name")}


def map_player(item: dict) -> Player | None:
    """One /players entry (person + first statistics block) -> our Player shape."""
    person, blocks = item["player"], item.get("statistics") or []
    if not blocks:
        return None
    s = blocks[0]

    def num(section: str, key: str) -> float:
        return float((s.get(section) or {}).get(key) or 0)

    return {"id": person["id"], "name": person["name"], "team_id": s["team"]["id"],
            "position": POSITION_CODES.get((s.get("games") or {}).get("position") or "", "MF"),
            "number": (s.get("games") or {}).get("number"), "age": person.get("age"),
            "nationality": person.get("nationality"), "photo": person.get("photo"),
            "stats": {"appearances": num("games", "appearences"), "minutes": num("games", "minutes"),
                      "goals": num("goals", "total"), "assists": num("goals", "assists"),
                      "shots": num("shots", "total"), "key_passes": num("passes", "key"),
                      "passes": num("passes", "total"), "pass_accuracy": num("passes", "accuracy"),
                      "tackles": num("tackles", "total"), "interceptions": num("tackles", "interceptions"),
                      "dribbles": num("dribbles", "success"), "saves": num("goals", "saves"),
                      "yellow": num("cards", "yellow"), "red": num("cards", "red"),
                      "rating": round(float((s.get("games") or {}).get("rating") or 0), 2)}}


def map_statistics(response: list[dict], home_id: int) -> dict[str, list[int]]:
    """/fixtures/statistics -> {'possession': [h, a], 'shots': [h, a], ...}."""
    wanted = {"Ball Possession": "possession", "Total Shots": "shots", "Shots on Goal": "shots_on_target",
              "Corner Kicks": "corners", "Fouls": "fouls"}
    result: dict[str, list[int]] = {}
    for block in response:
        index = 0 if block["team"]["id"] == home_id else 1
        for stat in block.get("statistics", []):
            key = wanted.get(stat["type"])
            if key:
                value = int(str(stat["value"] or 0).rstrip("%") or 0)
                result.setdefault(key, [0, 0])[index] = value
    return result


class ApiFootballSource:
    """Live data from API-Football (api-sports.io). Every public method may raise ApiError."""

    name = "api"

    def __init__(self, api_key: str, season: int, league_ids: list[int],
                 session: requests.Session | None = None, timeout: float = 10.0) -> None:
        self._key, self._season, self._league_ids = api_key, season, league_ids
        self._session = session or requests.Session()
        self._timeout = timeout
        self._memo: dict[tuple, tuple[float, list]] = {}

    def leagues(self) -> list[League]:
        result = []
        for league_id in self._league_ids:
            name, country = KNOWN_LEAGUES.get(league_id, (f"League {league_id}", ""))
            result.append({"id": league_id, "name": name, "country": country,
                           "logo": f"https://media.api-sports.io/football/leagues/{league_id}.png",
                           "zones": {"top": 4, "europe": 2, "relegation": 3}})
        return result

    def teams(self, league_id: int) -> list[Team]:
        seen: dict[int, Team] = {}
        for item in self._fixtures(league_id):
            for side in ("home", "away"):
                t = item["teams"][side]
                if t["id"] not in seen:
                    primary, secondary = team_colors(t["id"])
                    seen[t["id"]] = {"id": t["id"], "name": t["name"], "short": short_name(t["name"]),
                                     "league_id": league_id, "crest": t.get("logo"),
                                     "primary": primary, "secondary": secondary}
        return sorted(seen.values(), key=lambda t: t["name"])

    def matches(self, league_id: int) -> list[Match]:
        return [map_fixture(item) for item in self._fixtures(league_id)]

    def players(self, league_id: int) -> list[Player]:
        result: list[Player] = []
        for page in range(1, MAX_PLAYER_PAGES + 1):
            body = self._get_body("/players", ttl=86400, league=league_id, season=self._season, page=page)
            result += [p for p in (map_player(item) for item in body.get("response", [])) if p]
            if page >= (body.get("paging") or {}).get("total", 1):
                break
        return result

    def squad(self, team_id: int) -> list[Player]:
        response = self._get("/players/squads", ttl=86400, team=team_id)
        if not response:
            return []
        return [{"id": p["id"], "name": p["name"], "team_id": team_id,
                 "position": POSITION_CODES.get(p.get("position") or "", "MF"), "number": p.get("number"),
                 "age": p.get("age"), "nationality": None, "photo": p.get("photo"), "stats": {}}
                for p in response[0].get("players", [])]

    def match_detail(self, match: Match) -> dict[str, Any]:
        ttl = 60 if match["status"] == LIVE else 86400
        fixture = match["id"]
        lineups_raw = self._get("/fixtures/lineups", ttl=ttl, fixture=fixture)
        events_raw = self._get("/fixtures/events", ttl=ttl, fixture=fixture)
        stats_raw = self._get("/fixtures/statistics", ttl=ttl, fixture=fixture)
        lineups = None
        if len(lineups_raw) == 2:
            lineups = {}
            for block in lineups_raw:
                side = "home" if block["team"]["id"] == match["home_id"] else "away"
                lineups[side] = {"formation": block.get("formation") or "4-4-2",
                                 "start_xi": [_api_lineup_entry(x) for x in block.get("startXI", [])],
                                 "bench": [_api_lineup_entry(x) for x in block.get("substitutes", [])]}
        events = [e for e in (map_event(x, match["home_id"]) for x in events_raw) if e]
        return {"lineups": lineups, "events": events, "stats": map_statistics(stats_raw, match["home_id"])}

    # -- internals

    def _fixtures(self, league_id: int) -> list[dict]:
        return self._get("/fixtures", ttl=60, league=league_id, season=self._season)

    def _get(self, path: str, ttl: int, **params: Any) -> list:
        return self._get_body(path, ttl, **params).get("response", [])

    def _get_body(self, path: str, ttl: int, **params: Any) -> dict:
        """GET with a small in-process memo, so teams() and matches() share one request."""
        key = (path, tuple(sorted(params.items())))
        cached = self._memo.get(key)
        if cached and clock.monotonic() - cached[0] < ttl:
            return cached[1]  # type: ignore[return-value]
        try:
            response = self._session.get(API_BASE_URL + path, params=params, timeout=self._timeout,
                                         headers={"x-apisports-key": self._key})
        except requests.RequestException as error:
            raise ApiError(f"Network problem while calling API-Football: {error}") from error
        if response.status_code == 429:
            raise ApiError("API-Football rate limit reached. Try again in a minute.")
        if response.status_code >= 400:
            raise ApiError(f"API-Football answered with HTTP {response.status_code}.")
        body = response.json()
        errors = body.get("errors")
        if errors:  # API-Football reports bad keys and daily limits with HTTP 200 + an errors object
            raise ApiError(f"API-Football error: {errors}")
        self._memo[key] = (clock.monotonic(), body)
        return body


def _api_lineup_entry(item: dict) -> dict:
    p = item["player"]
    return {"id": p["id"], "name": p["name"], "number": p.get("number"),
            "position": POSITION_CODES.get(p.get("pos") or "", "MF")}
