import copy
import json
import unittest
from evaluation.alignment import ROOT, load_and_validate, validate_review

class AlignmentTests(unittest.TestCase):
    def setUp(self):
        self.review, self.evidence, _ = load_and_validate()
        self.raw = (ROOT/'data/processed/knowledge/evidence.json').read_bytes()
        self.pdf = (ROOT/'docs/FLEXI-ULife Prime Saver.pdf').read_bytes()
        self.pilot = json.loads((ROOT/'evaluation/retrieval_pilot.json').read_text())
        self.chunks = {c['chunk_id']:c for c in json.loads((ROOT/'data/processed/knowledge/chunks.json').read_text())}
    def check(self, **changes):
        args=dict(review=self.review,evidence=self.evidence,pdf_bytes=self.pdf,evidence_bytes=self.raw,pilot=self.pilot,chunks=self.chunks)
        args.update(changes)
        return validate_review(**args)
    def test_source_update_invalidates_previous_review(self):
        with self.assertRaisesRegex(ValueError,'Source changed'):
            self.check(evidence_bytes=self.raw+b' ')
        with self.assertRaisesRegex(ValueError,'Source changed'):
            self.check(pdf_bytes=self.pdf+b' ')
    def test_pilot_requires_conditions_and_three_query_languages(self):
        pilot=copy.deepcopy(self.pilot)
        pilot['cases'].pop()
        with self.assertRaisesRegex(ValueError,'three query languages'):
            self.check(pilot=pilot)
        evidence=copy.deepcopy(self.evidence)
        evidence['p012-b018']['text']=evidence['p012-b018']['text'].replace('three years','one year')
        with self.assertRaisesRegex(ValueError,'Checked condition missing'):
            self.check(evidence=evidence)
    def test_missing_language_cannot_be_reported_as_matched(self):
        review=copy.deepcopy(self.review)
        review['groups'][0]['source_evidence_ids']['en']=[]
        with self.assertRaisesRegex(ValueError,'missing one language'):
            self.check(review=review)
        self.assertFalse(self.check()['full_document_reviewed'])
        self.assertFalse(self.check()['embedding_performed'])
