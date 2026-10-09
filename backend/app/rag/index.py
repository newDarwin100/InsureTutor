"""Explicit embeddings and versioned local Chroma indexes. No model calls on import."""
import fcntl
import hashlib
import json
import math
import os
import time
import threading
from collections import OrderedDict
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

import chromadb
from chromadb.config import Settings

ROOT = Path(__file__).resolve().parents[3]
QUERY_VECTORS = OrderedDict()
QUERY_LOCK = threading.Lock()


def digest(value):
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True).encode()).hexdigest()


def write_json(path, value):
    temporary = path.with_suffix('.tmp')
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    temporary.replace(path)


class Embeddings:
    def __init__(self, model=None, dimensions=None):
        self.model = model or os.getenv('EMBEDDING_MODEL', 'text-embedding-3-large')
        defaults = {'text-embedding-3-large': 3072, 'text-embedding-3-small': 1536}
        self.dimensions = dimensions or int(os.getenv('EMBEDDING_DIMENSIONS', '') or defaults.get(self.model, 0))
        if self.dimensions <= 0:
            raise ValueError('Specify a positive embedding dimension for this model')

    def embed(self, texts):
        key = os.getenv('OPENAI_API_KEY', '').strip()
        if not key or key == 'your_openai_api_key_here':
            raise RuntimeError('OPENAI_API_KEY is not configured')
        body = {'model': self.model, 'dimensions': self.dimensions, 'input': texts, 'encoding_format': 'float'}
        request = Request('https://api.openai.com/v1/embeddings', data=json.dumps(body).encode(),
                          headers={'Authorization': f'Bearer {key}', 'Content-Type': 'application/json'})
        try:
            with urlopen(request, timeout=60) as response:
                result = json.load(response)
        except HTTPError as exc:
            raise RuntimeError(f'Embedding API returned HTTP {exc.code}; retry explicitly') from None
        except (URLError, TimeoutError):
            raise RuntimeError('Embedding API connection failed; retry explicitly') from None
        data = sorted(result['data'], key=lambda row: row['index'])
        if [row['index'] for row in data] != list(range(len(texts))):
            raise ValueError('Embedding API returned unexpected input indexes')
        vectors = [row['embedding'] for row in data]
        validate_vectors(vectors, len(texts), self.dimensions)
        return vectors, result['usage']['prompt_tokens']


def validate_vectors(vectors, count, dimensions):
    if len(vectors) != count or any(len(v) != dimensions or not all(math.isfinite(x) for x in v)
                                    or not any(v) for v in vectors):
        raise ValueError('Invalid embedding count, dimensions or values')


