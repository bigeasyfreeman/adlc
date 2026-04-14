import unittest

from src.scoreboard import render_scoreboard


class RenderScoreboardFeatureTest(unittest.TestCase):
    def test_render_scoreboard_outputs_ranked_lines_and_average_footer(self):
        entries = [
            {"name": "Ada", "points": 7},
            {"name": "Bob", "points": 5},
        ]

        actual = render_scoreboard(entries)

        self.assertEqual(
            actual,
            "1. Ada - 7\n2. Bob - 5\nAverage: 6.0",
            "render_scoreboard should emit ranked lines and average footer",
        )

    def test_render_scoreboard_returns_empty_message(self):
        actual = render_scoreboard([])

        self.assertEqual(
            actual,
            "No scores yet.",
            "render_scoreboard should return a clear empty message",
        )


if __name__ == "__main__":
    unittest.main()
