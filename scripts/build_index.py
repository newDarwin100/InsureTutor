"""Build or reuse an explicit, versioned embedding index."""
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
    parser.add_argument('--index-dir', type=Path)
    parser.add_argument('--full', action='store_true', help='Explicitly authorize building all document chunks')
    parser.add_argument('--limit', type=int, help='Smoke test only; requires a separate --index-dir')
    args = parser.parse_args()
    if not args.full and args.limit is None:
        parser.error('Choose --full deliberately, or run scripts/run_retrieval_pilot.py for the reviewed sample')
    if args.full and args.limit is not None:
        parser.error('--full and --limit cannot be combined')
    if args.limit is not None and args.index_dir is None:
        parser.error('--limit requires --index-dir so the full index is not replaced')
    load_dotenv(ROOT / '.env', override=False)
    try:
        print(json.dumps(VectorIndex(directory=args.index_dir, limit=args.limit).build(), indent=2))
    except (RuntimeError, ValueError) as exc:
        parser.exit(1, f'{exc}\n')
