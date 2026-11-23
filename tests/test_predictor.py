import unittest

from services.predictor import outcome_probabilities, poisson_pmf, predict, team_strength


def match(mid, home, away, hg, ag, day=1):
    return {"id": mid, "league_id": 1, "matchday": day, "kickoff": f"2026-01-{day:02d}T15:00:00+00:00",
            "status": "FINISHED", "minute": None, "home_id": home, "away_id": away, "home_goals": hg, "away_goals": ag}


class PoissonTest(unittest.TestCase):
    def test_pmf_sums_to_one(self):
        self.assertAlmostEqual(sum(poisson_pmf(k, 1.7) for k in range(40)), 1.0, places=9)

    def test_probabilities_sum_to_one(self):
        p = outcome_probabilities(1.6, 1.1)
        self.assertAlmostEqual(p.home_win + p.draw + p.away_win, 1.0, places=9)

    def test_equal_teams_are_symmetric(self):
        p = outcome_probabilities(1.3, 1.3)
        self.assertAlmostEqual(p.home_win, p.away_win, places=9)

    def test_stronger_attack_wins_more(self):
        self.assertGreater(outcome_probabilities(2.5, 0.8).home_win, outcome_probabilities(1.2, 1.2).home_win)

    def test_top_scorelines_are_sorted(self):
        probs = [p for _, _, p in outcome_probabilities(1.5, 1.0).top_scorelines(5)]
        self.assertEqual(probs, sorted(probs, reverse=True))


class StrengthTest(unittest.TestCase):
    def setUp(self):
        # Team 1 scores a lot, team 2 concedes a lot.
        self.matches = [match(i, 1 if i % 2 else 2, 2 if i % 2 else 1, 3 if i % 2 else 0, 0 if i % 2 else 3, day=i)
                        for i in range(1, 9)]
        self.matches += [match(100 + i, 3, 4, 1, 1, day=i) for i in range(1, 9)]

    def test_strong_team_has_attack_above_average(self):
        self.assertGreater(team_strength(self.matches, 1).attack, 1.0)
        self.assertGreater(team_strength(self.matches, 2).defence, 1.0)

    def test_team_without_games_is_average(self):
        s = team_strength(self.matches, 99)
        self.assertAlmostEqual(s.attack, 1.0)
        self.assertAlmostEqual(s.defence, 1.0)
        self.assertEqual(s.games, 0)

    def test_window_limits_games(self):
        self.assertEqual(team_strength(self.matches, 1, window=3).games, 3)

    def test_strong_team_is_favourite(self):
        p = predict(self.matches, 1, 2)
        self.assertGreater(p.home_win, p.away_win)

    def test_what_if_attack_slider_moves_probability(self):
        base = predict(self.matches, 3, 4)
        boosted = predict(self.matches, 3, 4, home_attack=1.5)
        self.assertGreater(boosted.home_win, base.home_win)
        self.assertAlmostEqual(boosted.home_xg, base.home_xg * 1.5, places=9)

    def test_better_defence_lowers_opponent_goals(self):
        base = predict(self.matches, 3, 4)
        tight = predict(self.matches, 3, 4, home_defence=1.25)
        self.assertLess(tight.away_xg, base.away_xg)

    def test_no_matches_still_predicts(self):
        p = predict([], 1, 2)
        self.assertAlmostEqual(p.home_win + p.draw + p.away_win, 1.0, places=9)


if __name__ == "__main__":
    unittest.main()
