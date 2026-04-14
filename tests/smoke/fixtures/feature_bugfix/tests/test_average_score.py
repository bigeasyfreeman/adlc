import unittest

from src.scoreboard import average_score


class AverageScoreBugfixTest(unittest.TestCase):
    def test_average_score_uses_all_entries(self):
        entries = [
            {"name": "Ada", "points": 2},
            {"name": "Bob", "points": 4},
            {"name": "Cy", "points": 6},
        ]

        actual = average_score(entries)

        self.assertEqual(
            actual,
            4.0,
            "average should divide by the full entry count",
        )

    def test_average_score_handles_negative_values_with_full_count(self):
        entries = [
            {"name": "Ada", "points": 10},
            {"name": "Bob", "points": -2},
            {"name": "Cy", "points": 4},
        ]

        actual = average_score(entries)

        self.assertEqual(
            actual,
            4.0,
            "average should divide by the full entry count",
        )


if __name__ == "__main__":
    unittest.main()
