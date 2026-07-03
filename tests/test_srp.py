import unittest

from providers.srp import CAUSE_SUMMARIES, summarize_cause


class SummarizeCauseTests(unittest.TestCase):
    def test_known_summaries_are_five_words_or_fewer(self):
        for comments, cause in CAUSE_SUMMARIES.items():
            with self.subTest(comments=comments):
                self.assertLessEqual(len(cause.split()), 5)

    def test_unknown_cause_uses_conservative_fallback(self):
        self.assertEqual(summarize_cause("New explanation"), "Other outage cause")

    def test_missing_cause_remains_missing(self):
        self.assertIsNone(summarize_cause(None))


if __name__ == "__main__":
    unittest.main()
