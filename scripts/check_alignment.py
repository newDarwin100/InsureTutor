"""Validate pilot review references and regenerate its readable report, without API calls."""
import json
import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from evaluation.alignment import load_and_validate, render_review

if __name__ == '__main__':
    review, evidence, result = load_and_validate()
    (ROOT/'data/reviewed/pilot_alignment.md').write_text(render_review(review, evidence, result), encoding='utf-8')
    print(json.dumps(result, ensure_ascii=False, indent=2))
