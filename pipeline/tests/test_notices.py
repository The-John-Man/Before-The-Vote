"""Tests for turning City notices into cards (btv/notices.py, btv/geo.py). No network.
Run from the pipeline folder:  python -m unittest -v
"""

import json
import unittest
from datetime import date
from pathlib import Path

from btv.geo import load_wards, ward_at
from btv.opendata import parse_notice
from btv.notices import attach_notice, can_forget, is_selected, matching_item, notice_card, select, update_card

FIXTURES = Path(__file__).parent / "fixtures"
NOTICES = {row["noticeId"]: parse_notice(row) for row in json.loads((FIXTURES / "notices.json").read_text(encoding="utf-8"))}
WARDS = load_wards()
TODAY = date(2026, 11, 13)


class SelectionTests(unittest.TestCase):
    def test_recent_applications_and_meetings_are_chosen(self):
        self.assertTrue(is_selected(NOTICES[8003], TODAY))      # "Notice of Application", 6 Nov
        self.assertTrue(is_selected(NOTICES[8007], TODAY))      # "Notice of Public Meeting", 3 Nov

    def test_other_kinds_and_old_notices_are_not(self):
        self.assertFalse(is_selected(NOTICES[7982], TODAY))     # "Notice of Adoption": already decided
        self.assertFalse(is_selected(NOTICES[7531], TODAY))     # June: older than 45 days

    def test_a_meetings_topic_is_enough(self):
        notice = dict(NOTICES[7982], title="Public Notice - Something", topics=["Meetings > Notice of meeting"])
        self.assertTrue(is_selected(notice, TODAY))

    def test_newest_first_and_at_most_40(self):
        many = [dict(NOTICES[8003], id=str(n), date=f"2026-11-{1 + n % 10:02d}") for n in range(60)]
        chosen = select(many, TODAY)
        self.assertEqual(len(chosen), 40)
        self.assertEqual(chosen[0]["date"], "2026-11-10")
        self.assertTrue(all(a["date"] >= b["date"] for a, b in zip(chosen, chosen[1:])))


class WardTests(unittest.TestCase):
    def test_689_king_street_west_is_in_spadina_fort_york(self):
        place = NOTICES[8003]["addresses"][0]
        self.assertEqual(ward_at(place["lon"], place["lat"], WARDS), {"code": "10", "name": "Spadina-Fort York"})

    def test_lake_ontario_is_in_no_ward(self):
        self.assertIsNone(ward_at(-79.40, 43.55, WARDS))


class NoticeCardTests(unittest.TestCase):
    def test_rule_facts(self):
        card = notice_card(NOTICES[8003], WARDS, "2026-11-13")
        self.assertEqual(card["id"], "notice-8003")
        self.assertEqual(card["title_official"], NOTICES[8003]["title"])
        self.assertEqual(card["title_plain"], "")
        self.assertEqual(card["topic"], "Planning")
        self.assertEqual(card["place"]["label"], "689 King Street West")
        self.assertFalse(card["place"]["approx"])
        self.assertEqual(card["ward"]["code"], "10")
        self.assertEqual(card["stages"][0], {"key": "notice", "body": "staff", "label": "City notice", "date": "2026-11-06",
                                             "result": None, "result_claim": None, "can_speak": False})
        doc = card["documents"][0]
        self.assertEqual((doc["id"], doc["type"], doc["snapshot"]), ("n1", "notice", "snapshots/notice-8003.txt"))
        self.assertEqual(card["official_url"], doc["url"])
        self.assertTrue(card["notice_excerpt"].startswith("The application proposes to amend the Official Plan"))

    def test_address_outside_the_community_council_is_not_pinned(self):
        # The City's data places "411 Kennedy Avenue" in Parkdale; the notice is for Scarborough.
        card = notice_card(NOTICES[8007], WARDS, "2026-11-13")
        self.assertIsNone(card["place"])
        self.assertIsNone(card["ward"])
        self.assertEqual(len(card["unknowns"]), 2)


class MatchingTests(unittest.TestCase):
    def test_one_shared_application_number_merges(self):
        items = [{"id": "2026.TE1.1", "application_numbers": ["26 247458 STE 10 OZ"]}, {"id": "x", "application_numbers": []}]
        self.assertEqual(matching_item(NOTICES[8003], items), "2026.TE1.1")

    def test_unsure_means_no_merge(self):
        items = [{"id": "a", "application_numbers": ["26 247458 STE 10 OZ"]}, {"id": "b", "application_numbers": ["26 247458 STE 10 OZ"]}]
        self.assertIsNone(matching_item(NOTICES[8003], items))
        self.assertIsNone(matching_item(NOTICES[8003], [{"id": "c"}]))

    def test_attach_adds_the_notice_once(self):
        item = {"id": "2026.TE1.1", "documents": [{"id": "d1"}, {"id": "n1", "notice_id": "1"}]}
        item, notes = attach_notice(item, NOTICES[8003], "2026-11-13")
        self.assertEqual(item["documents"][-1]["id"], "n2")
        self.assertEqual(len(notes), 1)
        self.assertEqual(attach_notice(item, NOTICES[8003], "2026-11-14"), (item, []))


class UpdateAndForgetTests(unittest.TestCase):
    def test_handwritten_sentences_survive_an_update(self):
        old = notice_card(NOTICES[8003], WARDS, "2026-11-13")
        old["claims"].append({"id": "c1", "section": "what", "text": "Written by a person.", "sources": []})
        old["title_plain"] = "A hotel and homes on King West"
        item, notes = update_card(old, notice_card(NOTICES[8003], WARDS, "2026-11-20"))
        self.assertEqual(item, old)                      # same notice, same facts: nothing changes
        self.assertEqual(notes, [])

    def test_old_rule_only_cards_are_forgotten(self):
        card = notice_card(NOTICES[8003], WARDS, "2026-11-13")
        self.assertFalse(can_forget(card, date(2027, 3, 1)))      # 115 days
        self.assertTrue(can_forget(card, date(2027, 3, 10)))      # 124 days
        card["claims"].append({"id": "c1", "text": "Written by a person."})
        self.assertFalse(can_forget(card, date(2027, 3, 10)))
        self.assertFalse(can_forget({"id": "2024.NY15.4", "claims": []}, date(2030, 1, 1)))


if __name__ == "__main__":
    unittest.main()
