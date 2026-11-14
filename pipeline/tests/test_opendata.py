"""Tests for reading the City's Open Data (btv/opendata.py). No network: the rows in
tests/fixtures/ are real rows copied from the portal on 13 Nov 2026, trimmed.
Run from the pipeline folder:  python -m unittest -v
"""

import json
import unittest
from pathlib import Path
from unittest import mock

from btv import opendata
from btv.opendata import group_votes, notice_text, parse_notice

FIXTURES = Path(__file__).parent / "fixtures"
NOTICES = {row["noticeId"]: row for row in json.loads((FIXTURES / "notices.json").read_text(encoding="utf-8"))}
VOTES = json.loads((FIXTURES / "votes.json").read_text(encoding="utf-8"))


class NoticeTextTests(unittest.TestCase):
    def test_paragraphs_entities_and_spaces(self):
        text = notice_text("<p>A&nbsp;&nbsp; <strong>B</strong> &amp; C</p>\n<p>&nbsp;</p><p>Second<br />line</p>")
        self.assertEqual(text, "A B & C\nSecond\nline")


class ParseNoticeTests(unittest.TestCase):
    def test_689_king_street_west(self):
        notice = parse_notice(NOTICES[8003])
        self.assertEqual(notice["id"], "8003")
        self.assertEqual(notice["date"], "2026-11-06")              # midnight in Toronto, not UTC
        self.assertEqual(notice["body"], "Toronto and East York Community Council")
        self.assertEqual(notice["application_numbers"], ["26 247458 STE 10 OZ"])
        self.assertEqual(notice["addresses"][0]["label"], "689 King Street West")
        self.assertAlmostEqual(notice["addresses"][0]["lat"], 43.6435, places=3)
        self.assertTrue(notice["documents"][0]["url"].startswith("https://"))
        self.assertTrue(notice["topics"][0].startswith("Planning > "))

    def test_no_contact_or_signature_is_kept(self):
        notice = parse_notice(NOTICES[8003])
        self.assertNotIn("contact", notice)
        self.assertNotIn("signedBy", notice)
        self.assertNotIn("Elvidge", json.dumps(notice))            # the signing clerk

    def test_permit_parking_notice_keeps_the_deadline_words(self):
        notice = parse_notice(NOTICES[7531])
        self.assertIn("please contact the Committee no later than 12:00 p.m. on Wednesday, June 10, 2026", notice["text"])


class GroupVotesTests(unittest.TestCase):
    def test_counts_per_motion_with_no_names(self):
        grouped = group_votes(VOTES, ["2024.NY15.4"])
        self.assertEqual(list(grouped), ["2024.NY15.4"])
        motions = {m["motion"]: m for m in grouped["2024.NY15.4"]}
        self.assertEqual((motions["Refer Item"]["yes"], motions["Refer Item"]["no"]), (1, 4))
        self.assertEqual((motions["Adopt Item as Amended"]["yes"], motions["Adopt Item as Amended"]["no"]), (4, 1))
        self.assertEqual(motions["Adopt Item as Amended"]["result"], "Carried, 4-1")   # the City's words, unchanged
        self.assertEqual(motions["Refer Item"]["committee"], "North York Community Council")
        self.assertEqual(motions["Refer Item"]["date"], "2024-07-09")
        text = json.dumps(grouped)
        for row in VOTES:
            self.assertNotIn(row["Last Name"], text)

    def test_other_items_are_left_out(self):
        self.assertEqual(group_votes(VOTES, ["2099.XX1.1"]), {})


class FetchRowsTests(unittest.TestCase):
    def test_pages_until_a_short_page(self):
        pages = [[{"n": i} for i in range(1000)], [{"n": 1000}]]
        calls = []

        def fake_call(action, **params):
            calls.append((action, params))
            if action == "package_show":
                return {"resources": [{"name": "old.csv", "id": "x", "datastore_active": False},
                                      {"name": "table", "id": "r1", "datastore_active": True}]}
            return {"records": pages[params["offset"] // 1000]}

        with mock.patch.object(opendata, "_call", fake_call), mock.patch.object(opendata.time, "sleep"):
            rows = opendata.fetch_rows("public-notices")
        self.assertEqual(len(rows), 1001)
        self.assertEqual([p.get("offset") for a, p in calls if a == "datastore_search"], [0, 1000])
        self.assertTrue(all(p["id"] == "r1" for a, p in calls if a == "datastore_search"))


if __name__ == "__main__":
    unittest.main()
