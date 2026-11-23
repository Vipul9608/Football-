"""Match predictor: an independent-Poisson model built on recent form.

1. Each team's attack and defence strength = its recent goals scored / conceded per game,
   relative to the league average (shrunk toward average when there are few games).
2. Expected goals = league average x own attack x opponent defence, adjusted for home advantage
   and for the user's what-if multipliers.
3. Win/draw/loss probabilities come from the matrix of Poisson scoreline probabilities.
"""
from __future__ import annotations

import math
from collections.abc import Iterable
from dataclasses import dataclass, field

from .data_source import Match
from .standings import finished

SHRINK_GAMES = 2  # pretend every team also played this many perfectly average games
MAX_GOALS = 10


@dataclass(frozen=True)
class Strength:
    attack: float
    defence: float  # >1 means the team concedes MORE than average
    games: int


@dataclass(frozen=True)
class Prediction:
    home_xg: float
    away_xg: float
    home_win: float
    draw: float
    away_win: float
    matrix: list[list[float]] = field(repr=False)

    def top_scorelines(self, count: int = 5) -> list[tuple[int, int, float]]:
        """Most likely exact scores as (home goals, away goals, probability)."""
        cells = [(h, a, p) for h, row in enumerate(self.matrix) for a, p in enumerate(row)]
        return sorted(cells, key=lambda c: c[2], reverse=True)[:count]


def poisson_pmf(k: int, lam: float) -> float:
    return math.exp(-lam) * lam ** k / math.factorial(k)


def league_averages(matches: Iterable[Match]) -> tuple[float, float]:
    """Average home goals and away goals per finished match (sensible defaults if none)."""
    played = finished(matches)
    if not played:
        return 1.5, 1.2
    home = sum(m["home_goals"] for m in played) / len(played)
    away = sum(m["away_goals"] for m in played) / len(played)
    return max(home, 0.1), max(away, 0.1)


def team_strength(matches: Iterable[Match], team_id: int, window: int = 10) -> Strength:
    """Attack/defence strength from the team's last `window` finished matches."""
    played = finished(matches)
    home_avg, away_avg = league_averages(played)
    per_team_avg = (home_avg + away_avg) / 2
    recent = [m for m in played if team_id in (m["home_id"], m["away_id"])][-window:]
    scored = sum(m["home_goals"] if m["home_id"] == team_id else m["away_goals"] for m in recent)
    conceded = sum(m["away_goals"] if m["home_id"] == team_id else m["home_goals"] for m in recent)
    games = len(recent) + SHRINK_GAMES
    attack = (scored + SHRINK_GAMES * per_team_avg) / (games * per_team_avg)
    defence = (conceded + SHRINK_GAMES * per_team_avg) / (games * per_team_avg)
    return Strength(attack=attack, defence=defence, games=len(recent))


def outcome_probabilities(home_xg: float, away_xg: float, max_goals: int = MAX_GOALS) -> Prediction:
    """Win/draw/loss from two independent Poisson goal counts. Probabilities are normalised."""
    home_p = [poisson_pmf(k, home_xg) for k in range(max_goals + 1)]
    away_p = [poisson_pmf(k, away_xg) for k in range(max_goals + 1)]
    matrix = [[h * a for a in away_p] for h in home_p]
    total = sum(map(sum, matrix))
    matrix = [[p / total for p in row] for row in matrix]
    home_win = sum(matrix[h][a] for h in range(max_goals + 1) for a in range(max_goals + 1) if h > a)
    draw = sum(matrix[k][k] for k in range(max_goals + 1))
    return Prediction(home_xg, away_xg, home_win, draw, 1 - home_win - draw, matrix)


def default_home_advantage(matches: Iterable[Match]) -> float:
    """How much more home teams score than away teams in this league (0.25 = 25 %)."""
    home_avg, away_avg = league_averages(matches)
    return max(0.0, min(0.6, home_avg / away_avg - 1))


def predict(matches: Iterable[Match], home_id: int, away_id: int, *, window: int = 10,
            home_advantage: float | None = None, home_attack: float = 1.0, home_defence: float = 1.0,
            away_attack: float = 1.0, away_defence: float = 1.0) -> Prediction:
    """Predict a match. The four multipliers are the what-if sliders (1.0 = no change).

    A defence multiplier above 1 means a BETTER defence: it divides the opponent's expected goals.
    """
    matches = list(matches)
    home_avg, away_avg = league_averages(matches)
    base = (home_avg + away_avg) / 2
    if home_advantage is None:
        home_advantage = default_home_advantage(matches)
    home, away = team_strength(matches, home_id, window), team_strength(matches, away_id, window)
    home_xg = base * (1 + home_advantage / 2) * home.attack * away.defence * home_attack / away_defence
    away_xg = base * (1 - home_advantage / 2) * away.attack * home.defence * away_attack / home_defence
    return outcome_probabilities(max(home_xg, 0.05), max(away_xg, 0.05))
