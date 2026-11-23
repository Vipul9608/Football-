import unittest
from datetime import datetime, timedelta, timezone

from services.data_source import (DemoSource, map_event, map_fixture, map_fixture_status, map_player,
                                  map_statistics, match_clock, parse_matchday)
from services.favorites import favorite_goals, score_snapshot, toggle
from services.layout import formation_lines, formation_positions
from services.player_stats import per90, percentile


class LayoutTest(unittest.TestCase):
    def test_formation_lines_include_goalkeeper(self):
        self.assertEqual(formation_lines("4-3-3"), [1, 4, 3, 3])
        self.assertEqual(formation_lines("4-2-3-1"), [1, 4, 2, 3, 1])

    def test_invalid_formation_falls_back(self):
        self.assertEqual(formation_lines("4-4-4"), [1, 4, 4, 2])
        self.assertEqual(formation_lines("abc"), [1, 4, 4, 2])
        self.assertEqual(formation_lines(None), [1, 4, 4, 2])

    def test_eleven_positions_on_correct_half(self):
        home, away = formation_positions("4-3-3", "home"), formation_positions("4-3-3", "away")
        self.assertEqual(len(home), 11)
        self.assertTrue(all(x < 50 for x, _ in home))
        self.assertTrue(all(x > 50 for x, _ in away))
        self.assertTrue(all(0 < y < 100 for _, y in home + away))


class FavoritesTest(unittest.TestCase):
    def live(self, mid, home, away, hg, ag):
        return {"id": mid, "status": "LIVE", "home_id": home, "away_id": away, "home_goals": hg, "away_goals": ag}

    def test_toggle(self):
        self.assertEqual(toggle({1}, 2), {1, 2})
        self.assertEqual(toggle({1, 2}, 2), {1})

    def test_detects_favourite_goal(self):
        before = score_snapshot([self.live(1, 10, 20, 0, 0)])
        goals = favorite_goals(before, [self.live(1, 10, 20, 1, 0)], {10})
        self.assertEqual([team for _, team in goals], [10])

    def test_ignores_non_favourites_and_new_matches(self):
        before = score_snapshot([self.live(1, 10, 20, 0, 0)])
        self.assertEqual(favorite_goals(before, [self.live(1, 10, 20, 0, 1)], {10}), [])
        self.assertEqual(favorite_goals(before, [self.live(2, 10, 30, 3, 0)], {10}), [])


class PlayerStatsTest(unittest.TestCase):
    def test_per90(self):
        self.assertAlmostEqual(per90({"stats": {"minutes": 180, "goals": 3}}, "goals"), 1.5)
        self.assertEqual(per90({"stats": {"minutes": 0, "goals": 3}}, "goals"), 0.0)

    def test_percentile_with_ties(self):
        self.assertEqual(percentile(5, [1, 2, 3, 4]), 100.0)
        self.assertEqual(percentile(0, [1, 2, 3, 4]), 0.0)
        self.assertEqual(percentile(2, [1, 2, 2, 3]), 50.0)
        self.assertEqual(percentile(1, []), 50.0)


class MatchClockTest(unittest.TestCase):
    def test_clock(self):
        self.assertEqual(match_clock(0), ("1'", 1))
        self.assertEqual(match_clock(30.5), ("31'", 31))
        self.assertEqual(match_clock(50), ("HT", 45))
        self.assertEqual(match_clock(60), ("46'", 46))
        self.assertEqual(match_clock(104), ("90'", 90))


