"""Present generated prose consistently; original citation quotations are never changed."""
import re

from app.services.language import TO_SIMPLIFIED, TO_TRADITIONAL

EVIDENCE_ID = r'p\d{3}-[bd]\d{3}(?:-t\d+-r\d+)?'
INLINE_IDS = re.compile(r'[【\[]\s*' + EVIDENCE_ID + r'(?:[\s,;、]+' + EVIDENCE_ID + r')*\s*[】\]]')
WEB_CITATION = re.compile(r'[^]*')


def answer_text(text, language=None, partial=False):
    """Remove generated citation markup, not ordinary brackets, amounts or source text."""
    text = WEB_CITATION.sub('', text)
    text = INLINE_IDS.sub('', text)
    if partial:
        # Do not flash an unfinished internal marker while waiting for the next provider delta.
        opener = text.find('')
        if opener >= 0:
            text = text[:opener]
        bracket = re.search(r'[【\[]([^】\]]*)$', text)
        if bracket and (not bracket[1] or re.match(r'p(?:\d|$)', bracket[1])):
            text = text[:bracket.start()]
    if language == 'zh-Hans':
        text = TO_SIMPLIFIED.convert(text)
    elif language == 'zh-Hant':
        text = TO_TRADITIONAL.convert(text)
    return text.strip()
