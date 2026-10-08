"""Validate reviewed sources, build/reuse the index, then serve the application."""
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def prepare_index():
    key = os.getenv('OPENAI_API_KEY', '').strip()
    if not key or key == 'your_openai_api_key_here':
        raise RuntimeError('Set OPENAI_API_KEY in .env before starting the application.')
    from evaluation.full_alignment import load_full_review
    from backend.app.rag.index import VectorIndex

    load_full_review()
    index = VectorIndex()
    if index.ready():
        print('Reviewed sources verified. Reusing the existing index; no build API usage.', flush=True)
    else:
        print(f'Building/resuming {len(index.chunks)} reviewed chunks with {index.embedder.model}. '
              'This sends brochure text to the embedding API and incurs usage. Please wait.', flush=True)
    result = index.build()
    print('Index ready: ' + json.dumps(result), flush=True)
    return result


def main():
    try:
        prepare_index()
    except (RuntimeError, ValueError) as exc:
        print(f'Startup stopped: {exc}', file=sys.stderr, flush=True)
        return 1
    except Exception as exc:
        # Do not log provider responses, environment values or other sensitive diagnostics.
        print(f'Startup stopped ({type(exc).__name__}). Check source files and volume permissions.',
              file=sys.stderr, flush=True)
        return 1
    print('Starting InsureTutor on port 8000.', flush=True)
    os.execvp('python', ['python', '-m', 'uvicorn', 'app.main:app', '--app-dir', 'backend',
                         '--host', '0.0.0.0', '--port', '8000', '--no-access-log'])


if __name__ == '__main__':
    raise SystemExit(main())
