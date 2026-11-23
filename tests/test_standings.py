import unittest

from services.standings import compute_standings, points_by_matchday, zone_for


def match(mid, home, away, hg, ag, day=1, status="FINISHED"):
    return {"id": mid, "league_id": 1, "matchday": day, "kickoff": f"2026-01-{day:02d}T15:00:00+00:00",
            "status": status, "minute": None, "home_id": home, "away_id": away, "home_goals": hg, "away_goals": ag}


class StandingsTest(unittest.TestCase):
    def setUp(self):
        self.matches = [match(1, 1, 2, 2, 0, 1), match(2, 3, 4, 1, 1, 1), match(3, 2, 3, 0, 3, 2), match(4, 4, 1, 1, 1, 2)]

    def test_points_and_order(self):
        table = compute_standings(self.matches, [1, 2, 3, 4])
        self.assertEqual([r["points"] for r in table], [4, 4, 2, 0])
        self.assertEqual([r["position"] for r in table], [1, 2, 3, 4])

    def test_goal_difference_breaks_ties(self):
        # Teams 1 and 3 both have 4 points; team 3 has GD +3, team 1 has GD +2.
        table = compute_standings(self.matches, [1, 2, 3, 4])
        self.assertEqual([r["team_id"] for r in table], [3, 1, 4, 2])
        self.assertEqual([table[0]["goal_diff"], table[1]["goal_diff"]], [3, 2])

    def test_name_breaks_full_ties(self):
        table = compute_standings([], [1, 2], names={1: "Zeta", 2: "Alpha"})
        self.assertEqual([r["team_id"] for r in table], [2, 1])

    def test_form_is_oldest_first_and_capped_at_five(self):
        many = [match(10 + i, 1, 2, 1 if i < 6 else 0, 0 if i < 6 else 1, day=i + 1) for i in range(8)]
        row = next(r for r in compute_standings(many, [1, 2]) if r["team_id"] == 1)
        self.assertEqual(row["form"], ["W", "W", "W", "L", "L"])
        self.assertEqual(row["played"], 8)

    def test_live_and_scheduled_matches_are_ignored(self):
        extra = self.matches + [match(9, 2, 1, 5, 0, 3, status="LIVE"), match(10, 2, 1, None, None, 4, status="SCHEDULED")]
        self.assertEqual(compute_standings(extra, [1, 2, 3, 4]), compute_standings(self.matches, [1, 2, 3, 4]))

    def test_unknown_teams_are_skipped(self):
        table = compute_standings([match(1, 1, 99, 1, 0)], [1])
        self.assertEqual(len(table), 1)
        self.assertEqual(table[0]["points"], 3)


class ZoneTest(unittest.TestCase):
    zones = {"top": 4, "europe": 2, "relegation": 3}

    def test_zones_for_20_team_league(self):
        self.assertEqual(zone_for(1, 20, self.zones), "top")
        self.assertEqual(zone_for(4, 20, self.zones), "top")
        self.assertEqual(zone_for(5, 20, self.zones), "europe")
        self.assertEqual(zone_for(7, 20, self.zones), None)
        self.assertEqual(zone_for(17, 20, self.zones), None)
        self.assertEqual(zone_for(18, 20, self.zones), "relegation")


class PointsByMatchdayTest(unittest.TestCase):
    def test_cumulative_points(self):
        matches = [match(1, 1, 2, 2, 0, 1), match(2, 2, 1, 1, 1, 2)]
        frames = points_by_matchday(matches, [1, 2])
        team1 = [f["points"] for f in frames if f["team_id"] == 1]
        self.assertEqual(team1, [3, 4])
        self.assertEqual(len(frames), 4)


if __name__ == "__main__":
    unittest.main()
