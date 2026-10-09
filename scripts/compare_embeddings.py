"""Compare large/small on the same 143 chunks and 12 fixed multilingual queries."""
import argparse
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'backend'))
sys.path.insert(0, str(ROOT))
from app.rag.index import Embeddings, VectorIndex, write_json
from app.services.answer import load_evidence, gather_evidence
from evaluation.alignment import load_and_validate
from scripts.run_retrieval_pilot import coverage


def run(output):
    if output.exists():
        raise ValueError('Choose a new output path; previous measurements must be preserved')
    load_dotenv(ROOT / '.env', override=False)
    pilot = json.loads((ROOT / 'evaluation/retrieval_pilot.json').read_text())
    review, _, _ = load_and_validate()
    groups = {g['clause_group_id']: g for g in review['groups']}
    large = VectorIndex(Embeddings('text-embedding-3-large', 3072))
    if not large.ready():
        raise RuntimeError('Existing large index must be ready; this comparison does not rebuild it')
    # A separate root prevents replacing the application's active index.
    small = VectorIndex(Embeddings('text-embedding-3-small', 1536), ROOT / 'data/chroma/comparison-small')
    started = time.perf_counter()
    build = small.build()
    report = {'generated_at': datetime.now(timezone.utc).isoformat(), 'mode': 'real_embedding_comparison',
              'small_build': build, 'small_build_ms': round((time.perf_counter() - started) * 1000, 2),
              'cases': [], 'index_specs': {'large': large.spec, 'small': small.spec},
              'limits': ['12 development queries, not held-out or answer correctness.',
                         'Alternating sequential requests; timings are exploratory, not a repeated latency benchmark.',
                         'Compare default dimensions, so model and vector size both differ.',
                         'The current large index is reused; no large build-time comparison.']}
    evidence, paired = load_evidence(large.knowledge)
    output.parent.mkdir(parents=True, exist_ok=True)
    for n, case in enumerate(pilot['cases']):
        row = {'case': case, 'measurements': {}}
        order = [('large', large), ('small', small)]
        if n % 2:
            order.reverse()
        for name, index in order:
            result = index.search(case['question'], top_k=5)
            direct = {eid for cid in result['ranked_chunk_ids'] for eid in index.by_id[cid]['evidence_ids']}
            linked = direct | {eid for cid in result['ranked_chunk_ids'] for eid in index.by_id[cid]['related_evidence_ids']}
            context, _ = gather_evidence(index, result, evidence, paired)
            denominator = len(case['required_clause_group_ids'])
            measure = {**result,
                       'direct_recall_at_5': len(coverage(case['required_clause_group_ids'], groups, direct)) / denominator,
                       'chunk_link_coverage': len(coverage(case['required_clause_group_ids'], groups, linked)) / denominator,
                       'answer_context_coverage': len(coverage(case['required_clause_group_ids'], groups, set(context))) / denominator}
            row['measurements'][name] = measure
        report['cases'].append(row)
        write_json(output, report)
        print(case['case_id'], {name: m['direct_recall_at_5'] for name, m in row['measurements'].items()}, flush=True)
    report['summary'] = {name: {field: round(sum(row['measurements'][name][field] for row in report['cases']) / len(report['cases']), 4)
                                for field in ['direct_recall_at_5', 'chunk_link_coverage', 'answer_context_coverage', 'retrieval_ms']}
                         for name in ['large', 'small']}
    write_json(output, report)
    print(json.dumps(report['summary']), flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run', action='store_true', help='Embed 143 brochure chunks with small and 12 questions with each model')
    parser.add_argument('--output', type=Path, default=ROOT / 'evaluation/results/embedding-comparison.json')
    args = parser.parse_args()
    if args.run:
        run(args.output)
    else:
        print('No API calls. --run builds a separate small index (143 chunks), then 12 queries per model. No LLM calls.')
