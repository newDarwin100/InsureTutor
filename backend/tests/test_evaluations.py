"""Saved reports only: null measurements stay null and no model calls are permitted."""
import asyncio
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'backend'))
from app.services.evaluations import dashboard
from test_api import call


class EvaluationTests(unittest.TestCase):
    def test_report_reader_preserves_stage_failures_and_missing_measurements(self):
        data = dashboard()
        self.assertFalse(data['live_model_called'])
        self.assertFalse(data['quality_benchmark_complete'])
        summaries = {s['group']: s for s in data['summaries']}
        self.assertEqual(summaries['full_trilingual']['direct_recall'], .875)
        self.assertEqual(summaries['full_gold']['direct_recall'], .9375)
        self.assertTrue(any(c['status'] == 'verification_failed' for c in data['cases']))
        skipped = [c for c in data['cases'] if c['provenance'] == 'not_run']
        self.assertEqual(len(skipped), 2)
        self.assertTrue(all(c['total_ms'] is None and c['embedding_input_tokens'] is None for c in skipped))
        retrieval = [c for c in data['cases'] if c['kind'] == 'retrieval']
        self.assertTrue(all(c['llm_ms'] is None for c in retrieval))
        self.assertNotIn('diagnostics', str(data))
        self.assertNotIn('source_pointer', str(data))

    def test_missing_reports_are_visible_without_inventing_results(self):
        with tempfile.TemporaryDirectory() as directory:
            data = dashboard(directory)
        self.assertEqual(data['cases'], [])
        self.assertEqual(len(data['missing_reports']), 5)

    def test_route_is_read_only_and_does_not_call_models(self):
        with patch('app.services.responses.Responses.structured', side_effect=AssertionError('No API')), patch(
                'app.rag.index.Embeddings.embed', side_effect=AssertionError('No API')):
            status, _, body = asyncio.run(call('/api/evaluations'))
        self.assertEqual(status, 200)
        self.assertFalse(json.loads(body)['live_model_called'])


if __name__ == '__main__':
    unittest.main()
