"""Explicit fixed-question regression; no private conversation database or automatic retries."""
import argparse
import hashlib
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'backend'))
from app.services.conversations import Conversations
from app.services.followup import conversational_answer
from app.services.language import detect_language
from app.services.responses import Responses


class RecordedModel(Responses):
    def __init__(self):
        super().__init__()
        self.calls = []

    def record(self, value, usage, payload, output_type):
        self.calls.append({'type': output_type.__name__, 'value': value.model_dump(), 'usage': usage,
                           'evidence_ids': [e['evidence_id'] for e in payload.get('evidence', [])]})
        return value, usage

    def structured(self, instructions, payload, output_type):
        value, usage = super().structured(instructions, payload, output_type)
        return self.record(value, usage, payload, output_type)

    def structured_stream(self, instructions, payload, output_type, emit):
        value, usage = super().structured_stream(instructions, payload, output_type, emit)
        return self.record(value, usage, payload, output_type)


def validate(cases, evidence, available=()):
    ids = set(available)
    for case in cases:
        if case['case_id'] in ids or not case['question'].strip() or not case['expected_facts']:
            raise ValueError('Duplicate/incomplete reference case')
        if case.get('follows') and case['follows'] not in ids:
            raise ValueError('Follow-up prerequisite must precede the case')
        ids.add(case['case_id'])
        for group in case['required_evidence_groups']:
            sources = group['alternative_evidence_ids']
            if not sources or any(eid not in evidence for eid in sources):
                raise ValueError('Unknown reference evidence')
            if set(group['pdf_pages']) != {evidence[eid]['pdf_page'] for eid in sources}:
                raise ValueError('Incorrect reference pages')


def structural_checks(case, response, evidence):
    citations = response.get('citations', [])
    by_number = {c['number']: c for c in citations}
    originals = all(c['evidence_id'] in evidence and
                    c['quote'] == evidence[c['evidence_id']]['text'] and
                    c['pdf_page'] == evidence[c['evidence_id']]['pdf_page'] and
                    c['document_name'] == evidence[c['evidence_id']]['document_name'] and
                    c['url'] == f"/api/documents/{evidence[c['evidence_id']]['document_id']}#page={c['pdf_page']}"
                    for c in citations)
    linked = all(claim['citation_numbers'] and all(n in by_number for n in claim['citation_numbers'])
                 for claim in response.get('claims', []))
    cited = {c['evidence_id'] for c in citations}
    return {'action_matches': response.get('action') in case['expected_actions'],
            'language_matches': response.get('language') == case['language'],
            'original_citations_valid': originals and linked,
            'required_reasons_present': set(case['expected_reasons']) <= set(response.get('guardrail', {}).get('reasons', [])),
            'reference_groups_cited': [g['group_id'] for g in case['required_evidence_groups']
                                       if cited.intersection(g['alternative_evidence_ids'])],
            'semantic_support': 'manual_review_required'}


def run(cases, output, baseline=None):
    load_dotenv(ROOT / '.env', override=False)
    evidence = {e['evidence_id']: e for e in json.loads((ROOT / 'data/processed/knowledge/evidence.json').read_text())}
    prior = {r['case']['case_id']: r for r in baseline.get('cases', [])} if baseline else {}
    validate(cases, evidence, available=set(prior) - {c['case_id'] for c in cases})
    # A process-local store only; never open data/history or read actual user messages.
    store = Conversations()
    report = {'generated_at': datetime.now(timezone.utc).isoformat(), 'mode': 'real_fixed_service_streaming',
              'limits': ['Development set, not held-out quality or production latency.',
                         'Service TTFT excludes browser/network transport; refusals have no answer-text TTFT.',
                         'Current service first-text time waits for final verification; internal draft timing is diagnostic only.',
                         'Structural checks and provider audit do not replace manual review.'], 'cases': [],
              'source_hashes': {name: hashlib.sha256((ROOT / name).read_bytes()).hexdigest() for name in [
                  'backend/app/main.py', 'backend/app/services/answer.py', 'backend/app/services/responses.py',
                  'backend/app/services/answer_text.py', 'evaluation/answer_regression.json']}}
    if output.exists():
        raise ValueError('Choose a new output path; previous runs must be preserved')
    output.parent.mkdir(parents=True, exist_ok=True)
    for case in cases:
        model = RecordedModel()
        started = time.perf_counter()
        first_text = None
        draft_first_text = None
        def emit(kind, data):
            nonlocal draft_first_text
            if kind == 'delta' and data.get('text', '').strip() and draft_first_text is None:
                draft_first_text = round((time.perf_counter() - started) * 1000, 2)
        item = {'case': case, 'measured_at': datetime.now(timezone.utc).isoformat(), 'manual_review': None}
        token = store.create()
        try:
            with store.use(token) as entry:
                if case.get('follows'):
                    previous = next((r for r in report['cases'] if r['case']['case_id'] == case['follows']),
                                    prior.get(case['follows']))
                    if not previous or previous.get('response', {}).get('action') != 'answered':
                        raise RuntimeError('Prerequisite failed; follow-up was not executed')
                    store.append(entry, previous['case']['question'], previous['resolved_question'], previous['response'])
                language = detect_language(case['question'], fallback=case['language'])
                response, resolved = conversational_answer(case['question'], language, entry.turns, model, emit)
                if any(claim['text'].strip() for claim in response['claims']):
                    first_text = round((time.perf_counter() - started) * 1000, 2)
                item.update(response=response, resolved_question=resolved,
                            service_first_text_ms=first_text,
                            internal_draft_first_text_ms=draft_first_text,
                            structural_checks=structural_checks(case, response, evidence))
        except RuntimeError as exc:
            # Service/provider messages are sanitized; never save credentials or arbitrary exception data.
            item['error'] = str(exc)
        finally:
            store.delete(token)
        item['diagnostics'] = model.calls
        report['cases'].append(item)
        temporary = output.with_suffix('.tmp')
        temporary.write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')
        temporary.replace(output)
        response = item.get('response', {})
        print(case['case_id'], response.get('action', 'error'),
              'first_text_ms=', first_text, 'total_ms=', response.get('metrics', {}).get('total_ms'), flush=True)
    print('Saved', output.relative_to(ROOT) if output.is_relative_to(ROOT) else output, flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run', action='store_true', help='Send these fixed questions, linked history and PDF evidence to OpenAI')
    parser.add_argument('--output', type=Path, default=ROOT / 'evaluation/results/answer-regression.json')
    parser.add_argument('--cases', nargs='+', help='Explicit subset of reference IDs; no automatic failure retry')
    parser.add_argument('--baseline', type=Path, help='Prior fixed regression report for follow-up prerequisites')
    args = parser.parse_args()
    cases = json.loads((ROOT / 'evaluation/answer_regression.json').read_text())['cases']
    evidence = {e['evidence_id']: e for e in json.loads((ROOT / 'data/processed/knowledge/evidence.json').read_text())}
    validate(cases, evidence)
    baseline = json.loads(args.baseline.read_text()) if args.baseline else None
    if baseline:
        reference = {c['case_id']: c for c in cases}
        if any(r['case'] != reference.get(r['case']['case_id']) for r in baseline['cases']):
            raise ValueError('Baseline must match this exact fixed reference set, not private chats')
    if args.cases:
        if not set(args.cases) <= {c['case_id'] for c in cases}:
            raise ValueError('Unknown reference IDs')
        cases = [c for c in cases if c['case_id'] in args.cases]
    if args.run:
        run(cases, args.output, baseline)
    else:
        print(f'Validated {len(cases)} fixed cases. No API calls; use --run explicitly.')
