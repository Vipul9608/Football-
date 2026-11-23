"""Player comparison maths: per-90 rates and percentiles (pure functions)."""
from __future__ import annotations

from bisect import bisect_left, bisect_right
from collections.abc import Sequence

# Radar metrics: (stats key, label, per 90 minutes?)
RADAR_METRICS: list[tuple[str, str, bool]] = [
    ("goals", "Goals", True), ("assists", "Assists", True), ("shots", "Shots", True),
    ("key_passes", "Key passes", True), ("passes", "Passes", True), ("pass_accuracy", "Pass %", False),
    ("tackles", "Tackles", True), ("interceptions", "Interceptions", True), ("dribbles", "Dribbles", True),
]


def per90(player: dict, key: str) -> float:
    """A stat per 90 minutes played (0 for players without minutes)."""
    minutes = float(player.get("stats", {}).get("minutes") or 0)
    if minutes <= 0:
        return 0.0
    return float(player["stats"].get(key) or 0) * 90 / minutes


def metric_value(player: dict, key: str, is_rate: bool) -> float:
    return per90(player, key) if is_rate else float(player.get("stats", {}).get(key) or 0)


def percentile(value: float, pool: Sequence[float]) -> float:
    """Share of the pool at or below `value`, 0-100, counting ties as half (mid-rank)."""
    if not pool:
        return 50.0
    ordered = sorted(pool)
    below, upto = bisect_left(ordered, value), bisect_right(ordered, value)
    return 100 * (below + (upto - below) / 2) / len(ordered)


def radar_profile(player: dict, pool: Sequence[dict]) -> tuple[list[float], list[str]]:
    """Percentiles and readable hover texts for one player against a comparison pool."""
    values, texts = [], []
    for key, label, is_rate in RADAR_METRICS:
        mine = metric_value(player, key, is_rate)
        values.append(percentile(mine, [metric_value(p, key, is_rate) for p in pool]))
        texts.append(f"{mine:.2f} per 90" if is_rate else f"{mine:.1f}")
    return values, texts
