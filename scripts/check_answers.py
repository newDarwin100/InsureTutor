"""Explicit paid fixed-case check. Diagnostics stay in test reports, never user responses."""
import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'backend'))
from app.services.answer import answer
from app.services.responses import Responses

CASES = [
    {'id': 'A01', 'message': 'Is the illustrated 4% interest rate guaranteed? How does it differ from the 2.5% guarantee?', 'language': 'en'},
    {'id': 'A02', 'message': '定期提款需要保单生效多久？每月、每年的最低提款额和最低提款期限是多少？提款费和安排费一样吗？', 'language': 'zh-Hans'},
]


class RecordedModel(Responses):
    def __init__(self):
        super().__init__()
        self.outputs = []
    def structured(self, instructions, payload, output_type):
        value, usage = super().structured(instructions, payload, output_type)
        self.outputs.append({'type': output_type.__name__, 'value': value.model_dump(), 'usage': usage})
        return value, usage


def main(selected, output):
    load_dotenv(ROOT / '.env', override=False)
    report = {'generated_at': datetime.now(timezone.utc).isoformat(), 'mode': 'real_single_turn_service',
              'limits': 'Fixed examples only; model verification is not a guarantee. No memory or full guardrail evaluation.',
              'cases': []}
    path = ROOT / 'evaluation/results' / output
    for case in CASES:
        if selected and case['id'] != selected:
            continue
        model = RecordedModel()
        result = answer(case['message'], case['language'], model=model)
        report['cases'].append({'case': case, 'response': result, 'diagnostics': model.outputs})
        path.write_text(json.dumps(report, ensure_ascii=False, indent=2)+'\n')
        print(case['id'], result['action'], result['verification'], result['metrics'], flush=True)
    if any(c['response']['action'] != 'answered' for c in report['cases']):
        raise SystemExit('Answer failed; inspect diagnostics before an explicit retry.')
    print('Saved', path.relative_to(ROOT))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--case', choices=['A01', 'A02'])
    parser.add_argument('--output', choices=['single-turn.json', 'single-turn-retry.json'], default='single-turn.json')
    parser.add_argument('--run', action='store_true', required=True, help='Calls embedding and Responses APIs')
    args = parser.parse_args()
    main(args.case, args.output)
