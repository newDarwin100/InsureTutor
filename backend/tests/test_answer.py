"""No paid calls: citation integrity, linked qualifications and fail-closed audit."""
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'backend'))
from app.services.answer import Draft, Verification, answer, gather_evidence, load_evidence, validate_citations


class Index:
    knowledge = ROOT / 'data/processed/knowledge'
    by_id = {'fake': {'evidence_ids': ['p008-b003'], 'related_evidence_ids': []}}
    def ready(self):
        return True
    def search(self, question, top_k):
        return {'ranked_chunk_ids': ['fake'], 'index_version': 'fake', 'retrieval_ms': 12,
                'query_embedding_ms': 10, 'vector_search_ms': 2, 'input_tokens': 5}


def draft(text='Charges are deducted before premiums are credited.', eid='p008-b003'):
    return Draft.model_validate({'action': 'answered', 'reasons': [], 'claims': [{'text': text,
                                'citations': [{'evidence_id': eid}]}]})


class Model:
    def __init__(self, response, supported=True):
        self.response, self.supported = response, supported
        self.calls = 0
    def structured(self, instructions, payload, output_type):
        self.calls += 1
        result = self.response if output_type == Draft else Verification(
            supported=self.supported, explanation='fixture', reason='supported' if self.supported else 'unsupported_claim')
        return result, {'ms': 15, 'input_tokens': 30, 'output_tokens': 10}


class AnswerTests(unittest.TestCase):
    def setUp(self):
        self.evidence, self.paired = load_evidence(Index.knowledge)

    def test_unknown_id_is_rejected_and_model_cannot_supply_quote(self):
        with self.assertRaises(ValueError):
            validate_citations(draft(eid='invented'), self.evidence)
        with self.assertRaises(ValueError):
            Draft.model_validate({'action': 'answered', 'reasons': [], 'claims': [{'text': 'bad', 'citations': [
                {'evidence_id': 'p008-b003', 'quote': 'translated or invented'}]}]})

    def test_footnotes_and_conflicting_counterpart_are_included(self):
        ctx, direct = gather_evidence(Index(), {'ranked_chunk_ids': ['fake']}, self.evidence, self.paired)
        self.assertIn('p008-b014', ctx)
        self.assertEqual(direct, ['p008-b003'])
        index = Index()
        index.by_id = {'fake': {'evidence_ids': ['p011-b009']}}
        ctx, _ = gather_evidence(index, {'ranked_chunk_ids': ['fake']}, self.evidence, self.paired)
        self.assertIn('p011-b015', ctx)
        with self.assertRaises(RuntimeError):
            gather_evidence(index, {'ranked_chunk_ids': ['fake']}, self.evidence, self.paired, max_chars=10)

    def test_withdrawal_footnote_hit_includes_cash_value_and_fee_limits(self):
        index = Index()
        index.by_id = {'fake': {'evidence_ids': ['p012-b007']}}
        context, _ = gather_evidence(index, {'ranked_chunk_ids': ['fake']}, self.evidence, self.paired)
        self.assertIn('p010-b005', context)
        self.assertIn('p010-b013', context)
        self.assertIn('p012-b011', context)

    def test_failure_message_explains_the_check_without_blaming_the_question(self):
        from app.services.answer import verification_message
        from app.guardrails.rules import Reason
        check = Verification(supported=False, reason='missing_condition', explanation='mock detail')
        message = verification_message('zh-Hans', Reason.INSURANCE_CONDITION_MISMATCH, check)
        self.assertIn('条款条件', message)
        self.assertIn('不需要缩小', message)

    def test_server_owns_page_and_link_and_separate_usage(self):
        result = answer('How are premiums credited?', 'en', index=Index(), model=Model(draft()))
        self.assertEqual(result['citations'][0]['quote'], self.evidence['p008-b003']['text'])
        self.assertEqual(result['citations'][0]['pdf_page'], 8)
        self.assertEqual(result['citations'][0]['url'], '/api/documents/flexi-ulife-prime-saver#page=8')
        self.assertEqual(result['metrics']['llm_input_tokens'], 60)
        self.assertEqual(result['metrics']['embedding_input_tokens'], 5)
        self.assertEqual(result['verification']['status'], 'passed')

    def test_valid_source_id_does_not_make_a_false_claim_valid(self):
        model = Model(draft(text='Every premium earns a guaranteed 4%.'), supported=False)
        result = answer('Is 4% guaranteed?', 'en', index=Index(), model=model)
        self.assertEqual(result['action'], 'verification_failed')
        self.assertEqual(result['claims'], [])
        self.assertEqual(result['citations'], [])
        self.assertEqual(model.calls, 2)

    def test_bad_citation_is_blocked_before_verifier(self):
        model = Model(draft(eid='invented'))
        result = answer('test', 'en', index=Index(), model=model)
        self.assertEqual(result['verification']['reason'], 'invalid_citation')
        self.assertEqual(model.calls, 1)

    def test_changed_reviewed_source_stops_before_paid_search(self):
        with patch('app.services.answer.load_evidence', side_effect=RuntimeError('changed')):
            with self.assertRaises(RuntimeError):
                answer('test', 'en', index=Index(), model=Model(draft()))


if __name__ == '__main__':
    unittest.main()
