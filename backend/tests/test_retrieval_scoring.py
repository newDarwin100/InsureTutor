"""Ensure expansion, duplicate ranks and safety cases cannot inflate recall."""

import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from evaluation.scoring import score_case, validate_cases


class ScoringTests(unittest.TestCase):
    def setUp(self):
        self.evidence = {"body": {"pdf_page": 11}, "note": {"pdf_page": 12}}
        self.chunks = {"c1": {"evidence_ids": ["body"], "related_evidence_ids": ["note"]}}
        self.case = {"case_id": "fixture", "required_evidence_groups": [
            {"group_id": "body", "alternative_evidence_ids": ["body"]},
            {"group_id": "note", "alternative_evidence_ids": ["note"]}]}

    def test_expansion_is_not_reported_as_recall(self):
        result = score_case(self.case, ["c1"], self.chunks, self.evidence)
        self.assertEqual(result["recall_at_k"], 0.5)
        self.assertEqual(result["coverage_after_link_expansion"], 1.0)
        self.assertIsNone(result["answer_correctness"])

    def test_safety_cases_have_no_retrieval_score(self):
        case = {"case_id": "safety", "required_evidence_groups": []}
        result = score_case(case, [], self.chunks, self.evidence)
        self.assertIsNone(result["recall_at_k"])

    def test_invalid_or_duplicate_rankings_rejected(self):
        for ranks in [["missing"], ["c1", "c1"]]:
            with self.assertRaises(ValueError):
                score_case(self.case, ranks, self.chunks, self.evidence)

    def test_reference_cases_and_page_mapping_are_valid(self):
        cases = json.loads((ROOT / "evaluation/questions.json").read_text())["cases"]
        evidence = {e["evidence_id"]: e for e in json.loads(
            (ROOT / "data/processed/knowledge/evidence.json").read_text())}
        validate_cases(cases, evidence)
        self.assertEqual(len(cases), 10)
        self.assertEqual({c["language"] for c in cases}, {"en", "zh-CN", "zh-TW"})


if __name__ == "__main__":
    unittest.main()
