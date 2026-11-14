"""Tests for the scheduled refresh (refresh.py). No network: they use tests/sample_item.html.
Run from the pipeline folder:  python -m unittest -v
"""

import copy
import json
import unittest
from pathlib import Path

import build_cards
from btv.tmmis import parse_item
from new_item import starter_item
from refresh import body_lines, describe_changes, lost_sentences, merge_stages, record_facts, refresh_item

HERE = Path(__file__).parent
HTML = (HERE / "sample_item.html").read_text(encoding="utf-8")
CITY = json.loads((HERE.parent / "city.json").read_text(encoding="utf-8"))


def sample_record(html=HTML):
    record = parse_item(html, "2024.NY15.4")
    record["retrieved"] = "2026-11-14"
    return record


def rule(key, label, date, outcome="", can_speak=None, letters=0, speakers=0):
    return {"key": key, "label": label, "date": date, "outcome": outcome,
            "can_speak": key != "council" if can_speak is None else can_speak,
            "letters": letters, "speakers": speakers}


class DescribeChangesTests(unittest.TestCase):
    def test_first_check_has_nothing_to_compare(self):
        self.assertEqual(describe_changes(None, record_facts(sample_record())), [])

    def test_unchanged_page_gives_no_notes(self):
        facts = record_facts(sample_record())
        self.assertEqual(describe_changes(facts, copy.deepcopy(facts)), [])

    def test_new_stage_result_documents_and_letters_are_described(self):
        old = {"tracking": "a", "stages": [{"body": "Toronto Preservation Board", "date": "November 16, 2026", "status": ""}],
               "documents": 1, "written": 0, "speakers": 0}
        new = {"tracking": "b", "stages": [{"body": "Toronto Preservation Board", "date": "November 16, 2026", "status": "Adopted"},
                                           {"body": "City Council", "date": "December 9 and 10, 2026", "status": ""}],
               "documents": 3, "written": 4, "speakers": 2}
        notes = " ".join(describe_changes(old, new))
        self.assertIn("now shows a result from Toronto Preservation Board", notes)
        self.assertIn("City Council was added", notes)
        self.assertIn("2 new documents", notes)
        self.assertIn("4 more letters", notes)
        self.assertIn("2 more people registered to speak", notes)

    def test_status_word_is_never_repeated_as_a_result(self):
        # "Adopted" can mean a refusal was adopted (1875 Steeles). Notes must not echo it.
        old = {"tracking": "", "stages": [{"body": "City Council", "date": "x", "status": ""}], "documents": 0, "written": 0, "speakers": 0}
        new = {"tracking": "", "stages": [{"body": "City Council", "date": "x", "status": "Adopted"}], "documents": 0, "written": 0, "speakers": 0}
        self.assertNotIn("Adopted", " ".join(describe_changes(old, new)))


class MergeStagesTests(unittest.TestCase):
    # Shaped like the hand-made Parkdale item: the board's key is "board", Council has no date yet.
    ITEM_STAGES = [
        {"key": "staff", "body": "staff", "label": "Staff report", "date": "2026-10-28",
         "result": "recommend approval, with a condition", "result_claim": "c1", "can_speak": False},
        {"key": "board", "body": "committee", "label": "Toronto Preservation Board", "date": "2026-11-16",
         "result": None, "result_claim": None, "can_speak": True},
        {"key": "council", "body": "council", "label": "City Council", "date": None,
         "result": None, "result_claim": None, "can_speak": False},
    ]

    def test_existing_stages_are_matched_and_human_results_kept(self):
        merged = merge_stages(self.ITEM_STAGES, [
            rule("staff", "City staff report", "2026-10-28", "Recommended"),
            rule("committee", "Toronto Preservation Board", "2026-11-16", "Adopted"),
            rule("council", "City Council", "2026-12-09"),
        ])
        self.assertEqual([s["key"] for s in merged], ["staff", "board", "council"])
        self.assertEqual(merged[0]["result"], "recommend approval, with a condition")
        self.assertEqual(merged[1]["city_status"], "Adopted")
        self.assertIsNone(merged[1]["result"])            # a result needs a checked sentence
        self.assertEqual(merged[2]["date"], "2026-12-09")

    def test_a_new_committee_goes_before_council(self):
        merged = merge_stages(self.ITEM_STAGES, [
            rule("committee", "Toronto Preservation Board", "2026-11-16", "Adopted"),
            rule("committee", "Planning and Housing Committee", "2026-11-26"),
        ])
        self.assertEqual([s["label"] for s in merged],
                         ["Staff report", "Toronto Preservation Board", "Planning and Housing Committee", "City Council"])
        self.assertEqual(len({s["key"] for s in merged}), 4)   # keys stay unique
        self.assertTrue(merged[2]["can_speak"])


