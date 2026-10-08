"""Build the reviewed full corpus and evaluate retrieval only, without answer generation."""
import argparse,json,sys,time
from datetime import datetime,timezone
from pathlib import Path
from dotenv import load_dotenv
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from backend.app.rag.index import VectorIndex,digest,write_json
from evaluation.full_alignment import load_full_review
from evaluation.alignment import load_and_validate
from evaluation.scoring import score_case,validate_cases
from scripts.run_retrieval_pilot import coverage


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,default=ROOT/'evaluation/results/full-large.json')
    args=parser.parse_args()
    review,check=load_full_review();pilot_review,evidence,_=load_and_validate()
    pilot=json.loads((ROOT/'evaluation/retrieval_pilot.json').read_text())
    gold=json.loads((ROOT/'evaluation/questions.json').read_text())['cases']
    validate_cases(gold,evidence)
    load_dotenv(ROOT/'.env',override=False)
    index=VectorIndex()
    started=time.perf_counter();build=index.build();build_ms=round((time.perf_counter()-started)*1000,2)
    print('Full index:',len(index.chunks),'chunks; embedded:',build['embedded_chunks'],flush=True)
    groups={g['clause_group_id']:g for g in pilot_review['groups']}
    cache_dir=ROOT/'data/chroma/full-query-results'/index.version;cache_dir.mkdir(parents=True,exist_ok=True)
    query_tokens=0
    def retrieve(question):
        nonlocal query_tokens
        path=cache_dir/(digest(question)+'.json')
        if path.is_file():return json.loads(path.read_text()),True
        result=index.search(question);write_json(path,result);query_tokens+=result['input_tokens']
        return result,False
    pilot_rows=[]
    for case in pilot['cases']:
        result,cached=retrieve(case['question'])
        selected=[index.by_id[i] for i in result['ranked_chunk_ids']]
        direct={i for c in selected for i in c['evidence_ids']}
        expanded=direct|{i for c in selected for i in c['related_evidence_ids']}
        hits=coverage(case['required_clause_group_ids'],groups,direct)
        extended=coverage(case['required_clause_group_ids'],groups,expanded)
        count=len(case['required_clause_group_ids'])
        pilot_rows.append({**case,**result,'query_result_reused':cached,'direct_hit_groups':hits,'expanded_hit_groups':extended,
                           'recall_at_5':len(hits)/count,'coverage_after_link_expansion':len(extended)/count,
                           'missing_groups':sorted(set(case['required_clause_group_ids'])-set(extended))})
        print(case['case_id'],f'{len(hits)}/{count}',f'expanded {len(extended)}/{count}',flush=True)
    gold_rows=[]
    for case in gold:
        if not case['required_evidence_groups']:
            gold_rows.append({'case_id':case['case_id'],'status':'NOT_RUN_GUARDRAILS_NOT_IMPLEMENTED','recall_at_k':None})
            continue
        # Only earlier USER questions provide query context. Assistant assertions are never evidence.
        question='\n'.join([h['content'] for h in case['history'] if h['role']=='user']+[case['question']])
        result,cached=retrieve(question)
        score=score_case(case,result['ranked_chunk_ids'],index.by_id,evidence)
        gold_rows.append({**score,**result,'effective_query':question,'query_result_reused':cached,
                          'history_mode':'USER_QUESTION_CONCATENATION' if case['history'] else 'SINGLE_TURN',
                          'language':case['language'],'status':'RETRIEVAL_ONLY'})
        print(case['case_id'],score['recall_at_k'],score['coverage_after_link_expansion'],flush=True)
    scored=[c for c in gold_rows if c['recall_at_k'] is not None]
    average=lambda rows,key:sum(r[key] for r in rows)/len(rows)
    report={'stage':'FULL_CORPUS_RETRIEVAL_ONLY','run_at_utc':datetime.now(timezone.utc).isoformat(),
            'index_version':index.version,'index_spec':index.spec,'review_validation':check,
            'evaluation_hashes':{'pilot':digest(pilot),'gold':digest(gold)},'build':build,'build_ms':build_ms,
            'new_query_input_tokens':query_tokens,
            'pilot_on_full_corpus':{'case_count':len(pilot_rows),'mean_recall_at_5':average(pilot_rows,'recall_at_5'),
                'mean_coverage_after_link_expansion':average(pilot_rows,'coverage_after_link_expansion'),'cases':pilot_rows},
            'gold_retrieval':{'measured_cases':len(scored),'skipped_guardrail_cases':2,
                'mean_recall_at_5':average(scored,'recall_at_k'),
                'mean_coverage_after_link_expansion':average(scored,'coverage_after_link_expansion'),'cases':gold_rows},
            'limitations':['No generated answers or citation semantic accuracy scored; guardrail cases were not run.',
                           'Q07 concatenates earlier user questions; this does not validate conversation memory or reference resolution.',
                           'Pilot groups require complete clause paragraphs; gold groups accept a listed alternative. Their means are separate.',
                           'Known unextracted graphic content is listed in full_alignment.json; this is the full cleaned TEXT corpus.',
                           'Cached rankings retain original timings/usage; no new API call when reused.']}
    args.output.parent.mkdir(parents=True,exist_ok=True);write_json(args.output,report)
    print(json.dumps({k:report[k] for k in ['build','new_query_input_tokens']},indent=2))
    print('Pilot on full:',report['pilot_on_full_corpus']['mean_recall_at_5'],report['pilot_on_full_corpus']['mean_coverage_after_link_expansion'])
    print('Gold retrieval:',report['gold_retrieval']['mean_recall_at_5'],report['gold_retrieval']['mean_coverage_after_link_expansion'])

if __name__=='__main__':main()
