"""Tests for refresh.py --source opendata. No network: a fake fetch returns the real rows
saved in tests/fixtures/, and every file is written to a temporary folder.
Run from the pipeline folder:  python -m unittest -v
"""

import contextlib
import io
import json
import shutil
import tempfile
import unittest
from datetime import datetime
from pathlib import Path
from unittest import mock

import build_cards
import refresh
from btv import opendata, sources
from refresh import attach_votes

HERE = Path(__file__).parent
PIPELINE = HERE.parent
NOTICE_ROWS = json.loads((HERE / "fixtures" / "notices.json").read_text(encoding="utf-8"))
VOTE_ROWS = json.loads((HERE / "fixtures" / "votes.json").read_text(encoding="utf-8"))
NOW = datetime(2026, 11, 13, 20, 0, tzinfo=opendata.TORONTO)


def fake_fetch(dataset, resource_name=None, filters=None):
    if dataset == opendata.NOTICES:
        return NOTICE_ROWS
    wanted = set(filters["Agenda Item #"])
    return [row for row in VOTE_ROWS if row["Agenda Item #"] in wanted]


def broken_fetch(dataset, resource_name=None, filters=None):
    raise ConnectionError("the portal did not answer")


class RefreshFromOpenDataTests(unittest.TestCase):
    def setUp(self):
        self.root = Path(tempfile.mkdtemp())
        for folder in ("items", "snapshots", "web"):
            (self.root / folder).mkdir()
        shutil.copy(PIPELINE / "city.json", self.root / "city.json")
        shutil.copy(PIPELINE / "items" / "2024.NY15.4.json", self.root / "items")
        shutil.copy(PIPELINE / "snapshots" / "2024.NY15.4.txt", self.root / "snapshots")
        patches = [
            mock.patch.object(refresh, "HERE", self.root), mock.patch.object(refresh, "ITEMS", self.root / "items"),
            mock.patch.object(refresh, "SNAPSHOTS", self.root / "snapshots"),
            mock.patch.object(refresh, "STATUS", self.root / "web" / "status.json"),
            mock.patch.object(refresh, "DECISIONS", self.root / "web" / "decisions.json"),
            mock.patch.object(refresh, "toronto_now", lambda: NOW),
            mock.patch.object(build_cards, "HERE", self.root), mock.patch.object(build_cards, "WEB_DATA", self.root / "web"),
            mock.patch.object(sources, "HERE", self.root),
        ]
        for patch in patches:
            patch.start()
            self.addCleanup(patch.stop)
        self.addCleanup(shutil.rmtree, self.root)

    def run_refresh(self, fetch=fake_fetch, argv=()):
        with contextlib.redirect_stdout(io.StringIO()):
            return refresh.main(list(argv), fetch=fetch, draft=lambda item, today: None)   # no AI in tests

    def read(self, relative):
        return json.loads((self.root / relative).read_text(encoding="utf-8"))

    def test_creates_notice_cards_and_attaches_votes(self):
        self.run_refresh()
        self.assertTrue((self.root / "items" / "notice-8007.json").exists())
        self.assertTrue((self.root / "snapshots" / "notice-8007.txt").exists())
        self.assertFalse((self.root / "items" / "notice-7982.json").exists())    # not a meeting or application notice
        cards = {c["id"]: c for c in self.read("web/decisions.json")["decisions"]}
        kennedy = cards["notice-8007"]
        self.assertEqual(kennedy["say"]["deadline"], "2026-11-24T12:00:00-05:00")   # passed the unchanged guard
        self.assertTrue(all(c["verified"] for c in kennedy["claims"]))
        self.assertTrue(kennedy["facts_only"])
        votes = cards["2024.NY15.4"]["votes_from_record"]
        self.assertEqual([(m["motion"], m["result"], m["yes"], m["no"]) for m in votes["motions"]],
                         [("Refer Item", "Lost, 1-4", 1, 4), ("Adopt Item as Amended", "Carried, 4-1", 4, 1)])
        self.assertEqual(votes["dataset"], opendata.VOTES)
        status = self.read("web/status.json")
        self.assertTrue(status["sources"]["notices"]["ok"])
        self.assertEqual(status["items"]["notice-8007"]["source"], "City open data")

    def test_not_written_yet_note_goes_once_ai_sentences_pass(self):
        def fake_draft(item, today):
            if item["id"] != "notice-8007":
                return 0
            item["claims"].append({"id": "a1", "section": "what", "ai_drafted": True,
                                   "text": "Eight rental homes would be torn down.",
                                   "sources": [{"doc": "n1", "quote": "The application proposes to demolish eight existing rental dwelling units"}]})
            return 1
        with contextlib.redirect_stdout(io.StringIO()):
            refresh.main([], fetch=fake_fetch, draft=fake_draft)
        notes = " ".join(n for u in self.read("items/notice-8007.json")["updates"] for n in u["notes"])
        self.assertIn("1 of 1 sentences passed", notes)
        self.assertNotIn("not written yet", notes)

    def test_an_identical_second_run_writes_nothing(self):
        self.run_refresh()
        files = list((self.root / "items").glob("*")) + list((self.root / "snapshots").glob("*"))
        before = {path: path.stat().st_mtime_ns for path in files}
        report = self.run_refresh()
        self.assertEqual({path: path.stat().st_mtime_ns for path in files}, before)
        self.assertEqual(sorted((self.root / "items").glob("*")), sorted(p for p in files if p.parent.name == "items"))
        self.assertFalse(any("new card" in line for line in report))

    def test_a_portal_error_is_recorded_and_the_last_data_kept(self):
        self.run_refresh()
        kept = (self.root / "items" / "notice-8007.json").read_text(encoding="utf-8")
        report = self.run_refresh(fetch=broken_fetch)                        # does not raise
        self.assertEqual((self.root / "items" / "notice-8007.json").read_text(encoding="utf-8"), kept)
        status = self.read("web/status.json")
        self.assertFalse(status["sources"]["notices"]["ok"])
        self.assertIn("ConnectionError", status["sources"]["notices"]["error"])
        self.assertFalse(status["items"]["notice-8007"]["ok"])
        self.assertTrue(any("could not reach" in line for line in report))

    def test_old_rule_only_notice_cards_are_removed(self):
        old = {"id": "notice-1", "notice_id": "1", "notice_date": "2026-05-01", "claims": [], "documents": []}
        (self.root / "items" / "notice-1.json").write_text(json.dumps(old), encoding="utf-8")
        (self.root / "snapshots" / "notice-1.txt").write_text("old", encoding="utf-8")
        self.run_refresh()
        self.assertFalse((self.root / "items" / "notice-1.json").exists())
        self.assertFalse((self.root / "snapshots" / "notice-1.txt").exists())

    def test_saved_pages_need_a_folder(self):
        with self.assertRaises(SystemExit), contextlib.redirect_stderr(io.StringIO()):
            self.run_refresh(argv=["--source", "tmmis"])


class AttachVotesTests(unittest.TestCase):
    MOTION = {"committee": "North York Community Council", "date": "2024-07-09", "motion": "Adopt Item as Amended",
              "result": "Carried, 4-1", "yes": 4, "no": 1}

    def test_first_check_is_not_news(self):
        item, notes = attach_votes({"id": "2024.NY15.4"}, [self.MOTION], "2026-11-13")
        self.assertEqual(notes, [])
        self.assertEqual(item["votes_from_record"]["retrieved"], "2026-11-13")

    def test_a_new_vote_gets_a_note_in_the_citys_words(self):
        item, _ = attach_votes({"id": "x"}, [], "2026-11-13")
        item, notes = attach_votes(item, [self.MOTION], "2026-11-14")
        self.assertEqual(notes, ["A vote was recorded on July 9, 2024 at North York Community Council: "
                                 "Adopt Item as Amended, Carried, 4-1."])
        self.assertNotIn("approved", notes[0])

    def test_unchanged_votes_change_nothing(self):
        item, _ = attach_votes({"id": "x"}, [self.MOTION], "2026-11-13")
        self.assertIs(attach_votes(item, [dict(self.MOTION)], "2026-11-14")[0], item)


if __name__ == "__main__":
    unittest.main()
