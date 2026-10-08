"""Explicit paid regression for displayed examples; preserve failures and provider usage."""
import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'backend'))
from app.services.conversations import Conversations
from app.services.followup import conversational_answer
from app.services.responses import Responses

CASES = [
    {'id': 'D01', 'message': '4% 的利率是保证的吗？定期提款有什么条件？', 'language': 'zh-Hans'},
    {'id': 'D02', 'message': '4% 的利率是保證的嗎？定期提款有什麼條件？', 'language': 'zh-Hant'},
    {'id': 'D03', 'message': 'Is the 4% rate guaranteed? What are the periodic withdrawal conditions?', 'language': 'en'},
    {'id': 'D04', 'message': '被裁员后能停缴多久？附加保障也适用吗？', 'language': 'zh-Hans'},
    {'id': 'D05', 'message': '定期提款有什么条件？', 'language': 'zh-Hans'},
    {'id': 'D06', 'message': '那每年提款呢？', 'language': 'zh-Hans', 'follows': 'D05'},
]


class RecordedModel(Responses):
    def __init__(self):
        super().__init__()
        self.outputs = []

    def structured(self, instructions, payload, output_type):
        value, usage = super().structured(instructions, payload, output_type)
        self.outputs.append({'type': output_type.__name__, 'value': value.model_dump(), 'usage': usage,
                             'allowed_evidence_ids': [item['evidence_id'] for item in payload.get('evidence', [])]})
        return value, usage


def main(selected, path):
    load_dotenv(ROOT / '.env', override=False)
    report = json.loads(path.read_text()) if selected and path.is_file() else {
        'mode': 'real_demo_service_regression', 'cases': [],
        'limits': 'Fixed development examples, not overall quality or safety scores. Manual review is separate.'}
    store = Conversations()
    token = store.create()
    for case in CASES:
        if selected and case['id'] != selected:
            continue
        model = RecordedModel()
        item = {'case': case, 'measured_at': datetime.now(timezone.utc).isoformat(), 'manual_review': None}
        try:
            with store.use(token) as entry:
                entry.turns = []
                if case.get('follows'):
                    previous = next(row for row in report['cases'] if row['case']['id'] == case['follows'])
                    if previous['response']['action'] != 'answered':
                        raise RuntimeError('Follow-up prerequisite did not return an answer')
                    store.append(entry, previous['case']['message'], previous['resolved_question'], previous['response'])
                response, resolved = conversational_answer(case['message'], case['language'], entry.turns, model)
                store.append(entry, case['message'], resolved, response)
            item.update(response=response, resolved_question=resolved)
        except (RuntimeError, ValueError, StopIteration) as exc:
            item['error'] = str(exc) if not isinstance(exc, StopIteration) else 'Missing follow-up prerequisite'
        item['diagnostics'] = model.outputs
        previous_attempt = next((row for row in report['cases'] if row['case']['id'] == case['id']), None)
        if previous_attempt:
            report.setdefault('previous_attempts', []).append(previous_attempt)
        report['cases'] = [row for row in report['cases'] if row['case']['id'] != case['id']] + [item]
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')
        response = item.get('response', {})
        print(case['id'], response.get('action', 'error'), response.get('verification', {}),
              response.get('metrics', {}).get('total_ms'), flush=True)
    store.delete(token)
    if any(row.get('response', {}).get('action') != 'answered' for row in report['cases']):
        raise SystemExit('Some examples failed; inspect the saved diagnostics before retesting.')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run', action='store_true', required=True, help='Sends fixed questions/PDF evidence to OpenAI')
    parser.add_argument('--case', choices=[case['id'] for case in CASES])
    parser.add_argument('--output', type=Path, default=ROOT / 'evaluation/results/demo-answers.json')
    args = parser.parse_args()
    main(args.case, args.output)
