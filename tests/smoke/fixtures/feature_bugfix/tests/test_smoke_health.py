import unittest

from src.scoreboard import average_score


class SmokeHealthTest(unittest.TestCase):
    def test_empty_average_is_zero(self):
        self.assertEqual(average_score([]), 0.0)


if __name__ == "__main__":
    unittest.main()