class DemoSourceTest(unittest.TestCase):
    def setUp(self):
        self.start = datetime(2026, 11, 23, 14, 0, tzinfo=timezone.utc)
        self.clock = [self.start]
        self.source = DemoSource(now=lambda: self.clock[0], started_at=self.start)

    def test_current_matchday_has_live_finished_and_scheduled(self):
        current = [m for m in self.source.matches(1) if m["matchday"] == 15]
        self.assertEqual(sorted(m["status"] for m in current), ["FINISHED", "FINISHED", "LIVE", "LIVE", "SCHEDULED"])

    def test_live_scores_never_go_down_and_finish(self):
        live_ids = [m["id"] for m in self.source.matches(1) if m["status"] == "LIVE"]
        last = {}
        for minutes in range(0, 120, 5):
            self.clock[0] = self.start + timedelta(minutes=minutes)
            for m in self.source.matches(1):
                if m["id"] in live_ids:
                    total = m["home_goals"] + m["away_goals"]
                    self.assertGreaterEqual(total, last.get(m["id"], 0))
                    last[m["id"]] = total
        self.assertTrue(all(m["status"] == "FINISHED" for m in self.source.matches(1) if m["id"] in live_ids))

    def test_scores_match_goal_events(self):
        finished = [m for m in self.source.matches(2) if m["status"] == "FINISHED"]
        for m in finished[:20]:
            detail = self.source.match_detail(m)
            goals = [e for e in detail["events"] if e["type"] in ("goal", "penalty", "own_goal")]
            self.assertEqual(sum(e["side"] == "home" for e in goals), m["home_goals"])
            self.assertEqual(len(detail["lineups"]["home"]["start_xi"]), 11)

    def test_scheduled_match_has_no_detail(self):
        scheduled = next(m for m in self.source.matches(1) if m["status"] == "SCHEDULED")
        self.assertIsNone(self.source.match_detail(scheduled)["lineups"])
        self.assertIsNone(scheduled["home_goals"])


class ApiMappingTest(unittest.TestCase):
    def test_status_and_round(self):
        self.assertEqual(map_fixture_status("2H"), "LIVE")
        self.assertEqual(map_fixture_status("FT"), "FINISHED")
        self.assertEqual(map_fixture_status("NS"), "SCHEDULED")
        self.assertEqual(map_fixture_status("PST"), "POSTPONED")
        self.assertEqual(parse_matchday("Regular Season - 15"), 15)
        self.assertEqual(parse_matchday("Quarter-finals"), 0)

    def test_map_fixture(self):
        item = {"fixture": {"id": 7, "date": "2023-08-12T14:00:00+00:00", "status": {"short": "2H", "elapsed": 67}},
                "league": {"id": 39, "round": "Regular Season - 1"},
                "teams": {"home": {"id": 1, "name": "A"}, "away": {"id": 2, "name": "B"}},
                "goals": {"home": 2, "away": 1}}
        m = map_fixture(item)
        self.assertEqual((m["status"], m["minute"], m["matchday"], m["home_goals"]), ("LIVE", "67'", 1, 2))

    def test_map_event(self):
        goal = {"time": {"elapsed": 23, "extra": None}, "team": {"id": 2}, "player": {"name": "X"},
                "assist": {"name": "Y"}, "type": "Goal", "detail": "Normal Goal"}
        self.assertEqual(map_event(goal, home_id=1)["side"], "away")
        self.assertEqual(map_event(goal | {"detail": "Own Goal"}, 1)["type"], "own_goal")
        self.assertIsNone(map_event(goal | {"detail": "Missed Penalty"}, 1))
        self.assertIsNone(map_event(goal | {"type": "Var"}, 1))

    def test_map_statistics(self):
        response = [{"team": {"id": 1}, "statistics": [{"type": "Ball Possession", "value": "58%"}, {"type": "Total Shots", "value": 12}]},
                    {"team": {"id": 2}, "statistics": [{"type": "Ball Possession", "value": "42%"}, {"type": "Total Shots", "value": None}]}]
        self.assertEqual(map_statistics(response, 1), {"possession": [58, 42], "shots": [12, 0]})

    def test_map_player_without_stats(self):
        self.assertIsNone(map_player({"player": {"id": 1, "name": "X"}, "statistics": []}))


if __name__ == "__main__":
    unittest.main()
