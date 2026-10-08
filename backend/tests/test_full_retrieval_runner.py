"""Verify the evaluation runner with fake vectors and real local Chroma, no API."""
import contextlib,io,json,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
from backend.app.rag.index import ROOT,VectorIndex
from backend.tests.test_vector_index import FakeEmbeddings
from scripts import run_full_retrieval as runner

class FullRunnerTests(unittest.TestCase):
    def test_runner_separates_retrieval_from_unimplemented_guards_and_memory(self):
        with tempfile.TemporaryDirectory() as directory:
            temp=Path(directory);(temp/'evaluation').mkdir()
            for name in ['questions.json','retrieval_pilot.json']:
                (temp/'evaluation'/name).write_bytes((ROOT/'evaluation'/name).read_bytes())
            output=temp/'report.json'
            with patch.object(runner,'ROOT',temp),patch.object(runner,'VectorIndex',side_effect=lambda:VectorIndex(FakeEmbeddings(),temp/'index')),patch('sys.argv',['runner','--output',str(output)]),contextlib.redirect_stdout(io.StringIO()):
                runner.main()
            report=json.loads(output.read_text())
            self.assertEqual(report['index_spec']['model'],'test-only')
            self.assertEqual(report['index_spec']['chunk_count'],143)
            self.assertEqual(report['pilot_on_full_corpus']['case_count'],12)
            self.assertEqual(report['gold_retrieval']['measured_cases'],8)
            cases={c['case_id']:c for c in report['gold_retrieval']['cases']}
            self.assertEqual(cases['Q09']['status'],'NOT_RUN_GUARDRAILS_NOT_IMPLEMENTED')
            self.assertEqual(cases['Q07']['history_mode'],'USER_QUESTION_CONCATENATION')
            self.assertNotIn('假设基本派息率为4%',cases['Q07']['effective_query'])