class RefreshItemTests(unittest.TestCase):
    def setUp(self):
        self.item = json.loads((HERE.parent / "items" / "2024.NY15.4.json").read_text(encoding="utf-8"))

    def test_first_refresh_sets_a_baseline_and_keeps_human_work(self):
        item, notes = refresh_item(self.item, sample_record(), "2026-11-14")
        self.assertEqual(notes, [])
        self.assertIn("record_facts", item)
        self.assertEqual([s["result"] for s in item["stages"]], [s["result"] for s in self.item["stages"]])
        self.assertEqual(item["claims"], self.item["claims"])

    def test_footer_links_saved_by_the_old_parser_are_removed(self):
        self.item["documents"].append({"id": "b9", "type": "background", "title": "|", "url": "https://www.toronto.ca/home/jobs/"})
        item, _ = refresh_item(self.item, sample_record(), "2026-11-14")
        self.assertNotIn("https://www.toronto.ca/home/jobs/", [d["url"] for d in item["documents"]])

    def test_counts_come_from_the_page(self):
        item, _ = refresh_item(self.item, sample_record(), "2026-11-14")
        committee = next(h for h in item["heard"] if h["stage"] == "committee")
        self.assertEqual((committee["written"], committee["speakers"]), (1, 3))   # the sample page's counts

    def test_a_later_change_is_noted_once(self):
        item, _ = refresh_item(self.item, sample_record(), "2026-11-14")
        extra = '<span class="rpt-text">(July 18, 2024) Letter from Resident Seven (CC.Main)</span><br>'
        changed = HTML.replace('<h4>Communications (City Council)</h4>\n   <div>', '<h4>Communications (City Council)</h4>\n   <div>' + extra)
        self.assertNotEqual(changed, HTML)
        item, notes = refresh_item(item, sample_record(changed), "2026-11-15")
        self.assertEqual(notes, ["1 more letter or e-mail from the public."])
        self.assertEqual(item["updates"][0], {"date": "2026-11-15", "notes": notes})
        _, again = refresh_item(item, sample_record(changed), "2026-11-16")
        self.assertEqual(again, [])                        # nothing new the next time


class FactsOnlyCardTests(unittest.TestCase):
    def test_a_new_item_is_published_as_facts_only(self):
        item = starter_item(sample_record())
        item, _ = refresh_item(item, sample_record(), "2026-11-14")
        card = build_cards.build_card(item, CITY)
        self.assertTrue(card["facts_only"])
        self.assertTrue(card["title_plain"].startswith("1875 Steeles Avenue West"))   # official title until a plain one is written
        self.assertNotIn("record_facts", card)
        self.assertEqual([s["key"] for s in card["stages"]], ["staff", "committee", "council"])

    def test_a_checked_item_is_not_facts_only(self):
        item = json.loads((HERE.parent / "items" / "2024.NY15.4.json").read_text(encoding="utf-8"))
        self.assertFalse(build_cards.build_card(item, CITY)["facts_only"])


class UpcomingMeetingTests(unittest.TestCase):
    """A new item has no checked sentence about its meeting, but the City's page lists the day."""

    def setUp(self):
        upcoming = HTML.replace("July 9, 2024", "December 1, 2026").replace("Status:</dt><dd class=\"inline\">Amended", "Status:</dt><dd class=\"inline\">")
        upcoming = upcoming[:upcoming.index('<div class="card">')] + upcoming[upcoming.rindex('<div class="card">'):]   # Council has not met
        self.record = parse_item(upcoming, "2099.NY1.1")
        self.record["retrieved"] = "2026-11-14"

    def test_the_listed_meeting_day_is_shown_without_a_time(self):
        item, _ = refresh_item(starter_item(self.record), self.record, "2026-11-14")
        card = build_cards.build_card(item, CITY)
        self.assertEqual(card["say"]["meeting"], "2026-12-01")
        self.assertEqual(card["say"]["meeting_from"], "page")
        self.assertIsNone(card["say"]["deadline"])          # a meeting is never turned into a deadline

    def test_a_day_that_is_not_a_listed_stop_is_dropped(self):
        item, _ = refresh_item(starter_item(self.record), self.record, "2026-11-14")
        item["say"]["meeting"] = "2026-11-30"
        self.assertIsNone(build_cards.build_card(item, CITY)["say"]["meeting"])


class LostSentenceTests(unittest.TestCase):
    def test_sentences_that_stop_matching_are_reported(self):
        before = {"claims": [{"id": "c1", "text": "A", "verified": True}, {"id": "c2", "text": "B", "verified": False}]}
        after = {"claims": [{"id": "c1", "text": "A", "verified": False}, {"id": "c2", "text": "B", "verified": False}]}
        self.assertEqual(lost_sentences(before, after), ["A"])
        self.assertEqual(lost_sentences(None, after), [])

    def test_copy_date_alone_is_not_a_change(self):
        a = "# copied 2026-11-13\nCity Council refuse the application."
        b = "# copied 2026-11-14\nCity Council   refuse the application."
        self.assertEqual(body_lines(a), body_lines(b))


if __name__ == "__main__":
    unittest.main()
