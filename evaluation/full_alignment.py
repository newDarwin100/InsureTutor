"""Validate coverage and provenance of the full extracted-text review."""
import hashlib
import json
from collections import Counter
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]


def validate_full_review(review, evidence, sources, pages):
    for key, raw in sources.items():
        if review['source_hashes'][key] != hashlib.sha256(raw).hexdigest():
            raise ValueError('Full review is stale; recheck changed source before indexing')
    covered, group_ids = set(), set()
    for group in review['groups']:
        if group['clause_group_id'] in group_ids:
            raise ValueError('Duplicate full-review group ID')
        group_ids.add(group['clause_group_id'])
        if group['status']=='CONTEXT_ONLY':
            ids=group['context_evidence_ids']
        else:
            languages=group['source_evidence_ids']
            if not languages.get('zh-Hant') or not languages.get('en'):
                raise ValueError('Bilingual source is incomplete')
            ids=set(languages['zh-Hant']+languages['en'])
        if any(i not in evidence for i in ids):
            raise ValueError('Unknown reviewed evidence')
        if sorted({evidence[i]['pdf_page'] for i in ids})!=group['pdf_pages']:
            raise ValueError('Reviewed page mismatch')
        covered.update(ids)
    covered.update(c['evidence_id'] for c in review['context_only'])
    if covered!=set(evidence):
        raise ValueError('Some evidence has no review disposition')
    raw_discarded={b['block_id'] for p in pages for b in p['discarded_blocks']}
    audited=[b['block_id'] for b in review['discarded_block_audit']]
    if set(audited)!=raw_discarded or len(audited)!=len(set(audited)):
        raise ValueError('Discarded blocks were not fully audited')
    for row in review['discarded_block_audit']:
        if row['disposition']=='RESTORED' and row['block_id'] not in evidence:
            raise ValueError('Restored source is missing from knowledge')
    if review['simplified_chinese_source']:
        raise ValueError('Simplified translation is not PDF source')
    return {'evidence_count':len(evidence),'group_count':len(review['groups']),
            'status_counts':dict(Counter(g['status'] for g in review['groups'])),
            'discarded_blocks_audited':len(audited),'extracted_evidence_coverage':1.0,
            'all_pdf_visual_content_indexed':False}


def load_full_review():
    paths={'pdf':ROOT/'docs/FLEXI-ULife Prime Saver.pdf','evidence':ROOT/'data/processed/knowledge/evidence.json',
           'normalized':ROOT/'data/processed/mineru/pages.json'}
    sources={key:path.read_bytes() for key,path in paths.items()}
    review=json.loads((ROOT/'data/reviewed/full_alignment.json').read_text())
    evidence={e['evidence_id']:e for e in json.loads(sources['evidence'])}
    result=validate_full_review(review,evidence,sources,json.loads(sources['normalized']))
    return review,result


def render_full_review(review,result):
    lines=['# 全文提取数据核对记录','','依据MinerU的正文、表格、discarded_blocks核对。PDF为20页，页码含封面。',
           '当前292条证据都有对应关系或用途说明；185个分组包含正文对应、共享双语表格和上下文。简体中文用于提问/回答，原文仍为繁体和英文。','',
           '这不是“PDF每个图像字符都已入库”，也不是专业保险审校。','',
           '## 这次修了什么','','- 第19页英文免责声明原本在discarded_blocks；恢复为p019-d001。',
           '- 恢复封面产品类型、第3页退休标签、第20页客服地址，原JSON和来源指针保留。',
           '- 第18页表格第一行是条款内容，不应成为后续行的表头；去掉错误继承的退保说明/投保年龄前缀。',
           '- 增补保障增值、保证可保、末期病症的条件与不保事项关联。','',
           '## 不能自行统一的内容','']
    for group in review['groups']:
        if group['status'] in ['CONFLICT','WORDING_DIFFERENCE']:
            lines += [f"- {group['clause_group_id']}（PDF {group['pdf_pages']}）：{group['review_note']}"]
    lines += ['','## 图像与历史信息的限制','']+['- '+f['note'] for f in review['findings']]
    lines += ['','## 对应表','','同一ID同时出现在两栏，表示原块本身包含双语或共享数字，不是新增了一份译文。',
              '','| 分组 | 状态 | 繁体来源 | 英文来源 | PDF页 |','| --- | --- | --- | --- | --- |']
    for g in review['groups']:
        src=g['source_evidence_ids']
        lines.append(f"| {g['clause_group_id']} | {g['status']} | {', '.join(src.get('zh-Hant',g.get('context_evidence_ids',[])))} | {', '.join(src.get('en',[]))} | {g['pdf_pages']} |")
    lines += ['','## 验证','','运行 `.venv/bin/python scripts/check_full_alignment.py`。来源变化、证据漏项、页码错误或遗漏discarded块都会让检查失败。','',
              '状态统计：'+json.dumps(result['status_counts'],ensure_ascii=False)+'。']
    return '\n'.join(lines)+'\n'
