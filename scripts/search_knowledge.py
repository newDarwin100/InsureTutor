"""Retrieve real chunks with page references; this does not generate an answer."""
import argparse
import json
import sys
from pathlib import Path
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from backend.app.rag.index import VectorIndex

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('question')
    args = parser.parse_args()
    load_dotenv(ROOT / '.env', override=False)
    index = VectorIndex()
    result = index.search(args.question)
    result['chunks'] = [index.by_id[cid] for cid in result['ranked_chunk_ids']]
    print(json.dumps(result, ensure_ascii=False, indent=2))
