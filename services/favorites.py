"""Favourite teams and goal detection (pure functions; the session state lives in the views)."""
from __future__ import annotations

from collections.abc import Iterable

from .data_source import LIVE, Match

Score = tuple[int, int]


def toggle(favorites: set[int], team_id: int) -> set[int]:
    """Return a new set with the team added, or removed if it was already a favourite."""
    return favorites - {team_id} if team_id in favorites else favorites | {team_id}


def score_snapshot(matches: Iterable[Match]) -> dict[int, Score]:
    """Current score of every live match, keyed by match id."""
    return {m["id"]: (m["home_goals"] or 0, m["away_goals"] or 0) for m in matches if m["status"] == LIVE}


def favorite_goals(previous: dict[int, Score], matches: Iterable[Match],
                   favorites: set[int]) -> list[tuple[Match, int]]:
    """Live matches where a favourite team scored since the previous snapshot.

    Returns (match, scoring team id) pairs. Matches missing from `previous` are skipped, so
    opening the app during a game does not celebrate goals that happened earlier.
    """
    goals = []
    for match in matches:
        if match["status"] != LIVE or match["id"] not in previous:
            continue
        old_home, old_away = previous[match["id"]]
        if (match["home_goals"] or 0) > old_home and match["home_id"] in favorites:
            goals.append((match, match["home_id"]))
        if (match["away_goals"] or 0) > old_away and match["away_id"] in favorites:
            goals.append((match, match["away_id"]))
    return goals
