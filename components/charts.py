"""Plotly charts: radar, probability gauges, bar-chart race, form, stat bars, timeline, scorelines."""
from __future__ import annotations

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from components.theme import color, style_figure


def radar(labels: list[str], series: list[tuple[str, list[float], list[str], str]]) -> go.Figure:
    """Radar chart. Each series is (name, values on a 0-100 scale, hover texts, colour)."""
    fig = go.Figure()
    for name, values, hover, line_color in series:
        fig.add_trace(go.Scatterpolar(
            r=values + values[:1], theta=labels + labels[:1], name=name, fill="toself", opacity=0.75,
            line={"color": line_color, "width": 2}, text=hover + hover[:1],
            hovertemplate="<b>%{theta}</b><br>%{text}<br>Percentile %{r:.0f}<extra>" + name + "</extra>"))
    fig.update_layout(polar={"bgcolor": "rgba(0,0,0,0)",
                             "radialaxis": {"range": [0, 100], "showticklabels": False, "gridcolor": color("border")},
                             "angularaxis": {"gridcolor": color("border")}})
    return style_figure(fig, height=460)


def probability_gauges(home_name: str, away_name: str, home: float, draw: float, away: float) -> go.Figure:
    """Three gauges side by side: home win, draw, away win."""
    fig = go.Figure()
    for index, (label, value, bar_color) in enumerate(
            [(f"{home_name} win", home, color("accent")), ("Draw", draw, color("draw")), (f"{away_name} win", away, "#38BDF8")]):
        fig.add_trace(go.Indicator(
            mode="gauge+number", value=round(value * 100, 1), number={"suffix": "%", "font": {"size": 34}},
            title={"text": label, "font": {"size": 15}},
            domain={"x": [index / 3 + 0.02, (index + 1) / 3 - 0.02], "y": [0, 1]},
            gauge={"axis": {"range": [0, 100], "tickwidth": 0, "tickcolor": "rgba(0,0,0,0)"},
                   "bar": {"color": bar_color, "thickness": 0.75}, "bgcolor": color("surface-2"),
                   "borderwidth": 0}))
    return style_figure(fig, height=250)


def probability_bar(home_name: str, away_name: str, home: float, draw: float, away: float) -> go.Figure:
    """One stacked horizontal bar of the three outcomes."""
    fig = go.Figure()
    for label, value, bar_color in [(home_name, home, color("accent")), ("Draw", draw, color("draw")), (away_name, away, "#38BDF8")]:
        fig.add_trace(go.Bar(x=[value * 100], y=[""], orientation="h", name=label, marker_color=bar_color,
                             text=[f"{value:.0%}"], textposition="inside", insidetextanchor="middle",
                             hovertemplate=f"{label}: %{{x:.1f}}%<extra></extra>"))
    fig.update_layout(barmode="stack", xaxis={"range": [0, 100], "visible": False}, yaxis={"visible": False},
                      showlegend=True)
    fig = style_figure(fig, height=120)
    fig.update_traces(textfont_color="#0A1A12")
    return fig


def scoreline_heatmap(matrix: list[list[float]], home_name: str, away_name: str, size: int = 6) -> go.Figure:
    data = [[p * 100 for p in row[:size]] for row in matrix[:size]]
    fig = px.imshow(data, text_auto=".1f", color_continuous_scale=[[0, color("surface-2")], [1, color("accent")]],
                    labels={"x": f"{away_name} goals", "y": f"{home_name} goals", "color": "%"}, aspect="auto")
    fig.update_traces(hovertemplate=f"{home_name} %{{y}} – %{{x}} {away_name}<br>%{{z:.1f}}%<extra></extra>")
    fig.update_layout(coloraxis_showscale=False)
    return style_figure(fig, height=360)


def points_race(frames: list[dict], teams: dict[int, dict]) -> go.Figure:
    """Animated bar-chart race of cumulative points by matchday (bars swap places as ranks change)."""
    df = pd.DataFrame(frames)
    df["team"] = df["team_id"].map(lambda tid: teams[tid]["name"] if tid in teams else str(tid))
    df = df.sort_values(["matchday", "points", "team"], ascending=[True, False, True])
    df["rank"] = df.groupby("matchday").cumcount() + 1
    palette = {teams[tid]["name"]: teams[tid].get("primary", color("accent")) for tid in df["team_id"].unique() if tid in teams}
    fig = px.bar(df, x="points", y="rank", color="team", orientation="h", text="team", animation_frame="matchday",
                 animation_group="team", color_discrete_map=palette, range_x=[0, df["points"].max() * 1.2 + 2],
                 hover_data={"rank": False, "team": True, "points": True, "matchday": True})
    team_count = df["team"].nunique()
    fig.update_yaxes(range=[team_count + 0.5, 0.5], visible=False)  # fixed slots, leader on top
    fig.update_traces(texttemplate="%{text}  %{x}", textposition="outside", cliponaxis=False,
                      textfont={"size": 13, "color": color("text")})
    fig.update_layout(showlegend=False, xaxis_title="Points")
    if fig.layout.updatemenus:
        fig.layout.updatemenus[0].buttons[0].args[1]["frame"]["duration"] = 600
        fig.layout.updatemenus[0].buttons[0].args[1]["transition"]["duration"] = 450
    return style_figure(fig, height=max(380, 40 * df["team"].nunique()))


