"""Protect source traceability, numerical conditions and cross-page footnotes."""

import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))
from app.rag.preprocess import build, clean_text, expand_table, source_hash, split_text


class PreprocessingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        raw = (ROOT / "data/processed/mineru/pages.json").read_bytes()
        config = json.loads((ROOT / "data/processed/mineru/corrections.json").read_text())
        config["original_pages"] = json.loads(raw)
        cls.raw, cls.config = raw, config
        cls.result = build(json.loads(raw), config, source_hash(raw))
        cls.evidence = {e["evidence_id"]: e for e in cls.result["evidence"]}

    def test_amount_line_wrap_does_not_change_digits(self):
        self.assertEqual(clean_text("400,0\n00港元"), "400,000港元")
        self.assertIn("4.0%", clean_text("Base interest\n4.0%"))

    def test_conditions_are_attached_across_pages(self):
        unemployment = self.evidence["p011-b003"]
        self.assertIn("365", unemployment["text"])
        self.assertIn("p012-b009", unemployment["related_evidence_ids"])
        self.assertIn("基本計劃", self.evidence["p012-b009"]["text"])
        withdrawal = self.evidence["p010-b006"]
        self.assertIn("p012-b018", withdrawal["related_evidence_ids"])
        self.assertIn("10 years", self.evidence["p012-b018"]["text"])

    def test_rate_evidence_includes_non_guaranteed_disclaimer(self):
        ids = self.evidence["p016-b002-t1-r2"]["related_evidence_ids"]
        self.assertTrue(any("not guaranteed" in self.evidence[i]["text"] for i in ids))
        self.assertTrue(any("January 2022" in self.evidence[i]["text"] for i in ids))

    def test_repairs_preserve_original_and_conflict(self):
        note = self.evidence["p012-b018"]
        self.assertIn("HK$/MOP4,000", note["source_text"])
        self.assertIn("HK$4,000/MOP4,000", note["text"])
        conflict = self.evidence["p017-b001-t1-r6"]
        self.assertIn("SOURCE_CONFLICT", conflict["review_flags"])
        self.assertIn("40,000港元", conflict["text"])
        self.assertIn("HK$400,000", conflict["text"])

    def test_table_spans_keep_row_and_column_context(self):
        rows = [[{"text": "Plan", "rowspan": 2}, {"text": "young"}, {"text": "old"}],
                [{"text": "30,000"}, {"text": "15,000"}]]
        self.assertEqual(expand_table(rows)[1], ["Plan", "30,000", "15,000"])
        expense = self.evidence["p017-b001-t1-r7"]["text"]
        self.assertNotIn("Age 45", expense)

    def test_no_text_evidence_lost_and_all_links_resolve(self):
        ids = set(self.evidence)
        chunk_sources = {i for c in self.result["chunks"] for i in c["evidence_ids"]}
        for entry in self.evidence.values():
            self.assertLessEqual(set(entry["related_evidence_ids"]), ids)
            self.assertIn(entry["pdf_page"], range(1, 21))
            if entry["kind"] != "local_footnote":
                self.assertIn(entry["evidence_id"], chunk_sources)
        for chunk in self.result["chunks"]:
            self.assertLessEqual(len(chunk["text"]), 1200)

    def test_long_text_is_bounded_without_losing_tail(self):
        text = "條件。" * 600 + "FINAL-CONDITION"
        pieces = split_text(text, max_chars=300, overlap_chars=30)
        self.assertTrue(all(len(p) <= 300 for p in pieces))
        self.assertTrue(pieces[-1].endswith("FINAL-CONDITION"))
        with self.assertRaises(ValueError):
            split_text(text, max_chars=100, overlap_chars=100)

    def test_changed_input_requires_rechecking_repairs(self):
        with self.assertRaises(ValueError):
            build(json.loads(self.raw), self.config, "wrong-hash")


if __name__ == "__main__":
    unittest.main()
