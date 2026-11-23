"""Generate the offline demo dataset at data/sample/demo.json.

The dataset is deterministic (seeded) and uses fictional leagues, clubs and players, so the
app can be demoed without an API key and without inventing statistics for real people.

Match dates are stored as offsets from "today" and resolved when the app starts, so the
demo always shows a current matchday with finished, live and upcoming games.

    python scripts/make_sample_data.py
"""
from __future__ import annotations

import json
import math
import random
from pathlib import Path

SEED = 7
CURRENT_MATCHDAY = 15
OUTPUT = Path(__file__).resolve().parent.parent / "data" / "sample" / "demo.json"

# Minutes since kickoff (relative to app start) for the five games of the current matchday:
# two finished earlier today, two live, one later today.
CURRENT_DAY_OFFSETS = [-300, -240, -70, -35, 180]
KICKOFF_TIMES = ["12:30", "15:00", "15:00", "17:30", "20:00"]
FORMATIONS = ["4-3-3", "4-4-2", "4-2-3-1", "3-5-2"]

LEAGUES = [
    {
        "id": 1,
        "name": "Premier Division",
        "country": "Demo Isles",
        "zones": {"top": 2, "europe": 1, "relegation": 2},
        "teams": [
            ("Redbridge United", "RBU", "#D7263D", "#FFFFFF", 1.40),
            ("Harbor City", "HAR", "#1B98E0", "#0B2545", 1.30),
            ("Kingsford Rovers", "KFR", "#1D3557", "#F1FAEE", 1.20),
            ("Ashton Vale", "ASV", "#6A0572", "#F7B801", 1.10),
            ("Millbrook Athletic", "MBA", "#2A9D8F", "#264653", 1.00),
            ("Crown Park", "CRP", "#F4A261", "#1D1D1D", 0.95),
            ("Westhaven FC", "WHV", "#E63946", "#1D3557", 0.90),
            ("Stonegate Town", "STG", "#8D99AE", "#2B2D42", 0.85),
            ("Riverside Wanderers", "RSW", "#06D6A0", "#073B4C", 0.80),
            ("Oakfield Albion", "OKA", "#FFD166", "#3D405B", 0.75),
        ],
    },
    {
        "id": 2,
        "name": "Liga Costa",
        "country": "Demo Peninsula",
        "zones": {"top": 2, "europe": 1, "relegation": 2},
        "teams": [
            ("Real Montaña", "RMO", "#F8F9FA", "#5E2B97", 1.38),
            ("Atlético Brisa", "ATB", "#C1121F", "#FDF0D5", 1.28),
            ("CD Puerto Sol", "PSO", "#FFB703", "#023047", 1.15),
            ("Sporting Valle", "SPV", "#2D6A4F", "#D8F3DC", 1.08),
            ("Unión Arena", "UAR", "#E76F51", "#264653", 1.00),
            ("Deportivo Faro", "DFA", "#0077B6", "#CAF0F8", 0.95),
            ("Racing Olivo", "ROL", "#606C38", "#FEFAE0", 0.90),
            ("CF Sierra Azul", "CSA", "#3A86FF", "#FFFFFF", 0.86),
            ("Club Marea", "CMA", "#00B4D8", "#03045E", 0.80),
            ("Estrella del Sur", "EDS", "#FB8500", "#000000", 0.76),
        ],
    },
]

FIRST_NAMES = [
    "Leo", "Mateo", "Noah", "Luca", "Adam", "Samuel", "Oscar", "Elias", "Hugo", "Felix",
    "Theo", "Jonas", "Marco", "Diego", "Rafael", "Kai", "Emil", "Ivan", "Tomas", "Nico",
    "Andre", "Bruno", "Caio", "Dario", "Enzo", "Fabio", "Gabriel", "Henrik", "Isak", "Joel",
    "Karim", "Lucas", "Milan", "Omar", "Pablo", "Ruben", "Sami", "Tiago", "Victor", "Yusuf",
]
LAST_NAMES = [
    "Almeida", "Brandt", "Costa", "Dahl", "Eriksen", "Ferreira", "Garcia", "Hansen", "Ibarra",
    "Jensen", "Keller", "Lindqvist", "Moreno", "Novak", "Okafor", "Petrov", "Quint", "Rossi",
    "Silva", "Torres", "Ulloa", "Vidal", "Weber", "Xavier", "Yilmaz", "Zanetti", "Baptiste",
    "Castell", "Duarte", "Engel", "Fontaine", "Gallo", "Haddad", "Ivers", "Jaramillo", "Kovac",
    "Lund", "Mensah", "Nilsen", "Ortega",
]
NATIONALITIES = ["Demo Isles", "Demo Peninsula", "Northland", "Eastmark", "Southport", "Westria"]
SQUAD_SHAPE = [("GK", 2), ("DF", 6), ("MF", 6), ("FW", 4)]


