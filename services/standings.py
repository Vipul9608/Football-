"""League table maths: standings, form guide, zones, and points per matchday."""
from __future__ import annotations

from collections.abc import Iterable, Mapping
from typing import TypedDict

from .data_source import FINISHED, Match


class TableRow(TypedDict):
    position: int
    team_id: int
    played: int
    won: int
    drawn: int
    lost: int
    goals_for: int
    goals_against: int
    goal_diff: int
    points: int
    form: list[str]  # last five results, oldest first: "W", "D", "L"


def result_for(match: Match, team_id: int) -> str:
    """'W', 'D' or 'L' for this team in a finished match."""
    own, other = (match["home_goals"], match["away_goals"]) if match["home_id"] == team_id \
        else (match["away_goals"], match["home_goals"])
    return "W" if own > other else "L" if own < other else "D"


def finished(matches: Iterable[Match]) -> list[Match]:
    """Finished matches, oldest first."""
    return sorted((m for m in matches if m["status"] == FINISHED), key=lambda m: (m["kickoff"], m["id"]))


def compute_standings(matches: Iterable[Match], team_ids: Iterable[int],
                      names: Mapping[int, str] | None = None) -> list[TableRow]:
    """Build the table from finished matches. Sorted by points, goal difference, goals, name."""
    names = names or {}
    rows: dict[int, TableRow] = {
        tid: {"position": 0, "team_id": tid, "played": 0, "won": 0, "drawn": 0, "lost": 0,
              "goals_for": 0, "goals_against": 0, "goal_diff": 0, "points": 0, "form": []}
        for tid in team_ids
    }
    for match in finished(matches):
        for team_id, scored, conceded in ((match["home_id"], match["home_goals"], match["away_goals"]),
                                          (match["away_id"], match["away_goals"], match["home_goals"])):
            row = rows.get(team_id)
            if row is None:
                continue
            outcome = result_for(match, team_id)
            row["played"] += 1
            row["goals_for"] += scored
            row["goals_against"] += conceded
            row["won" if outcome == "W" else "drawn" if outcome == "D" else "lost"] += 1
            row["points"] += {"W": 3, "D": 1, "L": 0}[outcome]
            row["form"] = (row["form"] + [outcome])[-5:]
    for row in rows.values():
        row["goal_diff"] = row["goals_for"] - row["goals_against"]
    ordered = sorted(rows.values(), key=lambda r: (-r["points"], -r["goal_diff"], -r["goals_for"],
                                                   names.get(r["team_id"], str(r["team_id"]))))
    for position, row in enumerate(ordered, start=1):
        row["position"] = position
    return ordered


def zone_for(position: int, team_count: int, zones: Mapping[str, int]) -> str | None:
    """'top', 'europe', 'relegation' or None for a table position."""
    top, europe, relegation = zones.get("top", 0), zones.get("europe", 0), zones.get("relegation", 0)
    if position <= top:
        return "top"
    if position <= top + europe:
        return "europe"
    if position > team_count - relegation:
        return "relegation"
    return None


def points_by_matchday(matches: Iterable[Match], team_ids: Iterable[int]) -> list[dict]:
    """Cumulative points for every team after every played matchday (for the bar-chart race)."""
    team_ids = list(team_ids)
    played = finished(matches)
    matchdays = sorted({m["matchday"] for m in played if m["matchday"] > 0})
    totals = {tid: 0 for tid in team_ids}
    frames = []
    for matchday in matchdays:
        for match in (m for m in played if m["matchday"] == matchday):
            for team_id in (match["home_id"], match["away_id"]):
                if team_id in totals:
                    totals[team_id] += {"W": 3, "D": 1, "L": 0}[result_for(match, team_id)]
        frames += [{"matchday": matchday, "team_id": tid, "points": totals[tid]} for tid in team_ids]
    return frames


def team_results(matches: Iterable[Match], team_id: int) -> list[Match]:
    """Finished matches of one team, oldest first."""
    return [m for m in finished(matches) if team_id in (m["home_id"], m["away_id"])]
