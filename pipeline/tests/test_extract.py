"""Tests for reading deadlines and meetings out of notices (btv/extract.py). No network.
Run from the pipeline folder:  python -m unittest -v
"""

import json
import unittest
from pathlib import Path

import build_cards
from btv.extract import notice_say, proposal_excerpt, sentences
from btv.geo import load_wards
from btv.notices import notice_card
from btv.opendata import parse_notice
from btv.verify import deadline_supported, find_quote

HERE = Path(__file__).parent
NOTICES = {row["noticeId"]: parse_notice(row) for row in json.loads((HERE / "fixtures" / "notices.json").read_text(encoding="utf-8"))}
CITY = json.loads((HERE.parent / "city.json").read_text(encoding="utf-8"))


class DeadlineTests(unittest.TestCase):
    def test_permit_parking_notice_PH31_6(self):
        notice = NOTICES[7531]
        claims, say = notice_say(notice["text"], notice["date"])
        quote = claims[0]["sources"][0]["quote"]
        self.assertIn("please contact the Committee no later than 12:00 p.m. on Wednesday, June 10, 2026", quote)
        self.assertEqual(say["deadline"], "2026-06-10T12:00:00-04:00")
        self.assertEqual(say["deadline_claim"], "r1")
        self.assertEqual(claims[0]["drafted_by"], "rule")
        self.assertEqual(claims[0]["section"], "say")
        self.assertIsNotNone(find_quote(quote, [notice["text"]]))        # the City's exact words
        self.assertTrue(deadline_supported(say["deadline"], quote))      # and the guard accepts the date

    def test_meeting_is_read_separately_and_keeps_its_time(self):
        notice = NOTICES[7531]
        claims, say = notice_say(notice["text"], notice["date"])
        self.assertEqual(say["meeting"], "2026-06-11T09:30:00-04:00")
        meeting = next(c for c in claims if c["id"] == say["meeting_claim"])
        self.assertIn("will hear from any person", meeting["sources"][0]["quote"])

    def test_a_meeting_only_notice_gives_no_deadline(self):
        text = ("NOTICE OF PUBLIC MEETING\nDate: November 25, 2026\nTime: 9:30 a.m., or as soon as possible thereafter\n"
                "You may send written comments by e-mail to the Committee.")
        claims, say = notice_say(text, "2026-11-03")
        self.assertIsNone(say["deadline"])
        self.assertEqual(say["meeting"], "2026-11-25T09:30:00-05:00")
        self.assertEqual([c["text"] for c in claims], ["The City's notice gives this date for the public meeting."])

    def test_appeal_deadlines_are_not_comment_deadlines(self):
        text = "A notice of appeal must be filed with the City Clerk no later than December 1, 2026."
        self.assertEqual(notice_say(text, "2026-11-01"), ([], {"deadline": None, "deadline_claim": None,
                                                                "meeting": None, "meeting_claim": None}))

    def test_a_garbled_time_is_dropped_not_guessed(self):
        # A real notice (7608) says "no later than 1 2:00 p.m.". Reading "2:00 p.m." would be wrong.
        text = "Please register to speak, no later than 1 2:00 p.m. on July 7, 2026 ."
        self.assertEqual(notice_say(text, "2026-06-18")[1]["deadline"], "2026-07-07")

    def test_a_council_meeting_is_not_a_public_meeting(self):
        text = "It is proposed that the amendments be adopted at the City Council meeting to be held on July 14, 2026."
        self.assertIsNone(notice_say(text, "2026-07-07")[1]["meeting"])


class NoticeCardTests(unittest.TestCase):
    def test_kennedy_road_card_has_a_deadline_and_a_meeting_stop(self):
        card = notice_card(NOTICES[8007], load_wards(), "2026-11-13")
        self.assertEqual(card["say"]["deadline"], "2026-11-24T12:00:00-05:00")
        self.assertEqual(card["say"]["meeting"], "2026-11-25T09:30:00-05:00")
        self.assertEqual(card["stages"][-1], {"key": "meeting", "body": "committee", "label": "Scarborough Community Council",
                                              "date": "2026-11-25", "result": None, "result_claim": None, "can_speak": True})

    def test_excerpt_is_a_whole_sentence(self):
        self.assertEqual(proposal_excerpt("PROPOSAL\nThe application proposes a park. Another sentence."),
                         "The application proposes a park.")
        self.assertIsNone(proposal_excerpt("The application proposes " + "very " * 80 + "much."))
        self.assertEqual(sentences("Call at 12:00 p.m. on Monday. Then stop."), ["Call at 12:00 p.m. on Monday.", "Then stop."])


class FactsOnlyRuleTests(unittest.TestCase):
    def test_rule_say_sentences_alone_leave_a_card_facts_only(self):
        item = json.loads((HERE.parent / "items" / "2026.PH31.6.json").read_text(encoding="utf-8"))
        item["claims"] = [c for c in item["claims"] if c["section"] == "say"]
        card = build_cards.build_card(item, CITY)
        self.assertTrue(any(c["verified"] for c in card["claims"]))       # the deadline sentence passed...
        self.assertTrue(card["facts_only"])                               # ...but nothing explains the item yet
        self.assertEqual(card["say"]["deadline"], "2026-06-10T12:00:00-04:00")


if __name__ == "__main__":
    unittest.main()
