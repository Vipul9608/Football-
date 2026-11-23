"""Pure helpers for laying out players on a pitch (no Streamlit, no Plotly)."""
from __future__ import annotations

DEFAULT_FORMATION = "4-4-2"


def formation_lines(formation: str) -> list[int]:
    """'4-3-3' -> [1, 4, 3, 3] including the goalkeeper. Invalid shapes fall back to 4-4-2."""
    try:
        lines = [int(part) for part in formation.split("-")]
    except (AttributeError, ValueError):
        lines = []
    if not lines or sum(lines) != 10 or any(n <= 0 for n in lines):
        lines = [int(part) for part in DEFAULT_FORMATION.split("-")]
    return [1] + lines


def formation_positions(formation: str, side: str) -> list[tuple[float, float]]:
    """Coordinates on a 100 x 100 pitch for a starting XI in formation order (GK first).

    The home team defends the left goal and fills x = 5..46; the away team is mirrored on the right.
    """
    lines = formation_lines(formation)
    positions = []
    for line_index, count in enumerate(lines):
        x = 5 + line_index * (41 / (len(lines) - 1))
        for slot in range(count):
            y = (slot + 1) * 100 / (count + 1)
            positions.append((x, y) if side == "home" else (100 - x, 100 - y))
    return positions