class VectorIndex:
    def __init__(self, embedder=None, directory=None, knowledge=None, limit=None, chunk_ids=None):
        self.embedder = embedder or Embeddings()
        self.directory = Path(directory or ROOT / 'data/chroma')
        self.knowledge = Path(knowledge or ROOT / 'data/processed/knowledge')
        self.chunks = json.loads((self.knowledge / 'chunks.json').read_text(encoding='utf-8'))
        if chunk_ids is not None:
            if limit is not None or len(chunk_ids) != len(set(chunk_ids)):
                raise ValueError('Select unique chunk IDs or a limit, not both')
            all_chunks = {c['chunk_id']: c for c in self.chunks}
            if any(cid not in all_chunks for cid in chunk_ids):
                raise ValueError('Unknown selected chunk ID')
            self.chunks = [all_chunks[cid] for cid in chunk_ids]
        if limit is not None:
            if limit <= 0:
                raise ValueError('Limit must be positive')
            self.chunks = self.chunks[:limit]
        if not self.chunks or len({c['chunk_id'] for c in self.chunks}) != len(self.chunks):
            raise ValueError('Chunks must have unique IDs and not be empty')
        self.by_id = {c['chunk_id']: c for c in self.chunks}
        self.spec = {'schema_version': 1, 'model': self.embedder.model, 'dimensions': self.embedder.dimensions,
                     'distance': 'cosine', 'chunks_sha256': digest(self.chunks),
                     'knowledge_hashes': {name: hashlib.sha256((self.knowledge / name).read_bytes()).hexdigest()
                                          for name in ['manifest.json', 'evidence.json', 'parents.json']},
                     'pdf_sha256': hashlib.sha256((ROOT / 'docs/FLEXI-ULife Prime Saver.pdf').read_bytes()).hexdigest(),
                     'chunk_count': len(self.chunks)}
        self.version = digest(self.spec)
        self.collection_name = 'insurance-' + self.version[:32]
        self.directory.mkdir(parents=True, exist_ok=True)
        self.client = chromadb.PersistentClient(path=str(self.directory), settings=Settings(anonymized_telemetry=False))
        self.marker = self.directory / 'active.json'

    def collection(self):
        return self.client.get_collection(self.collection_name, embedding_function=None)

    def ready(self):
        if not self.marker.is_file():
            return False
        record = json.loads(self.marker.read_text())
        if record.get('version') != self.version:
            return False
        try:
            return self.collection().count() == len(self.chunks)
        except chromadb.errors.NotFoundError:
            return False

    def build(self, batch_size=24):
        if not 1 <= batch_size <= 128:
            raise ValueError('Batch size must be between 1 and 128')
        with (self.directory / 'build.lock').open('a') as lock:
            try:
                fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError:
                raise RuntimeError('Another index build is running') from None
            if self.ready():
                return {'version': self.version, 'reused': True, 'embedded_chunks': 0, 'input_tokens': 0}
            collection = self.client.get_or_create_collection(self.collection_name, embedding_function=None,
                                    configuration={'hnsw': {'space': 'cosine'}})
            stored = set(collection.get(include=[])['ids'])
            missing = [c for c in self.chunks if c['chunk_id'] not in stored]
            tokens = 0
            for offset in range(0, len(missing), batch_size):
                batch = missing[offset:offset + batch_size]
                vectors, used = self.embedder.embed([c['retrieval_text'] for c in batch])
                validate_vectors(vectors, len(batch), self.embedder.dimensions)
                collection.upsert(ids=[c['chunk_id'] for c in batch], embeddings=vectors,
                                  documents=[c['retrieval_text'] for c in batch],
                                  metadatas=[{'parent_id': c['parent_id'], 'evidence_ids': json.dumps(c['evidence_ids']),
                                              'pdf_pages': json.dumps(c['pdf_pages'])} for c in batch])
                tokens += used
            if collection.count() != len(self.chunks):
                raise RuntimeError('Incomplete index; active index was not switched')
            write_json(self.marker, {'version': self.version, 'collection': self.collection_name, 'spec': self.spec})
            return {'version': self.version, 'reused': False, 'embedded_chunks': len(missing), 'input_tokens': tokens}

    def search(self, question, top_k=5):
        if not question.strip() or not 1 <= top_k <= 20:
            raise ValueError('Question must be nonblank and top_k between 1 and 20')
        if not self.ready():
            raise RuntimeError('Index missing or outdated; run scripts/build_index.py')
        start = time.perf_counter()
        # Hash keys only; ephemeral, bounded cache. Never share vectors across index/model/key changes.
        cache_key = (self.version, digest(question.strip()), digest(os.getenv('OPENAI_API_KEY', '')))
        cached = False
        with QUERY_LOCK:
            record = QUERY_VECTORS.get(cache_key) if isinstance(self.embedder, Embeddings) else None
            if record and time.monotonic()-record[0] < 600:
                vectors, tokens, cached = record[1], 0, True
                QUERY_VECTORS.move_to_end(cache_key)
            elif record:
                del QUERY_VECTORS[cache_key]
        if not cached:
            vectors, tokens = self.embedder.embed([question.strip()])
        validate_vectors(vectors, 1, self.embedder.dimensions)
        if not cached and isinstance(self.embedder, Embeddings):
            with QUERY_LOCK:
                QUERY_VECTORS[cache_key] = (time.monotonic(), vectors)
                while len(QUERY_VECTORS) > 128:
                    QUERY_VECTORS.popitem(last=False)
        embedded = time.perf_counter()
        result = self.collection().query(query_embeddings=vectors, n_results=min(top_k, len(self.chunks)),
                                         include=['distances'])
        end = time.perf_counter()
        return {'index_version': self.version, 'ranked_chunk_ids': result['ids'][0],
                'query_cached': cached,
                'distances': result['distances'][0], 'input_tokens': tokens,
                'query_embedding_ms': round((embedded-start)*1000, 2),
                'vector_search_ms': round((end-embedded)*1000, 2),
                'retrieval_ms': round((end-start)*1000, 2)}
