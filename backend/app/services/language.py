"""Local script detection; shared Chinese characters retain the conversation language."""
import re
from functools import lru_cache
from opencc import OpenCC

TO_SIMPLIFIED = OpenCC('t2s')
TO_TRADITIONAL = OpenCC('s2t')


@lru_cache(maxsize=8192)
def script_markers(character):
    # Only count exclusive characters: e.g. trad-only 員 vs simplified-only 员.
    traditional = TO_SIMPLIFIED.convert(character) != character
    simplified = TO_TRADITIONAL.convert(character) != character
    return (int(simplified and not traditional), int(traditional and not simplified))


def detect_language(question, fallback='zh-Hans', chinese_fallback=None):
    if fallback not in ('zh-Hans', 'zh-Hant', 'en'):
        fallback = 'zh-Hans'
    text = re.sub(r'https?://\S+|`[^`]*`', '', question)
    chinese = re.findall(r'[\u3400-\u9fff]', text)
    if chinese:
        counts = [script_markers(character) for character in chinese]
        simplified = sum(count[0] for count in counts)
        traditional = sum(count[1] for count in counts)
        if simplified != traditional:
            return 'zh-Hans' if simplified > traditional else 'zh-Hant'
        preferred = chinese_fallback or fallback
        return preferred if preferred in ('zh-Hans', 'zh-Hant') else 'zh-Hans'
    if re.search(r'[A-Za-z]', text):
        return 'en'
    return fallback
