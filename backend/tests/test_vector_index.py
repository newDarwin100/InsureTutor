"""Exercise real Chroma persistence with free deterministic test embeddings."""
import json
import tempfile
import unittest
from pathlib import Path

from backend.app.rag.index import ROOT, VectorIndex


class FakeEmbeddings:
    model = 'test-only'
    dimensions = 3
    def __init__(self, fail_at=None):
        self.calls = 0
        self.fail_at = fail_at
    def embed(self, texts):
        self.calls += 1
        if self.calls == self.fail_at:
            raise RuntimeError('Simulated provider outage')
        return [[1.0, (sum(map(ord, text)) % 97)/97, 0.25] for text in texts], len(texts)


class IndexTests(unittest.TestCase):
    def test_persistence_and_no_embedding_on_reuse(self):
        with tempfile.TemporaryDirectory() as directory:
            embedder = FakeEmbeddings()
            first = VectorIndex(embedder, directory, limit=3)
            self.assertFalse(first.ready())
            self.assertEqual(first.build()['embedded_chunks'], 3)
            second = VectorIndex(embedder, directory, limit=3)
            self.assertTrue(second.ready())
            self.assertTrue(second.build()['reused'])
            self.assertEqual(embedder.calls, 1)
            result = second.search('guaranteed interest', 2)
            self.assertEqual(len(result['ranked_chunk_ids']), 2)
            self.assertTrue(set(result['ranked_chunk_ids']) <= set(first.by_id))

    def test_failed_new_version_keeps_old_index_and_resumes(self):
        with tempfile.TemporaryDirectory() as directory:
            old = VectorIndex(FakeEmbeddings(), directory, limit=2)
            old.build()
            marker = Path(directory, 'active.json').read_bytes()
            next_index = VectorIndex(FakeEmbeddings(fail_at=2), directory, limit=4)
            self.assertFalse(next_index.ready())
            with self.assertRaises(RuntimeError):
                next_index.build(batch_size=2)
            self.assertEqual(Path(directory, 'active.json').read_bytes(), marker)
            self.assertTrue(old.ready())
            resumed = VectorIndex(FakeEmbeddings(), directory, limit=4)
            self.assertEqual(resumed.build()['embedded_chunks'], 2)
            self.assertTrue(resumed.ready())

    def test_versions_track_model_dimension_and_source(self):
        with tempfile.TemporaryDirectory() as directory, tempfile.TemporaryDirectory() as knowledge:
            for name in ['chunks.json', 'manifest.json', 'evidence.json', 'parents.json']:
                Path(knowledge, name).write_bytes((ROOT / 'data/processed/knowledge' / name).read_bytes())
            original = VectorIndex(FakeEmbeddings(), directory, knowledge, limit=2)
            changed = FakeEmbeddings()
            changed.dimensions = 4
            self.assertNotEqual(original.version, VectorIndex(changed, directory, knowledge, limit=2).version)
            changed.model = 'another-model'
            self.assertNotEqual(original.version, VectorIndex(changed, directory, knowledge, limit=2).version)
            path = Path(knowledge, 'evidence.json')
            content = json.loads(path.read_text())
            content[0]['text'] += ' updated'
            path.write_text(json.dumps(content))
            self.assertNotEqual(original.version, VectorIndex(FakeEmbeddings(), directory, knowledge, limit=2).version)

    def test_invalid_embedding_does_not_publish_index(self):
        class WrongDimensions(FakeEmbeddings):
            def embed(self, texts):
                return [[1.0] for _ in texts], 0
        with tempfile.TemporaryDirectory() as directory:
            index = VectorIndex(WrongDimensions(), directory, limit=2)
            with self.assertRaises(ValueError):
                index.build()
            self.assertFalse(index.ready())
            self.assertFalse(Path(directory, 'active.json').exists())

    def test_selected_sample_never_embeds_the_rest_of_the_corpus(self):
        chunks = json.loads((ROOT/'data/processed/knowledge/chunks.json').read_text())
        ids = [chunks[1]['chunk_id'], chunks[4]['chunk_id']]
        with tempfile.TemporaryDirectory() as directory:
            index = VectorIndex(FakeEmbeddings(), directory, chunk_ids=ids)
            self.assertEqual(index.build()['embedded_chunks'], 2)
            self.assertEqual(index.collection().count(), 2)
            self.assertEqual(set(index.collection().get(include=[])['ids']), set(ids))
