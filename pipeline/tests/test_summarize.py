"""Tests for AI drafting (btv/summarize.py) and the .env loader. No network, no real model.
Run from the pipeline folder:  python -m unittest -v
"""

import copy
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import build_cards
from btv import summarize
from btv.env import load_env
from btv.tmmis import parse_item
from new_item import starter_item

HERE = Path(__file__).parent
HTML = (HERE / "sample_item.html").read_text(encoding="utf-8")
CITY = json.loads((HERE.parent / "city.json").read_text(encoding="utf-8"))
REAL_QUOTE = "City Council refuse the application for 1875 Steeles Avenue West"


def provider_for(env: dict):
    with mock.patch.dict(os.environ, env, clear=True), mock.patch.object(summarize, "load_env"):
        return summarize.choose_provider()


class ProviderTests(unittest.TestCase):
    def test_no_key_means_no_drafting(self):
        self.assertIsNone(provider_for({}))

    def test_the_provider_with_a_key_is_used(self):
        self.assertEqual(provider_for({"DEEPSEEK_API_KEY": "k"}), ("deepseek", "deepseek-chat"))
        self.assertEqual(provider_for({"OPENAI_API_KEY": "k"}), ("openai", "gpt-4o-mini"))
        self.assertEqual(provider_for({"OPENROUTER_API_KEY": "sk-or-k"}), ("openrouter", "deepseek/deepseek-chat"))

    def test_choice_and_model_can_be_set(self):
        both = {"OPENAI_API_KEY": "k", "DEEPSEEK_API_KEY": "k"}
        self.assertEqual(provider_for(both)[0], "openai")
        self.assertEqual(provider_for({**both, "BTV_AI_PROVIDER": "DeepSeek"})[0], "deepseek")
        self.assertEqual(provider_for({**both, "BTV_AI_MODEL": "gpt-4.1"}), ("openai", "gpt-4.1"))

    def test_chosen_provider_without_its_key_is_off(self):
        self.assertIsNone(provider_for({"BTV_AI_PROVIDER": "deepseek", "OPENAI_API_KEY": "k"}))

    def test_unknown_provider_is_an_error(self):
        with self.assertRaises(ValueError):
            provider_for({"BTV_AI_PROVIDER": "somebot", "OPENAI_API_KEY": "k"})


class EnvFileTests(unittest.TestCase):
    def test_reads_values_but_never_overrides_the_environment(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / ".env"
            path.write_text('# a note\nOPENAI_API_KEY="from-file"\nDEEPSEEK_API_KEY=from-file\n\nEMPTY=\n', encoding="utf-8")
            with mock.patch.dict(os.environ, {"DEEPSEEK_API_KEY": "from-secret"}, clear=True):
                load_env(path)
                self.assertEqual(os.environ["OPENAI_API_KEY"], "from-file")
                self.assertEqual(os.environ["DEEPSEEK_API_KEY"], "from-secret")
                self.assertNotIn("EMPTY", os.environ)


class DraftItemTests(unittest.TestCase):
    """A facts-only item gets AI sentences; only the ones whose quotes are real are shown."""

    def setUp(self):
        record = parse_item(HTML, "2024.NY15.4")
        record["retrieved"] = "2026-11-14"
        self.item = starter_item(record)          # quotes are checked against snapshots/2024.NY15.4.txt
        self.prompts = []

    def fake_model(self, prompt, provider, model):
        self.prompts.append((prompt, provider, model))
        return {"title_plain": "Council refused a big rezoning at 1875 Steeles",
                "topic": "Housing",
                "claims": [
                    {"section": "what", "stage": "council", "lenses": ["rent", "astrology"],
                     "text": "City Council refused the application.",
                     "sources": [{"doc": "anything", "quote": REAL_QUOTE}]},
                    {"section": "say", "stage": "board", "lenses": [],
                     "text": "City Council approved the application.",
                     "sources": [{"doc": "d1", "quote": "City Council approve the application for 1875 Steeles"}]},
                    {"section": "why", "text": "A sentence with no quote is dropped.", "sources": []},
                ],
                "unknowns": ["Why Council refused."]}

    def draft(self, item):
        with mock.patch.dict(os.environ, {"OPENAI_API_KEY": "test"}, clear=True), \
                mock.patch.object(summarize, "load_env"):
            return summarize.draft_item(item, "2026-11-14", ask=self.fake_model)

    def test_only_checked_sentences_are_published(self):
        self.assertEqual(self.draft(self.item), 2)
        self.assertIn("d1", self.prompts[0][0])
        self.assertIn("refuse the application", self.prompts[0][0])   # the record went to the model
        card = build_cards.build_card(copy.deepcopy(self.item), CITY)
        shown = [c["text"] for c in card["claims"] if c["verified"]]
        self.assertEqual(shown, ["City Council refused the application."])
        self.assertFalse(card["facts_only"])
        self.assertTrue(all(c["ai_drafted"] for c in card["claims"]))

    def test_drafts_are_tidied_into_the_item_shape(self):
        self.draft(self.item)
        first, second = self.item["claims"]
        self.assertEqual((first["id"], first["lenses"], first["sources"][0]["doc"]), ("c1", ["rent"], "d1"))
        self.assertEqual((second["section"], second["stage"]), ("what", None))   # unknown values reset
        self.assertEqual(self.item["title_plain"], "Council refused a big rezoning at 1875 Steeles")
        self.assertEqual(self.item["unknowns"], ["Why Council refused."])
        self.assertTrue(self.item["drafted_by"].startswith("openai gpt-4o-mini (AI), 2026-11-14"))

    def test_people_s_sentences_are_never_redrafted(self):
        written = json.loads((HERE.parent / "items" / "2024.NY15.4.json").read_text(encoding="utf-8"))
        before = copy.deepcopy(written)
        self.assertEqual(self.draft(written), 0)
        self.assertEqual(written, before)
        self.assertEqual(self.prompts, [])

    def test_an_item_is_drafted_only_once(self):
        self.draft(self.item)
        self.item["claims"] = []
        self.assertEqual(self.draft(self.item), 0)
        self.assertEqual(len(self.prompts), 1)

    def test_a_card_with_only_rule_sentences_is_drafted_and_keeps_them(self):
        # A notice card: its deadline sentence was read by rules. That is not an explanation.
        rule = {"id": "r1", "section": "say", "drafted_by": "rule", "text": "Deadline.", "sources": [{"doc": "d1", "quote": REAL_QUOTE}]}
        self.item["claims"] = [rule]
        self.assertEqual(self.draft(self.item), 2)
        self.assertEqual(self.item["claims"][0], rule)
        self.assertEqual([c["id"] for c in self.item["claims"]], ["r1", "c1", "c2"])

    def test_no_key_leaves_the_item_facts_only(self):
        with mock.patch.dict(os.environ, {}, clear=True), mock.patch.object(summarize, "load_env"):
            self.assertIsNone(summarize.draft_item(self.item, "2026-11-14", ask=self.fake_model))
        self.assertEqual(self.item["claims"], [])


if __name__ == "__main__":
    unittest.main()
