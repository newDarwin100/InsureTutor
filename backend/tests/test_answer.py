"""No paid calls: citation integrity, linked qualifications and fail-closed audit."""
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'backend'))
from app.services.answer import Draft, Verification, answer, gather_evidence, grounded_draft_type, load_evidence, validate_citations


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
        result = self.response if issubclass(output_type, Draft) else Verification(
            supported=self.supported, explanation='fixture', reason='supported' if self.supported else 'unsupported_claim')
        return result, {'ms': 15, 'input_tokens': 30, 'output_tokens': 10}


class AnswerTests(unittest.TestCase):
    def setUp(self):
        self.evidence, self.paired = load_evidence(Index.knowledge)

    def test_generated_script_and_markers_are_normalized_but_pdf_quote_is_unchanged(self):
        index = Index()
        index.by_id = {'fake': {'evidence_ids': ['p014-b012']}}
        model = Model(draft('期滿利益等於保單期滿日的賬戶價值。【p014-b012】', 'p014-b012'))
        result = answer('期满利益是多少？', 'zh-Hans', index=index, model=model)
        self.assertEqual(result['claims'][0]['text'], '期满利益等于保单期满日的账户价值。')
        self.assertEqual(result['citations'][0]['quote'], self.evidence['p014-b012']['text'])
        self.assertIn('賬戶', result['citations'][0]['quote'])

    def test_supported_conflict_verdict_is_accepted_only_for_a_reviewed_conflict_answer(self):
        class ConflictModel(Model):
            def structured(self, instructions, payload, output_type):
                if issubclass(output_type, Draft):
                    return super().structured(instructions, payload, output_type)
                return Verification(supported=self.supported, reason='source_conflict', explanation=''), {
                    'ms': 1, 'input_tokens': 1, 'output_tokens': 1}
        index = Index()
        index.by_id = {'fake': {'evidence_ids': ['p011-b009']}}
        value = draft('中文65岁或以前，英文before age65，边界未解决。', 'p011-b009').model_dump()
        value['action'] = 'source_conflict'
        from app.guardrails.rules import Reason
        value['reasons'] = [Reason.SOURCE_CONFLICT]
        value['claims'][0]['citations'].append({'evidence_id': 'p011-b015'})
        for supported in [True, False]:
            result = answer('Does the age limit include 65?', 'en', index=index,
                            model=ConflictModel(Draft.model_validate(value), supported))
            self.assertEqual(result['action'], 'source_conflict' if supported else 'verification_failed')
        ordinary = answer('How are premiums credited?', 'en', index=Index(), model=ConflictModel(draft()))
        self.assertEqual(ordinary['action'], 'verification_failed')

    def test_marker_only_claim_cannot_pass_as_an_empty_answer(self):
        result = answer('How are premiums credited?', 'en', index=Index(), model=Model(draft('【p008-b003】')))
        self.assertEqual(result['action'], 'verification_failed')
        self.assertEqual(result['claims'], [])

    def test_generation_schema_restricts_ids_to_this_requests_evidence(self):
        output = grounded_draft_type(['p008-b003', 'p008-b014', 'p008-b003'])
        schema = output.model_json_schema()
        self.assertEqual(schema['$defs']['GroundedReference']['properties']['evidence_id']['enum'],
                         ['p008-b003', 'p008-b014'])
        self.assertEqual(output.model_validate(draft().model_dump()).claims[0].citations[0].evidence_id,
                         'p008-b003')
        for eid in ['invented', 'p008-b003,p008-b014', 'p008-b003 ', 'p012-b007']:
            with self.subTest(eid=eid), self.assertRaises(ValueError):
                output.model_validate(draft(eid=eid).model_dump())
        with self.assertRaises(ValueError):
            grounded_draft_type([])

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
        self.assertIn('适用条件', message)
        self.assertIn('可以重试', message)
        self.assertNotIn('缩小问题', message)
        self.assertNotIn('已停止展示', message)

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
