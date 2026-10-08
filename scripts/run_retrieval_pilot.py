"""Embed only the reviewed 12-chunk pilot and measure retrieval; no generated answers."""
import argparse
import hashlib
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

from dotenv import load_dotenv
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from backend.app.rag.index import VectorIndex, write_json
from evaluation.alignment import load_and_validate


def coverage(required, groups, ids):
    # A clause may contain several paragraphs. Require every paragraph in at least
    # one reviewed source language, rather than crediting a partial paragraph hit.
    return [gid for gid in required if any(set(source) <= ids and source
            for source in groups[gid]['source_evidence_ids'].values())]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=ROOT/'evaluation/results/pilot-large.json')
    args = parser.parse_args()
    review, evidence, validation = load_and_validate()
    pilot = json.loads((ROOT/'evaluation/retrieval_pilot.json').read_text())
    load_dotenv(ROOT/'.env', override=False)
    directory = ROOT/'data/chroma/pilot'
    index = VectorIndex(directory=directory, chunk_ids=pilot['target_chunk_ids']+pilot['distractor_chunk_ids'])
    started = time.perf_counter()
    build = index.build()
    build_ms = round((time.perf_counter()-started)*1000, 2)
    # Construct a second instance as a restart check. This must not embed documents.
    restarted = VectorIndex(directory=directory, chunk_ids=list(index.by_id))
    reuse = restarted.build()
    if not reuse['reused'] or reuse['input_tokens'] != 0:
        raise RuntimeError('Restart unexpectedly rebuilt document embeddings')
    groups = {g['clause_group_id']: g for g in review['groups']}
    cache_dir = directory/'query-results'/index.version
    cache_dir.mkdir(parents=True, exist_ok=True)
    rows, new_query_tokens = [], 0
    for case in pilot['cases']:
        cache_path = cache_dir/(case['case_id']+'.json')
        cached = json.loads(cache_path.read_text()) if cache_path.is_file() else None
        reused_query = bool(cached and cached.get('question') == case['question'])
        if reused_query:
            retrieval = cached['retrieval']
        else:
            retrieval = index.search(case['question'], top_k=5)
            write_json(cache_path, {'question':case['question'], 'retrieval':retrieval})
            new_query_tokens += retrieval['input_tokens']
        selected = [index.by_id[cid] for cid in retrieval['ranked_chunk_ids']]
        direct = {eid for chunk in selected for eid in chunk['evidence_ids']}
        expanded = direct | {eid for chunk in selected for eid in chunk['related_evidence_ids']}
        direct_hits = coverage(case['required_clause_group_ids'], groups, direct)
        expanded_hits = coverage(case['required_clause_group_ids'], groups, expanded)
        count = len(case['required_clause_group_ids'])
        rows.append({**case, **retrieval, 'query_result_reused':reused_query,
                     'direct_hit_groups':direct_hits, 'expanded_hit_groups':expanded_hits,
                     'recall_at_5':len(direct_hits)/count, 'coverage_after_link_expansion':len(expanded_hits)/count,
                     'missing_groups':sorted(set(case['required_clause_group_ids'])-set(expanded_hits)),
                     'retrieved_sources':[{'chunk_id':chunk['chunk_id'], 'evidence_ids':chunk['evidence_ids'],
                                           'pdf_pages':chunk['pdf_pages']} for chunk in selected]})
        print(case['case_id'], f'direct={len(direct_hits)}/{count}', f'expanded={len(expanded_hits)}/{count}', flush=True)
    report = {'stage':'PILOT_RETRIEVAL_ONLY', 'run_at_utc':datetime.now(timezone.utc).isoformat(),
              'index_spec':index.spec, 'index_version':index.version, 'alignment_source_hashes':review['source_hashes'],
              'pilot_sha256':hashlib.sha256((ROOT/'evaluation/retrieval_pilot.json').read_bytes()).hexdigest(),
              'build':build,'build_ms':build_ms,'restart_reuse':reuse,'preflight_validation':validation,
              'new_query_input_tokens':new_query_tokens,
              'mean_recall_at_5':sum(r['recall_at_5'] for r in rows)/len(rows),
              'mean_coverage_after_link_expansion':sum(r['coverage_after_link_expansion'] for r in rows)/len(rows),
              'cases':rows,
              'metric_definition':'Necessary clause group recall: all referenced paragraphs in at least one source language must be covered. Expansion is one hop of explicit footnote links, reported separately.',
              'limitations':['Only 12 preselected chunks; results do not represent the full 139-chunk corpus.',
                             'Bilingual chunks contain both languages; this does not prove retrieval from monolingual indexes.',
                             'No generated answers, guardrails or citation semantic accuracy were evaluated.',
                             'Cached cases retain original measured API timings and token usage; they are not new requests.']}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    write_json(args.output, report)
    print(json.dumps({'report':str(args.output),'mean_recall_at_5':report['mean_recall_at_5'],
                      'expanded_coverage':report['mean_coverage_after_link_expansion'],
                      'new_input_tokens':build['input_tokens']+new_query_tokens}, indent=2))


if __name__ == '__main__':
    main()
