"""Lottie animations and goal celebrations. Everything degrades gracefully if a package is missing."""
from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

import streamlit as st

LOTTIE_DIR = Path(__file__).resolve().parent.parent / "assets" / "lottie"

try:
    from streamlit_lottie import st_lottie
except ImportError:  # the app still works, just without animations
    st_lottie = None


@lru_cache(maxsize=None)
def _load(name: str) -> dict | None:
    try:
        return json.loads((LOTTIE_DIR / f"{name}.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


def lottie(name: str, height: int = 200, key: str | None = None, loop: bool = True) -> None:
    """Show a bundled animation (assets/lottie/<name>.json), or nothing if unavailable."""
    data = _load(name)
    if st_lottie and data:
        st_lottie(data, height=height, key=key or f"lottie-{name}", loop=loop, quality="high")


def celebrate(team_name: str, detail: str = "") -> None:
    """Goal for a favourite team: balloons, a toast and the goal animation."""
    st.balloons()
    st.toast(f"⚽ GOAL for {team_name}! {detail}".strip())
    lottie("goal", height=220, key=f"goal-{team_name}-{detail}", loop=False)
