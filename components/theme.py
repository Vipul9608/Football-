"""Dark/light theme: CSS variables, CSS injection, and matching Plotly styling."""
from __future__ import annotations

from pathlib import Path

import plotly.graph_objects as go
import streamlit as st

CSS_PATH = Path(__file__).resolve().parent.parent / "assets" / "styles.css"

THEMES: dict[str, dict[str, str]] = {
    "dark": {
        "bg": "#07140F", "bg-stripe": "#081710", "bg-2": "#0B1D16", "surface": "#0F261D", "surface-2": "#133126",
        "border": "rgba(212,255,58,0.10)", "text": "#E9F5EE", "muted": "#8DB3A1",
        "accent": "#D4FF3A", "accent-ink": "#0A1A12", "accent-soft": "rgba(212,255,58,0.35)",
        "glow": "rgba(212,255,58,0.10)", "live": "#FF3B5C",
        "win": "#22C55E", "draw": "#8B9A93", "loss": "#EF4444",
        "zone-top": "#22C55E", "zone-europe": "#38BDF8", "zone-releg": "#EF4444",
        "hero-a": "#0F2A1F", "hero-b": "#14402C",
        "shadow": "0 6px 24px rgba(0,0,0,0.25)", "shadow-hover": "0 12px 32px rgba(0,0,0,0.38)",
    },
    "light": {
        "bg": "#F2F7F3", "bg-stripe": "#EDF4EF", "bg-2": "#E4EEE7", "surface": "#FFFFFF", "surface-2": "#F4F9F5",
        "border": "rgba(10,60,35,0.12)", "text": "#0D2118", "muted": "#557063",
        "accent": "#0F9D58", "accent-ink": "#FFFFFF", "accent-soft": "rgba(15,157,88,0.30)",
        "glow": "rgba(15,157,88,0.10)", "live": "#E11D48",
        "win": "#16A34A", "draw": "#94A3B8", "loss": "#DC2626",
        "zone-top": "#16A34A", "zone-europe": "#0284C7", "zone-releg": "#DC2626",
        "hero-a": "#E3F4E9", "hero-b": "#CBEBD7",
        "shadow": "0 4px 18px rgba(13,33,24,0.06)", "shadow-hover": "0 10px 28px rgba(13,33,24,0.12)",
    },
}


def current_theme() -> str:
    return st.session_state.get("theme", "dark")


def color(name: str) -> str:
    """One colour of the active theme, e.g. color('accent')."""
    return THEMES[current_theme()][name]


def inject_css() -> None:
    """Write the theme variables and the stylesheet into the page."""
    variables = "; ".join(f"--{k}: {v}" for k, v in THEMES[current_theme()].items())
    css = CSS_PATH.read_text(encoding="utf-8")
    if current_theme() == "light":  # the Lottie iframe paints a dark background; invert it to blend in
        css += '\niframe[title="streamlit_lottie.streamlit_lottie"] { filter: invert(1) hue-rotate(180deg); }'
    st.markdown(f"<style>:root {{ {variables}; }}\n{css}</style>", unsafe_allow_html=True)


def style_figure(fig: go.Figure, height: int | None = None) -> go.Figure:
    """Give a Plotly figure transparent backgrounds, theme fonts and a tidy hover label."""
    theme = THEMES[current_theme()]
    fig.update_layout(
        template="plotly_dark" if current_theme() == "dark" else "plotly_white",
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        font={"family": "Inter, sans-serif", "color": theme["text"]},
        margin={"l": 10, "r": 10, "t": 40, "b": 10},
        hoverlabel={"bgcolor": theme["surface-2"], "font": {"color": theme["text"]}, "bordercolor": theme["accent"]},
        legend={"orientation": "h", "yanchor": "bottom", "y": 1.02, "x": 0},
    )
    fig.update_xaxes(gridcolor=theme["border"], zerolinecolor=theme["border"])
    fig.update_yaxes(gridcolor=theme["border"], zerolinecolor=theme["border"])
    if height:
        fig.update_layout(height=height)
    return fig


def menu_styles() -> dict[str, dict[str, str]]:
    """Styles for streamlit-option-menu.

    The menu lives in an iframe that always paints the dark config background, so it uses the
    dark palette in both modes and reads as a deliberate dark navigation card in light mode.
    """
    theme = THEMES["dark"]
    return {
        "container": {"padding": "6px", "background-color": theme["surface"]},
        "icon": {"color": theme["muted"], "font-size": "16px"},
        "nav-link": {"font-size": "15px", "font-weight": "500", "color": theme["text"], "border-radius": "12px",
                     "margin": "3px 0", "--hover-color": theme["surface-2"]},
        "nav-link-selected": {"background-color": theme["accent"], "color": theme["accent-ink"], "font-weight": "700"},
    }
