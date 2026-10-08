"""Cheap high-confidence rules. Ambiguous scope is classified in the answer call."""
import re
import unicodedata
from enum import Enum


class Reason(str, Enum):
    OUT_OF_SCOPE_GENERAL = 'OUT_OF_SCOPE_GENERAL'
    UNSUPPORTED_PRODUCT = 'UNSUPPORTED_PRODUCT'
    PERSONAL_FINANCIAL_ADVICE = 'PERSONAL_FINANCIAL_ADVICE'
    MEDICAL_OR_LEGAL_ADVICE = 'MEDICAL_OR_LEGAL_ADVICE'
    PROMPT_INJECTION = 'PROMPT_INJECTION'
    SECRET_OR_PRIVATE_DATA_REQUEST = 'SECRET_OR_PRIVATE_DATA_REQUEST'
    INSUFFICIENT_EVIDENCE = 'INSUFFICIENT_EVIDENCE'
    SOURCE_CONFLICT = 'SOURCE_CONFLICT'
    FALSE_PREMISE = 'FALSE_PREMISE'
    UNSUPPORTED_OUTPUT = 'UNSUPPORTED_OUTPUT'
    INVALID_CITATION = 'INVALID_CITATION'
    INSURANCE_CONDITION_MISMATCH = 'INSURANCE_CONDITION_MISMATCH'


class Action(str, Enum):
    ANSWER = 'ANSWER'
    CLARIFY = 'CLARIFY'
    CORRECT = 'CORRECT'
    REFUSE = 'REFUSE'
    REVISE = 'REVISE'


SECRET = re.compile(r'\bsk-[a-zA-Z0-9_-]{16,}\b')
RULES = [
    (Reason.SECRET_OR_PRIVATE_DATA_REQUEST,
     r'(show|reveal|print|give|disclose|expose).{0,50}(api.?key|system prompt|other users?.{0,20}(chat|conversation))|'
     r'(告诉|告訴|给我|給我|显示|顯示|输出|輸出|泄露|洩露).{0,25}(密钥|密鑰|api.?key|系统提示|系統提示|其他用户|其他用戶)'),
    (Reason.PROMPT_INJECTION,
     r'(ignore|bypass|override|disregard).{0,50}(instructions|rules|prompt|guardrails)|'
     r'(忽略|无视|無視|绕过|繞過).{0,20}(指令|规则|規則|提示|限制)|'
     r'(pretend|act as).{0,20}(unrestricted|jailbroken)|你现在是.{0,10}(管理员|管理員)'),
    (Reason.PERSONAL_FINANCIAL_ADVICE,
     r'(how much|which policy).{0,25}should i (buy|invest)|should i buy|recommend.{0,25}(for me|my portfolio)|'
     r'(我该|我該|我应该|我應該|帮我|幫我).{0,20}(买多少|買多少|买哪|買哪|决定买|決定買|配置保险|配置保險)|'
     r'(推荐|推薦).{0,15}(适合我|適合我)|保证我.{0,15}(赚|賺)'),
    (Reason.MEDICAL_OR_LEGAL_ADVICE,
     r'diagnose (me|my)|what (medicine|medication|treatment) should i|can i sue|'
     r'(诊断我|診斷我|我该吃|我該吃|我应该吃|我應該吃).{0,15}(病|药|藥)|'
     r'(我能否|我可以|帮我|幫我).{0,15}(起诉|起訴|打官司)'),
    (Reason.UNSUPPORTED_PRODUCT, r'\b(aia|axa|prudential|manulife)\b|友邦|保诚|保誠|宏利'),
    (Reason.OUT_OF_SCOPE_GENERAL,
     r'(write|debug|generate).{0,20}(python|java|sql|code)|写.{0,12}(代码|代碼|爬虫|爬蟲)|'
     r'weather (today|tomorrow)|今日天气|今日天氣|明天天气|明天天氣|炒股推荐|炒股推薦|菜谱|菜譜'),
]


def input_reasons(question):
    text = unicodedata.normalize('NFKC', question).lower()
    reasons = [reason for reason, pattern in RULES if re.search(pattern, text, re.DOTALL)]
    if SECRET.search(question) and Reason.SECRET_OR_PRIVATE_DATA_REQUEST not in reasons:
        reasons.insert(0, Reason.SECRET_OR_PRIVATE_DATA_REQUEST)
    return list(dict.fromkeys(reasons))


# Review flags describe a disputed field, not every fact in the paragraph.
CONFLICT_FIELDS = {
    'p011-b009': r'65|\bage\b|birthday|年龄|年齡|岁|歲|生日|年龄条件|年齡條件',
    'p011-b015': r'65|\bage\b|birthday|年龄|年齡|岁|歲|生日',
    'p017-b001-t1-r6': r'\d|minimum|amount|最低|最少|金额|金額|额度|額度',
}


def conflict_applies(evidence, text):
    if 'SOURCE_CONFLICT' not in evidence['review_flags']:
        return False
    pattern = CONFLICT_FIELDS.get(evidence['evidence_id'])
    if pattern is None:
        return True  # Unknown review issues remain conservative.
    return bool(re.search(pattern + r'|conflict|discrepancy|冲突|衝突|不一致', text, re.IGNORECASE))


def relevant_conflict_ids(draft, evidence):
    return {citation.evidence_id for claim in draft.claims for citation in claim.citations
            if citation.evidence_id in evidence and conflict_applies(evidence[citation.evidence_id], claim.text)}


def output_reason(draft, evidence, paired=None):
    if any(SECRET.search(claim.text) for claim in draft.claims):
        return Reason.SECRET_OR_PRIVATE_DATA_REQUEST
    refused = {Reason.OUT_OF_SCOPE_GENERAL, Reason.UNSUPPORTED_PRODUCT, Reason.PERSONAL_FINANCIAL_ADVICE,
               Reason.MEDICAL_OR_LEGAL_ADVICE, Reason.PROMPT_INJECTION, Reason.SECRET_OR_PRIVATE_DATA_REQUEST}
    if draft.claims and any(r in refused for r in draft.reasons):
        return next(r for r in draft.reasons if r in refused)
    cited = {c.evidence_id for claim in draft.claims for c in claim.citations}
    if any(i not in evidence for i in cited):
        return Reason.INVALID_CITATION
    relevant = relevant_conflict_ids(draft, evidence)
    if draft.action != 'source_conflict' and relevant:
        return Reason.SOURCE_CONFLICT
    if draft.action == 'source_conflict' and paired:
        for eid in relevant:
            if not set(paired.get(eid, [])) <= cited:
                return Reason.SOURCE_CONFLICT
    return None


def guard_result(reasons, action, explanation, attempts=0):
    return {'reasons': list(dict.fromkeys(str(r.value if isinstance(r, Reason) else r) for r in reasons)),
            'action': action.value, 'explanation': explanation, 'repair_attempts': attempts}
