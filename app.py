"""Pitchside: a football companion app built with Streamlit.

Entry point: page config, theme, sidebar navigation, and routing to the views.
    streamlit run app.py
"""
from __future__ import annotations

import streamlit as st

st.set_page_config(page_title="Pitchside · Football", page_icon="⚽", layout="wide",
                   initial_sidebar_state="auto")

from components.cards import banner, html  # noqa: E402  (set_page_config must run first)
from components.theme import inject_css, menu_styles  # noqa: E402
from services import api  # noqa: E402
from views import home, match_center, players, predictor, scores, tables, teams  # noqa: E402

try:
    from streamlit_option_menu import option_menu
except ImportError:  # fall back to a plain radio if the component is missing
    option_menu = None

PAGES = {
    "Home": ("house-fill", home.render),
    "Scores": ("broadcast", scores.render),
    "Tables": ("table", tables.render),
    "Teams": ("shield-fill", teams.render),
    "Players": ("person-badge-fill", players.render),
    "Match Center": ("camera-reels-fill", match_center.render),
    "Predictor": ("graph-up-arrow", predictor.render),
}


def sidebar() -> str:
    """Brand, navigation, league picker, theme toggle and data-source controls. Returns the page."""
    with st.sidebar:
        html('<div class="ps-brand"><div class="logo">⚽</div><div class="word">Pitch<span>side</span></div></div>')
        names = list(PAGES)
        target = st.session_state.pop("nav_to", None)
        if target in names:
            st.session_state.page = target
        current = st.session_state.get("page", "Home")
        if option_menu:
            # A stable key keeps the menu's state; manual_select moves it when a button navigates.
            page = option_menu(None, names, icons=[PAGES[n][0] for n in names], default_index=names.index(current),
                               styles=menu_styles(), key="nav",
                               manual_select=names.index(target) if target in names else None)
            if target in names:  # the component reports the new selection one run later
                page = target
        else:
            page = st.radio("Navigate", names, index=names.index(current), label_visibility="collapsed")
        st.session_state.page = page

        st.divider()
        leagues = api.leagues()
        ids = [lg["id"] for lg in leagues]
        if st.session_state.get("league_id") not in ids:
            st.session_state.league_id = ids[0]
        st.selectbox("League", ids, key="league_id", format_func=lambda lid: next(lg["name"] for lg in leagues if lg["id"] == lid))
        st.toggle("☀️ Light mode", key="light_mode")

        st.divider()
        if api.api_settings():
            live = st.toggle("Live API data", value=api.mode() == api.API, help="Turn off to use the offline demo dataset.")
            if live != (api.mode() == api.API):
                api.set_mode(api.API if live else api.DEMO)
                st.rerun()
        else:
            st.caption("🧪 **Demo mode** – add `API_FOOTBALL_KEY` to your secrets for live data.")
        st.caption("Data: API-Football (live) or a bundled fictional demo dataset.")
    return page


def data_banner() -> None:
    reason = api.fallback_reason()
    if reason:
        banner(f"<b>Live data unavailable, showing demo data.</b> {reason}", warn=True)
    elif api.mode() == api.DEMO:
        banner("<b>Demo mode.</b> Clubs and players are fictional; live games tick along in real time.")


def main() -> None:
    st.session_state.theme = "light" if st.session_state.get("light_mode") else "dark"
    inject_css()
    page = sidebar()
    data_banner()
    try:
        PAGES[page][1]()
    except Exception as error:  # a friendly message instead of a stack trace
        st.error("Something went wrong while loading this page. Try again, or switch to demo mode in the sidebar.")
        with st.expander("Technical details"):
            st.exception(error)


main()
