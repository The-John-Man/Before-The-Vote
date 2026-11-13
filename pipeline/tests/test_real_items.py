"""Tests that run the checker on the real Toronto page snapshots.

The 1875 Steeles item is the reason this project exists. Its official title ends in
"Approval" and its status says "Adopted", but City Council REFUSED the application.
A summary written from the title would be wrong. These tests prove the checker
blocks that mistake and accepts the true sentence.
"""

import unittest

from btv.sources import snapshot_pages
from btv.verify import deadline_supported, find_quote

STEELES = snapshot_pages("snapshots/2024.NY15.4.txt")
PARKDALE = snapshot_pages("snapshots/2027.PB1.6.txt")


class SteelesTrapTests(unittest.TestCase):
    def test_wrong_reading_is_blocked(self):
        # What a careless summary would claim. These words are not in the record.
        self.assertIsNone(find_quote("City Council approve the application for 1875 Steeles Avenue West", STEELES))

    def test_true_decision_is_found(self):
        self.assertIsNotNone(find_quote("City Council refuse the application for 1875 Steeles Avenue West", STEELES))

    def test_quote_may_span_paragraphs(self):
        quote = "City Council on July 24 and 25, 2024, adopted the following: 1. City Council refuse the application"
        self.assertIsNotNone(find_quote(quote, STEELES))


class ParkdaleDeadlineTests(unittest.TestCase):
    def test_meeting_date_is_not_accepted_as_a_deadline(self):
        # The page states when the board meets (16 Nov) but no deadline. A "15 Nov" deadline is a guess.
        quote = "This item will be considered by Toronto Preservation Board on November 16, 2026."
        self.assertIsNotNone(find_quote(quote, PARKDALE))
        self.assertFalse(deadline_supported("2026-11-15T16:30:00-05:00", quote))


if __name__ == "__main__":
    unittest.main()
