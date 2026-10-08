"""Read only fixed, committed reports. No database, conversation data or model calls."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
REPORTS = ('pilot-large.json', 'full-large.json', 'single-turn.json', 'single-turn-retry.json', 'compound-question.json')


def dashboard(directory=None):
    directory = Path(directory or ROOT / 'evaluation/results')
    rows, summaries, missing = [], [], []
    for name in REPORTS:
        path = directory / name
        if not path.is_file():
            missing.append(name)
            continue
        try:
            report = json.loads(path.read_text())
        except (ValueError, OSError):
            missing.append(name)
            continue
        timestamp = report.get('run_at_utc', report.get('generated_at'))
        if name in ['pilot-large.json', 'full-large.json']:
            sets = [('pilot', report)] if name == 'pilot-large.json' else [
                ('full_trilingual', report['pilot_on_full_corpus']), ('full_gold', report['gold_retrieval'])]
            for group, data in sets:
                summaries.append({'group': group, 'source': name,
                    'direct_recall': data.get('mean_recall_at_5', data.get('mean_recall_at_k')),
                    'expanded_coverage': data.get('mean_coverage_after_link_expansion'),
                    'model': report.get('index_spec', {}).get('model'), 'measured_at': timestamp})
                for case in data['cases']:
                    executed = bool(case.get('ranked_chunk_ids'))
                    rows.append({'id': f"{group}:{case['case_id']}", 'group': group, 'source': name,
                        'kind': 'retrieval', 'provenance': 'real' if executed else 'not_run',
                        'question': case.get('question', case.get('effective_query', case['case_id'])),
                        'language': case.get('language'), 'status': 'retrieval_only' if executed else 'not_run',
                        'measured_at': timestamp, 'model': report.get('index_spec', {}).get('model'),
                        'retrieval_ms': case.get('retrieval_ms'), 'llm_ms': None,
                        'total_ms': case.get('retrieval_ms'), 'chunks': len(case['ranked_chunk_ids']) if executed else None,
                        'embedding_input_tokens': case.get('input_tokens'), 'llm_input_tokens': None, 'llm_output_tokens': None,
                        'direct_recall': case.get('recall_at_5', case.get('recall_at_k')),
                        'expanded_coverage': case.get('coverage_after_link_expansion'),
                        'query_cached': case.get('query_result_reused', False)})
        else:
            cases = report.get('cases', [{'case': {'id': 'compound', 'message': report.get('question'),
                                                 'language': report.get('language')}, 'response': report.get('response', {})}])
            for item in cases:
                case, response = item['case'], item['response']
                metrics = response.get('metrics', {})
                rows.append({'id': f"{name}:{case['id']}", 'group': 'answers', 'source': name, 'kind': 'answer',
                    'provenance': 'real', 'question': case.get('message'), 'language': case.get('language'),
                    'status': response.get('action', 'error'), 'measured_at': timestamp,
                    'model': response.get('models', {}).get('llm'),
                    'retrieval_ms': metrics.get('retrieval_ms'), 'llm_ms': metrics.get('llm_ms'),
                    'total_ms': metrics.get('total_ms'), 'chunks': metrics.get('retrieved_chunks'),
                    'embedding_input_tokens': metrics.get('embedding_input_tokens'),
                    'llm_input_tokens': metrics.get('llm_input_tokens'), 'llm_output_tokens': metrics.get('llm_output_tokens'),
                    'direct_recall': None, 'expanded_coverage': None, 'query_cached': False})
    return {'summaries': summaries, 'cases': rows, 'missing_reports': missing,
            'live_model_called': False, 'quality_benchmark_complete': False,
            'limitations': ['historical_reports', 'retrieval_is_not_answer_quality', 'cached_timings_are_original',
                            'mock_tests_not_quality_scores', 'compound_answer_missing_condition_before_fix']}
