"""Explicit, bounded live SSE check using three previously authorized fixed demo questions."""
import argparse
import json
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
BASE = 'http://127.0.0.1:8767'


def post(path, body, token=None):
    headers = {'Content-Type': 'application/json'}
    if token:
        headers['X-Conversation-Token'] = token
    return urlopen(Request(BASE + path, data=json.dumps(body).encode(), headers=headers), timeout=120)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run', action='store_true', help='Calls embedding and generation/check APIs via the local backend.')
    args = parser.parse_args()
    if not args.run:
        print('Prepared D01, D05, D06. Pass --run to perform paid live tests against localhost:8767.')
        return
    cases = {c['case']['id']: c['case'] for c in json.loads((ROOT / 'evaluation/results/demo-answers.json').read_text())['cases']}
    rows = []
    token = None
    for case_id in ['D01', 'D05', 'D06']:
        if case_id != 'D06':
            with post('/api/conversations', {}) as response:
                token = json.load(response)['token']
        question = cases[case_id]['message']
        began = time.perf_counter()
        first_text, final, deltas, content = None, None, 0, {}
        event, data = '', []
        with post('/api/chat/stream', {'message': question, 'language': 'auto'}, token) as response:
            for raw in response:
                line = raw.decode('utf-8').strip('\r\n')
                if line.startswith('event:'):
                    event = line[6:].strip()
                elif line.startswith('data:'):
                    data.append(line[5:].lstrip())
                elif not line and data:
                    value = json.loads('\n'.join(data))
                    data = []
                    if event == 'delta':
                        deltas += 1
                        content[value['index']] = value['text'] if value.get('replace') else content.get(value['index'], '') + value['text']
                        if first_text is None and value['text'].strip():
                            first_text = round((time.perf_counter()-began)*1000, 2)
                            print(json.dumps({'case': case_id, 'first_text_ms': first_text}, ensure_ascii=False), flush=True)
                    elif event == 'error':
                        raise RuntimeError(value['code'])
                    elif event == 'done':
                        final = value
                        if first_text is None and any(c['text'].strip() for c in final['claims']):
                            first_text = round((time.perf_counter()-began)*1000, 2)
                        break
        if final is None:
            raise RuntimeError('Stream ended without a final response')
        rows.append({'case_id': case_id, 'question': question, 'client_ttft_ms': first_text,
            'under_2_seconds': first_text is not None and first_text < 2000,
            'delta_events': deltas, 'delivery': 'verified_final' if not deltas else 'provisional',
            'draft_text_sent': bool(deltas),
            'client_total_ms': round((time.perf_counter()-began)*1000, 2), 'response': final})
        print(json.dumps({'case': case_id, 'action': final['action'], 'metrics': final['metrics']}, ensure_ascii=False), flush=True)
    path = ROOT / 'evaluation/results/streaming.json'
    report = {'measured_at': datetime.now(timezone.utc).isoformat(), 'provenance': 'real_api',
        'ttft_definition': 'HTTP submission to final checked answer availability; status/heartbeats/JSON fields excluded.',
        'target_ms': 2000, 'target_is_guarantee': False, 'cases': rows}
    if path.exists():
        report['previous_runs'] = [json.loads(path.read_text())]
    path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')


if __name__ == '__main__':
    main()
