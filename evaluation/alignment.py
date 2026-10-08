"""Check reviewed references stay valid; this does not automate semantic review."""
import hashlib
import json
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def validate_review(review, evidence, pdf_bytes, evidence_bytes, pilot, chunks):
    hashes = review['source_hashes']
    if hashes['pdf'] != hashlib.sha256(pdf_bytes).hexdigest() or hashes['evidence'] != hashlib.sha256(evidence_bytes).hexdigest():
        raise ValueError('Source changed: review bilingual clauses again before using the pilot')
    if review['languages']['simplified_chinese_source']:
        raise ValueError('Simplified Chinese translations must not be labelled PDF source')
    groups = {}
    for group in review['groups']:
        cid = group['clause_group_id']
        if cid in groups:
            raise ValueError('Duplicate clause group')
        groups[cid] = group
        if group['status'] not in {'MATCHED', 'WORDING_DIFFERENCE', 'CONFLICT', 'EN_ONLY', 'ZH_ONLY'}:
            raise ValueError('Unknown review status')
        sources = group['source_evidence_ids']
        for language in ['zh-Hant', 'en']:
            ids = sources.get(language, [])
            if not ids and group['status'] in {'MATCHED', 'WORDING_DIFFERENCE'}:
                raise ValueError('Reviewed bilingual group is missing one language')
            if any(eid not in evidence for eid in ids):
                raise ValueError('Unknown evidence ID')
            text = '\n'.join(evidence[eid]['text'] for eid in ids)
            for fragment in group['source_text_checks'].get(language, []):
                if fragment not in text:
                    raise ValueError(f'Checked condition missing in {cid}: {language}')
        ids = {eid for values in sources.values() for eid in values}
        if sorted({evidence[eid]['pdf_page'] for eid in ids}) != group['pdf_pages']:
            raise ValueError('Reviewed PDF page references are incorrect')
    target_ids = pilot['target_chunk_ids']
    sample_ids = target_ids + pilot['distractor_chunk_ids']
    if len(sample_ids) != len(set(sample_ids)) or any(cid not in chunks for cid in sample_ids):
        raise ValueError('Pilot contains missing or duplicate chunk IDs')
    selected = {eid for cid in target_ids for eid in chunks[cid]['evidence_ids']}
    reviewed = {eid for group in groups.values() for values in group['source_evidence_ids'].values() for eid in values}
    if not reviewed <= selected:
        raise ValueError('Pilot chunks are missing reviewed source evidence')
    cases, languages_by_question = set(), {}
    for case in pilot['cases']:
        if case['case_id'] in cases or not case['question'].strip():
            raise ValueError('Duplicate or empty pilot case')
        cases.add(case['case_id'])
        if any(cid not in groups for cid in case['required_clause_group_ids']):
            raise ValueError('Pilot refers to an unreviewed clause')
        base_id = case['case_id'].removesuffix('-' + case['language'])
        languages_by_question.setdefault(base_id, set()).add(case['language'])
    if any(langs != {'zh-Hans', 'zh-Hant', 'en'} for langs in languages_by_question.values()):
        raise ValueError('Pilot questions must each have all three query languages')
    return {'reviewed_groups': len(groups), 'reviewed_evidence': len(reviewed),
            'status_counts': dict(Counter(g['status'] for g in groups.values())),
            'pilot_chunks': len(sample_ids), 'pilot_questions': len(cases),
            'full_document_reviewed': False, 'embedding_performed': False}


def load_and_validate():
    review = json.loads((ROOT/'data/reviewed/pilot_alignment.json').read_text())
    evidence_bytes = (ROOT/'data/processed/knowledge/evidence.json').read_bytes()
    evidence = {e['evidence_id']: e for e in json.loads(evidence_bytes)}
    chunks = {c['chunk_id']: c for c in json.loads((ROOT/'data/processed/knowledge/chunks.json').read_text())}
    pilot = json.loads((ROOT/'evaluation/retrieval_pilot.json').read_text())
    pdf = (ROOT/'docs/FLEXI-ULife Prime Saver.pdf').read_bytes()
    result = validate_review(review, evidence, pdf, evidence_bytes, pilot, chunks)
    return review, evidence, result


def render_review(review, evidence, result):
    lines = ['# 小样本条款核对', '', '核对日期：2026-10-08。这里只检查利率、失业、提款选定的正文和脚注。', '',
             f"{result['reviewed_groups']}组条款，涉及{result['reviewed_evidence']}条证据；12组含义一致，1组有措辞差异。",
             '由开发助手对照PDF页面图像核对，不是外部保险专家审校。编号脚注的自动配对结果仍留在 alignment.json，本文件记录实际核对结论。', '',
             'PDF有繁体中文和英文来源。简体中文是提问和回答语言，不另造一份原文。', '',
             '## 逐项记录', '']
    for group in review['groups']:
        lines += [f"### {group['clause_group_id']} · {group['status']}", '',
                  'PDF实际页码：'+', '.join(map(str, group['pdf_pages']))+'（包含封面）。', '']
        for language in ['zh-Hant', 'en']:
            lines += [f'**{language} 来源**', '']
            for eid in group['source_evidence_ids'][language]:
                lines += [f"- `{eid}`：{evidence[eid]['text']}"]
            lines += ['']
        lines += ['**核对结果**', ''] + ['- '+fact for fact in group['checked_facts']]+['']
        if group['review_note']:
            lines += [group['review_note'], '']
    lines += ['## 下一步', '', '小样本选9个目标检索块、3个干扰块，共12块；4种问题分别用简体、繁体、英文提问，共12题。',
              '只准备好了文本和问题，还没向量化、没测召回。具体块和问题见 evaluation/retrieval_pilot.json。', '',
              '## 尚未完成', '']+['- '+note for note in review['limitations']]
    return '\n'.join(lines)+'\n'
