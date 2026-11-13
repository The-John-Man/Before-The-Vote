"""Tests for the quote checker. Run from the pipeline folder:  python -m unittest -v"""

import unittest

from btv.verify import deadline_supported, find_quote, normalize, verify_claim

# A made-up page shaped like a real notice, including an awkward PDF line break.
PAGE = (
    "To submit comments or make a presentation to the Planning and Housing Commit-\n"
    "tee, please contact the Committee no later than 12:00 p.m. on Wednesday,\n"
    "June 10, 2026. The Committee will meet on Thursday, June 11, 2026."
)


class NormalizeTests(unittest.TestCase):
    def test_joins_hyphenated_line_breaks(self):
        self.assertIn("committee", normalize("Commit-\ntee"))

    def test_straightens_curly_quotes(self):
        self.assertEqual(normalize("“Hello”"), '"hello"')


class FindQuoteTests(unittest.TestCase):
    def test_finds_real_quote_across_line_breaks(self):
        quote = "please contact the Committee no later than 12:00 p.m. on Wednesday, June 10, 2026"
        self.assertEqual(find_quote(quote, ["cover page", PAGE]), 2)

    def test_rejects_invented_quote(self):
        quote = "residents must register no later than 5:00 p.m. on Friday, June 12, 2026"
        self.assertIsNone(find_quote(quote, [PAGE]))

    def test_rejects_quote_that_is_too_short(self):
        self.assertIsNone(find_quote("the Committee", [PAGE]))


class VerifyClaimTests(unittest.TestCase):
    def test_marks_sources_and_fixes_page(self):
        claim = {"sources": [
            {"doc": "d1", "page": 9, "quote": "The Committee will meet on Thursday, June 11, 2026"},
            {"doc": "d1", "page": 1, "quote": "Council approved the plan unanimously last week"},
        ]}
        verify_claim(claim, {"d1": [PAGE]})
        self.assertTrue(claim["sources"][0]["verified"])
        self.assertEqual(claim["sources"][0]["page"], 1)
        self.assertFalse(claim["sources"][1]["verified"])


class DeadlineTests(unittest.TestCase):
    def test_deadline_written_in_quote(self):
        self.assertTrue(deadline_supported(
            "2026-06-10T12:00:00-04:00", "no later than 12:00 p.m. on Wednesday, June 10, 2026"))

    def test_deadline_guessed_from_meeting_date_is_refused(self):
        # The quote only gives the meeting date (June 11), not a June 10 deadline.
        self.assertFalse(deadline_supported(
            "2026-06-10T12:00:00-04:00", "The Committee will meet on Thursday, June 11, 2026"))


if __name__ == "__main__":
    unittest.main()


class MeetingTimeTests(unittest.TestCase):
    """A time of day is only kept when the record states one."""

    def test_time_is_dropped_when_the_record_gives_only_the_day(self):
        from btv.verify import supported_moment
        quote = "This item will be considered by Toronto Preservation Board on November 16, 2026."
        self.assertEqual(supported_moment("2026-11-16T09:30:00-05:00", quote), "2026-11-16")

    def test_time_is_kept_when_written(self):
        from btv.verify import supported_moment
        quote = "no later than 12:00 p.m. on Wednesday, June 10, 2026"
        self.assertEqual(supported_moment("2026-06-10T12:00:00-04:00", quote), "2026-06-10T12:00:00-04:00")

    def test_wrong_day_gives_nothing(self):
        from btv.verify import supported_moment
        self.assertIsNone(supported_moment("2026-11-17", "considered on November 16, 2026"))
