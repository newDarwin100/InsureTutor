"""Startup checks use real Chroma persistence and deterministic, free embeddings."""
import contextlib
import io
import os
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from backend.app.rag.index import VectorIndex
from scripts import container_entrypoint as startup
from backend.tests.test_vector_index import FakeEmbeddings

ROOT = Path(__file__).resolve().parents[2]


class StartupTests(unittest.TestCase):
    def test_first_start_builds_and_restart_reuses_without_embedding(self):
        with tempfile.TemporaryDirectory() as directory:
            embedder = FakeEmbeddings()
            def index_factory():
                return VectorIndex(embedder, directory, limit=3)
            with patch.dict(os.environ, {'OPENAI_API_KEY': 'test-placeholder'}), \
                 patch('backend.app.rag.index.VectorIndex', side_effect=index_factory), \
                 contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(startup.prepare_index()['embedded_chunks'], 3)
                self.assertTrue(startup.prepare_index()['reused'])
                self.assertEqual(embedder.calls, 1)

    def test_missing_key_and_stale_review_stop_before_index_build(self):
        with patch.dict(os.environ, {'OPENAI_API_KEY': 'your_openai_api_key_here'}), \
             patch('backend.app.rag.index.VectorIndex') as factory:
            with self.assertRaisesRegex(RuntimeError, 'Set OPENAI_API_KEY'):
                startup.prepare_index()
            factory.assert_not_called()
        with patch.dict(os.environ, {'OPENAI_API_KEY': 'test-placeholder'}), \
             patch('evaluation.full_alignment.load_full_review', side_effect=ValueError('Full review is stale')), \
             patch('backend.app.rag.index.VectorIndex') as factory:
            with self.assertRaisesRegex(ValueError, 'stale'):
                startup.prepare_index()
            factory.assert_not_called()

    def test_failed_bootstrap_does_not_serve_or_log_unknown_diagnostics(self):
        output = io.StringIO()
        with patch.object(startup, 'prepare_index', side_effect=OSError('sensitive diagnostic')), \
             patch.object(startup.os, 'execvp') as serve, contextlib.redirect_stderr(output):
            self.assertEqual(startup.main(), 1)
            serve.assert_not_called()
        self.assertIn('OSError', output.getvalue())
        self.assertNotIn('sensitive diagnostic', output.getvalue())

    def test_successful_bootstrap_replaces_process_for_shutdown_signals(self):
        with patch.object(startup, 'prepare_index'), patch.object(startup.os, 'execvp') as serve, \
             contextlib.redirect_stdout(io.StringIO()):
            startup.main()
        command, arguments = serve.call_args.args
        self.assertEqual(command, 'python')
        self.assertIn('app.main:app', arguments)
        self.assertNotIn('--workers', arguments)  # Conversation storage is single-process.


class LauncherTests(unittest.TestCase):
    def run_launcher(self, state):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'scripts').mkdir()
            (root / 'scripts/start.sh').write_bytes((ROOT / 'scripts/start.sh').read_bytes())
            (root / '.env').write_text('OPENAI_API_KEY=test-placeholder\n')
            (root / 'bin').mkdir()
            docker = root / 'bin/docker'
            docker.write_text('''#!/bin/bash
printf '%s\\n' "$*" >> "$TEST_DOCKER_CALLS"
case "$1 $2" in
  "compose version"|"info "|"compose up") exit 0 ;;
  "compose ps") echo test-container ;;
  "compose logs") echo 'Startup stopped: configured test failure' ;;
  "inspect --format")
    if [[ "$3" == '{{.State.Status}}' ]]; then
      echo "$TEST_CONTAINER_STATE"
    else
      echo healthy
    fi ;;
  *) exit 2 ;;
esac
''')
            docker.chmod(0o755)
            log = root / 'calls.txt'
            environment = dict(os.environ, PATH=str(root / 'bin') + os.pathsep + os.environ['PATH'],
                               TEST_DOCKER_CALLS=str(log), TEST_CONTAINER_STATE=state)
            result = subprocess.run(['bash', str(root / 'scripts/start.sh')], env=environment,
                                    capture_output=True, text=True, timeout=5)
            return result, log.read_text()

    def test_exited_container_prints_logs_and_does_not_retry(self):
        result, calls = self.run_launcher('exited')
        self.assertEqual(result.returncode, 1)
        self.assertIn('configured test failure', result.stderr)
        self.assertEqual(calls.count('compose up --build -d'), 1)
        self.assertIn('compose ps --all -q app', calls)

    def test_ready_container_reports_success(self):
        result, calls = self.run_launcher('running')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('http://127.0.0.1:8000', result.stdout)
        self.assertIn('Health.Status', calls)
        self.assertNotIn('compose logs', calls)
