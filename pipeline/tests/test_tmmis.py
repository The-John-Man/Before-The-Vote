"""Tests for reading an item page and building the timeline. Run:  python -m unittest -v"""

import unittest
from pathlib import Path

from btv.timeline import authority, build_stages, documents, first_date, source_pages, wards
from btv.tmmis import parse_item

HTML = (Path(__file__).parent / "sample_item.html").read_text(encoding="utf-8")


class ParseTests(unittest.TestCase):
    def setUp(self):
        self.record = parse_item(HTML, "2024.NY15.4")
        self.council, self.committee = self.record["considerations"]

    def test_finds_both_considerations(self):
        self.assertEqual(self.council["body"], "City Council")
        self.assertEqual(self.committee["body"], "North York Community Council")
        self.assertEqual(self.committee["date_text"], "July 9, 2024")

    def test_reads_status_ward_and_decision(self):
        self.assertEqual(self.council["meta"]["Status"], "Adopted")
        self.assertEqual(self.committee["meta"]["Status"], "Amended")
        self.assertIn("refuse the application", self.council["sections"]["City Council Decision"])

    def test_tracking_summary(self):
        self.assertIn("without amendments", self.record["tracking"])
        self.assertNotIn("Expand All", self.record["tracking"])

    def test_counts_residents_but_never_keeps_their_names(self):
        self.assertEqual(self.council["counts"]["Communications (Community Council)"], 2)
        self.assertEqual(self.council["counts"]["Communications (City Council)"], 1)
        self.assertEqual(self.committee["counts"]["Speakers"], 3)
        self.assertNotIn("Resident", str(self.record))

    def test_documents_have_title_and_link(self):
        titles = [d["title"] for d in self.council["documents"]]
        self.assertEqual(titles[1], "Notice of Public Meeting")
        self.assertTrue(self.council["documents"][0]["url"].endswith("246991.pdf"))

    def test_motion_text_stays_on_one_line(self):
        self.assertIn("Motion to Adopt Item (Carried)", self.council["sections"]["Motions (City Council)"])


class TimelineTests(unittest.TestCase):
    def setUp(self):
        self.record = parse_item(HTML, "2024.NY15.4")

    def test_first_date(self):
        self.assertEqual(first_date("July 24 and 25, 2024"), "2024-07-24")
        self.assertEqual(first_date("(May 28, 2026) Report from staff"), "2026-05-28")
        self.assertIsNone(first_date("Notice of Public Meeting"))

    def test_stages_run_oldest_first(self):
        stages = build_stages(self.record)
        self.assertEqual([s["key"] for s in stages], ["staff", "committee", "council"])
        self.assertEqual(stages[0]["date"], "2024-06-20")
        self.assertTrue(stages[1]["can_speak"])
        self.assertFalse(stages[2]["can_speak"])
        self.assertEqual(stages[1]["speakers"], 3)
        self.assertEqual(stages[1]["letters"], 1)
        self.assertEqual(stages[2]["letters"], 1)

    def test_authority_wards_documents(self):
        self.assertEqual(authority(self.record), "decided")
        self.assertEqual(wards(self.record), [{"code": "06", "name": "York Centre"}])
        self.assertEqual(len(documents(self.record)), 2)   # the repeated report is listed once

    def test_source_pages(self):
        pages, labels = source_pages(self.record)
        self.assertEqual(len(pages), 3)
        self.assertEqual(labels[1], "City Council, July 24 and 25, 2024")


if __name__ == "__main__":
    unittest.main()


class StarterItemTests(unittest.TestCase):
    """new_item.py: what rules alone can fill in for a new decision."""

    def setUp(self):
        from new_item import snapshot_text, starter_item
        record = parse_item(HTML, "2024.NY15.4")
        record["retrieved"] = "2026-11-13"
        self.item = starter_item(record)
        self.text = snapshot_text(record)

    def test_starter_item_has_ward_stops_and_counts(self):
        self.assertEqual(self.item["ward"], {"code": "06", "name": "York Centre"})
        self.assertTrue(self.item["title_official"].startswith("1875 Steeles Avenue West"))
        self.assertEqual([s["key"] for s in self.item["stages"]], ["staff", "committee", "council"])
        self.assertEqual(self.item["heard"][0], {"stage": "committee", "written": 1, "speakers": 3})

    def test_results_are_left_empty_until_a_sentence_is_checked(self):
        self.assertTrue(all(s["result"] is None for s in self.item["stages"]))

    def test_snapshot_can_be_quoted_but_holds_no_resident_names(self):
        from btv.verify import find_quote
        page = "\n".join(line for line in self.text.splitlines() if not line.startswith("#"))
        self.assertIsNotNone(find_quote("City Council refuse the application for 1875 Steeles Avenue West", [page]))
        self.assertNotIn("Resident", self.text)


class UpcomingItemTests(unittest.TestCase):
    """An item that has not been to committee yet must not be shown as recommended by one."""

    def test_staff_recommendations_alone_are_only_proposed(self):
        html = HTML.replace("<h4>Community Council Recommendations</h4>", "<h4>Recommendations</h4>")
        html = html[:html.index('<div class="card">')] + html[html.rindex('<div class="card">'):]   # drop Council
        self.assertEqual(authority(parse_item(html, "x")), "proposed")