def poisson(rng: random.Random, lam: float) -> int:
    """Draw from a Poisson distribution (Knuth's method; fine for small lambdas)."""
    limit, k, p = math.exp(-lam), 0, 1.0
    while True:
        p *= rng.random()
        if p <= limit:
            return k
        k += 1


def round_robin(team_ids: list[int]) -> list[list[tuple[int, int]]]:
    """Double round robin with the circle method: returns rounds of (home, away) pairs."""
    teams = list(team_ids)
    half = len(teams) // 2
    first_leg = []
    for round_index in range(len(teams) - 1):
        pairs = []
        for i in range(half):
            a, b = teams[i], teams[-1 - i]
            pairs.append((a, b) if (round_index + i) % 2 == 0 else (b, a))
        first_leg.append(pairs)
        teams = [teams[0]] + [teams[-1]] + teams[1:-1]
    second_leg = [[(away, home) for home, away in pairs] for pairs in first_leg]
    return first_leg + second_leg


def make_player(rng: random.Random, player_id: int, team_id: int, position: str, number: int,
                strength: float, used_names: set[str]) -> dict:
    """One fictional player with season stats that fit their position and team strength."""
    while True:
        name = f"{rng.choice(FIRST_NAMES)} {rng.choice(LAST_NAMES)}"
        if name not in used_names:
            used_names.add(name)
            break
    appearances = rng.randint(4, CURRENT_MATCHDAY - 1)
    minutes = appearances * rng.randint(55, 90)
    per90 = minutes / 90
    attack = {"GK": 0.0, "DF": 0.05, "MF": 0.18, "FW": 0.45}[position] * strength
    creativity = {"GK": 0.01, "DF": 0.07, "MF": 0.22, "FW": 0.15}[position] * strength
    stats = {
        "appearances": appearances,
        "minutes": minutes,
        "goals": poisson(rng, attack * per90),
        "assists": poisson(rng, creativity * per90),
        "shots": poisson(rng, (attack * 5 + 0.2) * per90),
        "key_passes": poisson(rng, (creativity * 6 + 0.1) * per90),
        "passes": int(per90 * rng.uniform(*{"GK": (22, 32), "DF": (40, 70), "MF": (45, 85), "FW": (18, 35)}[position])),
        "pass_accuracy": round(rng.uniform(*{"GK": (62, 80), "DF": (78, 91), "MF": (80, 93), "FW": (68, 82)}[position]), 1),
        "tackles": poisson(rng, {"GK": 0.05, "DF": 2.4, "MF": 1.9, "FW": 0.6}[position] * per90),
        "interceptions": poisson(rng, {"GK": 0.1, "DF": 1.6, "MF": 1.1, "FW": 0.3}[position] * per90),
        "dribbles": poisson(rng, {"GK": 0.0, "DF": 0.4, "MF": 1.2, "FW": 1.8}[position] * per90),
        "saves": poisson(rng, 2.8 * per90) if position == "GK" else 0,
        "yellow": poisson(rng, 0.12 * per90),
        "red": 1 if rng.random() < 0.03 else 0,
        "rating": round(min(9.0, rng.uniform(6.2, 7.2) + (strength - 1) * 0.8), 2),
    }
    return {
        "id": player_id,
        "name": name,
        "team_id": team_id,
        "position": position,
        "number": number,
        "age": rng.randint(18, 35),
        "nationality": rng.choice(NATIONALITIES),
        "photo": None,
        "stats": stats,
    }


def pick_lineup(rng: random.Random, squad: list[dict]) -> dict:
    """A formation, a starting XI ordered GK -> defence -> midfield -> attack, and the bench."""
    formation = rng.choice(FORMATIONS)
    lines = [int(n) for n in formation.split("-")]
    need = {"GK": 1, "DF": lines[0], "MF": sum(lines[1:-1]), "FW": lines[-1]}
    start: list[int] = []
    for position in ("GK", "DF", "MF", "FW"):
        pool = [p for p in squad if p["position"] == position]
        start += [p["id"] for p in rng.sample(pool, need[position])]
    bench = [p["id"] for p in squad if p["id"] not in start]
    return {"formation": formation, "start_xi": start, "bench": bench}


