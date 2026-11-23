"""Team crests and player photos, with generated badges when the API has no image."""
from __future__ import annotations

import base64
from html import escape


def _initials(name: str, letters: int = 2) -> str:
    words = [w for w in name.replace("-", " ").split() if w[:1].isalpha()]
    return "".join(w[0] for w in words[:letters]).upper() or "?"


def badge_data_uri(text: str, primary: str, secondary: str, round_shape: bool = False) -> str:
    """A small SVG badge (shield or circle) as a data: URI, used as the image fallback."""
    shape = ('<circle cx="32" cy="32" r="30" fill="{p}" stroke="{s}" stroke-width="3"/>' if round_shape else
             '<path d="M32 3 L58 12 V32 C58 47 46 57 32 61 C18 57 6 47 6 32 V12 Z" fill="{p}" '
             'stroke="{s}" stroke-width="3"/>').format(p=primary, s=secondary)
    svg = (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64">{shape}'
           f'<text x="32" y="38" text-anchor="middle" font-family="Arial, sans-serif" font-weight="700" '
           f'font-size="{18 if len(text) <= 2 else 14}" fill="{secondary}">{escape(text)}</text></svg>')
    return "data:image/svg+xml;base64," + base64.b64encode(svg.encode()).decode()


def team_badge(team: dict) -> str:
    return badge_data_uri(_initials(team["name"]), team.get("primary", "#2A9D8F"), team.get("secondary", "#FFFFFF"))


def player_badge(player: dict) -> str:
    return badge_data_uri(_initials(player["name"]), "#163629", "#D4FF3A", round_shape=True)


def crest_html(team: dict, large: bool = False) -> str:
    """<img> for a crest. If the remote image fails to load, the browser swaps in the badge."""
    fallback = team_badge(team)
    src = team.get("crest") or fallback
    size = "ps-crest lg" if large else "ps-crest"
    return (f'<img class="{size}" src="{escape(src)}" alt="{escape(team["name"])} crest" loading="lazy" '
            f'onerror="this.onerror=null;this.src=\'{fallback}\'">')


def avatar_html(player: dict) -> str:
    fallback = player_badge(player)
    src = player.get("photo") or fallback
    return (f'<img class="ps-avatar" src="{escape(src)}" alt="{escape(player["name"])}" loading="lazy" '
            f'onerror="this.onerror=null;this.src=\'{fallback}\'">')


def image_url(item: dict, kind: str) -> str:
    """URL for st.dataframe ImageColumn: the real image, or the generated badge."""
    if kind == "team":
        return item.get("crest") or team_badge(item)
    return item.get("photo") or player_badge(item)
