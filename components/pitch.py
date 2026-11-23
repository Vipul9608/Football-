"""A football pitch drawn with Plotly shapes, with both line-ups placed by formation."""
from __future__ import annotations

import plotly.graph_objects as go

from components.theme import current_theme, style_figure
from services.layout import formation_positions

# Pitch is 105 x 68 m, drawn on a 100 x 100 grid; these constants are in grid units.
BOX_DEPTH, BOX_TOP, BOX_BOTTOM = 15.7, 20.35, 79.65
SIX_DEPTH, SIX_TOP, SIX_BOTTOM = 5.2, 36.5, 63.5
CIRCLE_RX, CIRCLE_RY = 8.7, 13.5


def _pitch_shapes(line: str) -> list[dict]:
    def rect(x0: float, x1: float, y0: float, y1: float) -> dict:
        return {"type": "rect", "x0": x0, "x1": x1, "y0": y0, "y1": y1, "line": {"color": line, "width": 2}, "layer": "below"}
    shapes = [rect(0, 100, 0, 100),
              {"type": "line", "x0": 50, "x1": 50, "y0": 0, "y1": 100, "line": {"color": line, "width": 2}, "layer": "below"},
              {"type": "circle", "x0": 50 - CIRCLE_RX, "x1": 50 + CIRCLE_RX, "y0": 50 - CIRCLE_RY, "y1": 50 + CIRCLE_RY,
               "line": {"color": line, "width": 2}, "layer": "below"},
              rect(0, BOX_DEPTH, BOX_TOP, BOX_BOTTOM), rect(100 - BOX_DEPTH, 100, BOX_TOP, BOX_BOTTOM),
              rect(0, SIX_DEPTH, SIX_TOP, SIX_BOTTOM), rect(100 - SIX_DEPTH, 100, SIX_TOP, SIX_BOTTOM),
              rect(-1.6, 0, 44.6, 55.4), rect(100, 101.6, 44.6, 55.4)]
    return shapes


def _stripes(dark: bool) -> list[dict]:
    a, b = ("#0F3B25", "#124429") if dark else ("#3FA45B", "#48B064")
    return [{"type": "rect", "x0": i * 10, "x1": (i + 1) * 10, "y0": 0, "y1": 100, "fillcolor": a if i % 2 else b,
             "line": {"width": 0}, "layer": "below"} for i in range(10)]


def pitch_figure(lineups: dict, home: dict, away: dict) -> go.Figure:
    dark = current_theme() == "dark"
    line = "rgba(255,255,255,0.55)" if dark else "rgba(255,255,255,0.9)"
    fig = go.Figure()
    for side, team in (("home", home), ("away", away)):
        lineup = lineups.get(side)
        if not lineup:
            continue
        players = lineup["start_xi"][:11]
        coords = formation_positions(lineup["formation"], side)[: len(players)]
        xs, ys = [c[0] for c in coords], [c[1] for c in coords]
        numbers = [str(p.get("number") or "") for p in players]
        surnames = [p["name"].split()[-1] for p in players]
        fig.add_trace(go.Scatter(
            x=xs, y=ys, mode="markers+text", text=numbers, name=f"{team['name']} ({lineup['formation']})",
            textfont={"color": team.get("secondary", "#FFFFFF"), "size": 12, "family": "Outfit, sans-serif"},
            marker={"size": 30, "color": team.get("primary", "#2A9D8F"), "line": {"color": "#FFFFFF", "width": 2}},
            customdata=[[p["name"], p.get("position", "")] for p in players],
            hovertemplate="<b>%{customdata[0]}</b><br>#%{text} · %{customdata[1]}<extra>" + team["name"] + "</extra>"))
        fig.add_trace(go.Scatter(x=xs, y=[y - 6.5 for y in ys], mode="text", text=surnames, hoverinfo="skip",
                                 showlegend=False, textfont={"color": "#FFFFFF", "size": 11}))
    fig.update_layout(shapes=_stripes(dark) + _pitch_shapes(line))
    fig.update_xaxes(range=[-3, 103], visible=False, fixedrange=True)
    fig.update_yaxes(range=[-3, 103], visible=False, fixedrange=True)
    fig = style_figure(fig, height=560)
    fig.update_layout(legend={"y": 1.06})
    return fig