def make_events(rng: random.Random, side: str, goals: int, lineup: dict, players: dict[int, dict]) -> list[dict]:
    """Goals, cards and substitutions for one team in one match."""
    starters = [players[pid] for pid in lineup["start_xi"]]
    weights = [{"GK": 0.01, "DF": 0.6, "MF": 2.0, "FW": 5.0}[p["position"]] for p in starters]
    events = []
    for _ in range(goals):
        scorer = rng.choices(starters, weights)[0]
        assister = rng.choice([p for p in starters if p["id"] != scorer["id"]]) if rng.random() < 0.7 else None
        kind = "penalty" if rng.random() < 0.1 else "goal"
        events.append({"minute": rng.randint(1, 90), "side": side, "type": kind,
                       "player": scorer["name"], "assist": assister["name"] if assister and kind == "goal" else None})
    for _ in range(poisson(rng, 1.8)):
        events.append({"minute": rng.randint(5, 90), "side": side, "type": "yellow",
                       "player": rng.choice(starters)["name"], "assist": None})
    if rng.random() < 0.06:
        events.append({"minute": rng.randint(30, 90), "side": side, "type": "red",
                       "player": rng.choice(starters[1:])["name"], "assist": None})
    outfield = lineup["start_xi"][1:]
    for player_out, player_in in zip(rng.sample(outfield, 3), rng.sample(lineup["bench"], 3)):
        events.append({"minute": rng.randint(55, 88), "side": side, "type": "sub",
                       "player": players[player_in]["name"], "assist": players[player_out]["name"]})
    return events


def make_stats(rng: random.Random, home_goals: int, away_goals: int, strength_gap: float) -> dict:
    """Full-time team stats as [home, away] pairs."""
    possession = max(28, min(72, round(50 + strength_gap * 25 + rng.uniform(-8, 8))))
    shots_home = home_goals + poisson(rng, 9 + strength_gap * 6)
    shots_away = away_goals + poisson(rng, 8 - strength_gap * 6)
    return {
        "possession": [possession, 100 - possession],
        "shots": [shots_home, shots_away],
        "shots_on_target": [min(shots_home, home_goals + poisson(rng, 2.5)), min(shots_away, away_goals + poisson(rng, 2.2))],
        "corners": [poisson(rng, 5 + strength_gap * 3), poisson(rng, 4.5 - strength_gap * 3)],
        "fouls": [poisson(rng, 11), poisson(rng, 11.5)],
    }


def build() -> dict:
    rng = random.Random(SEED)
    leagues, teams, players, matches = [], [], [], []
    used_names: set[str] = set()
    match_id = 1000
    for league in LEAGUES:
        leagues.append({k: league[k] for k in ("id", "name", "country", "zones")} | {"logo": None})
        league_team_ids, strengths = [], {}
        squads: dict[int, list[dict]] = {}
        for index, (name, short, primary, secondary, strength) in enumerate(league["teams"]):
            team_id = league["id"] * 100 + index + 1
            league_team_ids.append(team_id)
            strengths[team_id] = strength
            teams.append({"id": team_id, "name": name, "short": short, "league_id": league["id"],
                          "crest": None, "primary": primary, "secondary": secondary,
                          "venue": f"{name.split()[0]} Stadium"})
            squad, number = [], 1
            for position, count in SQUAD_SHAPE:
                for _ in range(count):
                    squad.append(make_player(rng, team_id * 100 + number, team_id, position, number, strength, used_names))
                    number += 1
            squads[team_id] = squad
            players += squad
        by_id = {p["id"]: p for p in players}
        for matchday, pairs in enumerate(round_robin(league_team_ids), start=1):
            for slot, (home, away) in enumerate(pairs):
                match_id += 1
                gap = strengths[home] - strengths[away]
                home_goals = poisson(rng, max(0.2, 1.45 + gap * 1.1))
                away_goals = poisson(rng, max(0.2, 1.10 - gap * 1.0))
                match = {"id": match_id, "league_id": league["id"], "matchday": matchday,
                         "home_id": home, "away_id": away}
                if matchday == CURRENT_MATCHDAY:
                    match["start_offset_min"] = CURRENT_DAY_OFFSETS[slot]
                else:
                    match["day_offset"] = (matchday - CURRENT_MATCHDAY) * 7
                    match["time"] = KICKOFF_TIMES[slot]
                if matchday <= CURRENT_MATCHDAY:
                    lineups = {"home": pick_lineup(rng, squads[home]), "away": pick_lineup(rng, squads[away])}
                    events = (make_events(rng, "home", home_goals, lineups["home"], by_id)
                              + make_events(rng, "away", away_goals, lineups["away"], by_id))
                    match |= {"lineups": lineups, "events": sorted(events, key=lambda e: e["minute"]),
                              "stats": make_stats(rng, home_goals, away_goals, gap)}
                matches.append(match)
    return {"generated_with_seed": SEED, "current_matchday": CURRENT_MATCHDAY,
            "leagues": leagues, "teams": teams, "players": players, "matches": matches}


if __name__ == "__main__":
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps(build(), ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    print(f"Wrote {OUTPUT}")
