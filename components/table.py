"""The standings table as styled HTML, with zone colours, form dots and favourite highlighting."""
from __future__ import annotations

from html import escape

from components.cards import form_dots
from components.media import crest_html
from services.standings import TableRow, zone_for

ZONE_LABELS = {"top": "Champions / promotion", "europe": "Europe", "relegation": "Relegation"}


def standings_html(rows: list[TableRow], teams: dict[int, dict], zones: dict[str, int],
                   favorites: set[int] | None = None) -> str:
    favorites = favorites or set()
    body = []
    for row in rows:
        team = teams.get(row["team_id"], {"id": row["team_id"], "name": str(row["team_id"])})
        zone = zone_for(row["position"], len(rows), zones)
        classes = " ".join(c for c in (f"zone-{zone}" if zone else "", "fav" if row["team_id"] in favorites else "") if c)
        body.append(
            f'<tr class="{classes}"><td class="pos l">{row["position"]}</td>'
            f'<td class="l"><div class="team-cell">{crest_html(team)}{escape(team["name"])}</div></td>'
            f'<td>{row["played"]}</td><td class="hide-sm">{row["won"]}</td><td class="hide-sm">{row["drawn"]}</td>'
            f'<td class="hide-sm">{row["lost"]}</td><td class="hide-sm">{row["goals_for"]}:{row["goals_against"]}</td>'
            f'<td>{row["goal_diff"]:+d}</td><td class="pts">{row["points"]}</td>'
            f'<td class="l hide-sm">{form_dots(row["form"])}</td></tr>')
    head = ('<tr><th class="l">#</th><th class="l">Team</th><th>P</th><th class="hide-sm">W</th><th class="hide-sm">D</th>'
            '<th class="hide-sm">L</th><th class="hide-sm">Goals</th><th>GD</th><th>Pts</th><th class="l hide-sm">Form</th></tr>')
    legend = "".join(f'<span class="{z}">{label}</span>' for z, label in ZONE_LABELS.items() if zones.get(z))
    return (f'<div class="ps-table-wrap"><table class="ps-table"><thead>{head}</thead>'
            f'<tbody>{"".join(body)}</tbody></table></div><div class="ps-legend">{legend}</div>')
