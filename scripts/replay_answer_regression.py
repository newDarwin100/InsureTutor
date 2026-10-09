"""Replay four saved model outputs through presentation/conflict fixes; never call providers."""
import json
import sys
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'backend'))
from app.services.answer import answer
from app.services.responses import ClaimTextStream


class SnapshotIndex:
    knowledge = ROOT / 'data/processed/knowledge'

    def __init__(self, evidence_ids):
        self.by_id = {'snapshot': {'evidence_ids': evidence_ids, 'related_evidence_ids': []}}

    def ready(self):
        return True

    def search(self, question, top_k):
        return {'ranked_chunk_ids': ['snapshot'], 'index_version': 'saved-context-replay',
                'retrieval_ms': 0, 'query_embedding_ms': 0, 'vector_search_ms': 0, 'input_tokens': 0}


class SnapshotModel:
    model = 'saved-output-replay-not-new-generation'

    def __init__(self, calls):
        self.calls = iter(calls)

    def structured(self, instructions, payload, output_type):
        value = next(self.calls)['value']
        return output_type.model_validate_json(json.dumps(value)), {'ms': 0, 'input_tokens': 0, 'output_tokens': 0}

    def structured_stream(self, instructions, payload, output_type, emit):
        value, usage = self.structured(instructions, payload, output_type)
        parser = ClaimTextStream(emit, payload['language'])
        for char in json.dumps(value.model_dump(), ensure_ascii=False):
            parser.feed(char)
        return value, usage


def main():
    original = json.loads((ROOT / 'evaluation/results/answer-regression.json').read_text())
    report = {'mode': 'offline_saved_output_replay', 'api_calls': 0, 'new_latency_measurement': False,
              'limits': 'Tests local presentation and conflict-verdict handling only; provider audit is replayed, not rerun.',
              'cases': []}
    with patch('app.rag.index.Embeddings.embed', side_effect=AssertionError('No API in replay')), \
         patch('app.services.responses.urlopen', side_effect=AssertionError('No API in replay')), \
         patch.dict('os.environ', {'ANSWER_REPAIR_ENABLED': 'false'}):
        for row in original['cases']:
            case = row['case']
            if case['case_id'] not in ['R03', 'R06', 'R17', 'R19']:
                continue
            preview = {}
            def emit(event, data):
                if event == 'delta':
                    preview[data['index']] = data['text'] if data.get('replace') else preview.get(data['index'], '') + data['text']
            result = answer(case['question'], case['language'], index=SnapshotIndex(row['diagnostics'][0]['evidence_ids']),
                            model=SnapshotModel(row['diagnostics']), emit=emit)
            assert result['action'] in case['expected_actions'], case['case_id']
            assert list(preview.values()) == [c['text'] for c in result['claims']], case['case_id']
            assert all('' not in c['text'] and '【p' not in c['text'] for c in result['claims'])
            report['cases'].append({'case_id': case['case_id'], 'action': result['action'],
                                    'claims': result['claims'], 'citations': result['citations'],
                                    'preview_matches_final': True})
            print(case['case_id'], result['action'], 'saved-output replay passed; no provider calls')
    (ROOT / 'evaluation/results/answer-replay.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')


if __name__ == '__main__':
    main()