def form_chart(rows: list[dict]) -> go.Figure:
    """Per match goals scored/conceded bars, plus the running points total on a second axis."""
    df = pd.DataFrame(rows)
    fig = make_subplots(specs=[[{"secondary_y": True}]])
    fig.add_trace(go.Bar(x=df["label"], y=df["scored"], name="Scored", marker_color=color("win"),
                         customdata=df[["opponent", "score"]], hovertemplate="vs %{customdata[0]}<br>%{customdata[1]}<extra>Scored</extra>"))
    fig.add_trace(go.Bar(x=df["label"], y=-df["conceded"], name="Conceded", marker_color=color("loss"),
                         customdata=df[["opponent", "score"]], hovertemplate="vs %{customdata[0]}<br>%{customdata[1]}<extra>Conceded</extra>"))
    fig.add_trace(go.Scatter(x=df["label"], y=df["points_total"], name="Points (total)", mode="lines+markers",
                             line={"color": color("accent"), "width": 3, "shape": "spline"}), secondary_y=True)
    fig.update_layout(barmode="relative", xaxis_title=None)
    fig.update_yaxes(title_text="Goals", secondary_y=False)
    fig.update_yaxes(title_text="Points", secondary_y=True, showgrid=False, rangemode="tozero", tickformat="d")
    return style_figure(fig, height=380)


def stat_bars(stats: dict[str, list[int]], home_name: str, away_name: str, home_color: str, away_color: str) -> go.Figure:
    """Side-by-side 100 % bars for possession, shots, corners and so on."""
    labels = {"possession": "Possession %", "shots": "Shots", "shots_on_target": "On target",
              "corners": "Corners", "fouls": "Fouls"}
    keys = [k for k in labels if k in stats][::-1]
    shares = [(stats[k][0] / max(1, sum(stats[k])) * 100) for k in keys]
    fig = go.Figure()
    fig.add_trace(go.Bar(y=[labels[k] for k in keys], x=shares, orientation="h", name=home_name, marker_color=home_color,
                         text=[stats[k][0] for k in keys], textposition="inside", hovertemplate="%{y}: %{text}<extra>" + home_name + "</extra>"))
    fig.add_trace(go.Bar(y=[labels[k] for k in keys], x=[100 - s for s in shares], orientation="h", name=away_name,
                         marker_color=away_color, text=[stats[k][1] for k in keys], textposition="inside",
                         hovertemplate="%{y}: %{text}<extra>" + away_name + "</extra>"))
    fig.update_layout(barmode="stack", xaxis={"visible": False, "range": [0, 100]}, bargap=0.35)
    return style_figure(fig, height=60 + 52 * len(keys))


EVENT_SYMBOLS = {"goal": ("circle", "Goal"), "penalty": ("circle-dot", "Penalty"), "own_goal": ("circle-x", "Own goal"),
                 "yellow": ("square", "Yellow card"), "red": ("square", "Red card"), "sub": ("diamond", "Substitution")}


def event_timeline(events: list[dict], home_name: str, away_name: str, minute_now: int = 90) -> go.Figure:
    """Events on a 0-90 minute axis, home above the line and away below."""
    fig = go.Figure()
    colors = {"goal": color("accent"), "penalty": color("accent"), "own_goal": color("loss"),
              "yellow": "#FACC15", "red": "#EF4444", "sub": "#38BDF8"}
    for kind, (symbol, label) in EVENT_SYMBOLS.items():
        chosen = [e for e in events if e["type"] == kind]
        if not chosen:
            continue
        fig.add_trace(go.Scatter(
            x=[e["minute"] for e in chosen], y=[1 if e["side"] == "home" else -1 for e in chosen], mode="markers",
            name=label, marker={"symbol": symbol, "size": 16 if kind in ("goal", "penalty", "own_goal") else 12,
                                "color": colors[kind], "line": {"width": 1, "color": "#0A1A12"}},
            text=[f"{e['player']}" + (f" (← {e['assist']})" if kind == "sub" and e.get("assist") else
                                      f" (assist {e['assist']})" if e.get("assist") else "") for e in chosen],
            hovertemplate="%{x}' %{text}<extra>" + label + "</extra>"))
    fig.add_shape(type="line", x0=0, x1=90, y0=0, y1=0, line={"color": color("muted"), "width": 2})
    fig.add_shape(type="line", x0=45, x1=45, y0=-1.4, y1=1.4, line={"color": color("border"), "dash": "dot"})
    fig.add_shape(type="rect", x0=0, x1=min(minute_now, 90), y0=-0.08, y1=0.08, fillcolor=color("accent"), line_width=0, opacity=0.6)
    fig.update_xaxes(range=[-2, 93], tickvals=[0, 15, 30, 45, 60, 75, 90], ticksuffix="'")
    fig.update_yaxes(range=[-1.6, 1.6], tickvals=[1, -1], ticktext=[home_name, away_name], showgrid=False)
    return style_figure(fig, height=260)
