"""Check the full extracted-text review without API calls."""
import json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from evaluation.full_alignment import load_full_review,render_full_review
if __name__=='__main__':
    review,result=load_full_review()
    (ROOT/'data/reviewed/full_alignment.md').write_text(render_full_review(review,result),encoding='utf-8')
    print(json.dumps(result,ensure_ascii=False,indent=2))
