"""Exercise incomplete/refusal/schema failures without external requests."""
import io
import json
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'backend'))
from app.services.answer import Draft
from app.services.responses import ModelError, Responses


class ResponsesTests(unittest.TestCase):
    def invoke(self, value):
        with patch.dict('os.environ', {'OPENAI_API_KEY': 'test-only-key'}), patch(
                'app.services.responses.urlopen', return_value=io.BytesIO(json.dumps(value).encode())) as network:
            result = Responses().structured('system', {'question': 'fixed'}, Draft)
            request = network.call_args.args[0]
            body = json.loads(request.data)
            self.assertFalse(body['store'])
            self.assertNotIn('tools', body)
            self.assertEqual(body['text']['format']['type'], 'json_schema')
            self.assertTrue(body['text']['format']['strict'])
            self.assertNotIn('test-only-key', request.data.decode())
            return result

    def test_completed_structured_response(self):
        parsed, usage = self.invoke({'status': 'completed', 'output': [{'content': [{'type': 'output_text',
            'text': '{"action":"no_evidence","reasons":[],"claims":[]}'}]}], 'usage': {'input_tokens': 20, 'output_tokens': 8}})
        self.assertEqual(parsed.action, 'no_evidence')
        self.assertEqual(usage['input_tokens'], 20)

    def test_incomplete_refusal_and_invalid_json_do_not_become_answers(self):
        for value in [{'status': 'incomplete'}, {'status': 'completed', 'output': [{'content': [{'type': 'refusal'}]}]},
                      {'status': 'completed', 'output': [{'content': [{'type': 'output_text', 'text': 'not JSON'}]}]}]:
            with self.assertRaises(ModelError):
                self.invoke(value)


if __name__ == '__main__':
    unittest.main()
