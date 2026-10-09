"""Real SQLite and ASGI requests, with no paid model dependencies."""
import asyncio
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'backend'))
from app.services.chat_history import ChatHistory
from app.services.conversations import ConversationError
from app.services.language import detect_language
from app.services.responses import ModelError
from test_api import call


def reply(language='zh-Hans', action='answered'):
    return {'action': action, 'language': language, 'message': '',
            'claims': [{'text': 'Checked answer', 'citation_numbers': [1]}],
            'citations': [{'number': 1, 'evidence_id': 'e1', 'pdf_page': 12, 'url': '/api/documents/flexi-ulife-prime-saver#page=12'}],
            'metrics': {'total_ms': 123}}


class HistoryTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.path = Path(self.directory.name) / 'history.sqlite3'
        self.store = ChatHistory(self.path, max_turns=2)
        self.owner = self.store.create_workspace()
        self.token = self.store.create(self.owner)

    def add(self, question, result=None, language='zh-Hans'):
        with self.store.use(self.token) as entry:
            self.store.begin(entry, question, language)
            self.store.append(entry, question, question, result or reply(language))

    def test_restart_and_idle_eviction_keep_full_transcript_but_bound_model_context(self):
        for question in ['First question', 'Second question', 'Third question']:
            self.add(question)
        self.add('Blocked question', reply(action='unsafe_request'))
        with self.store.use(self.token) as entry:
            self.store.begin(entry, 'Failed question', 'en')
            self.store.fail(entry, 'MODEL_UNAVAILABLE')
        restarted = ChatHistory(self.path, ttl=0, max_turns=2)
        self.assertEqual(len(restarted.read(self.token)['messages']), 10)
        self.assertEqual(restarted.read(self.token)['messages'][-1]['error_code'], 'MODEL_UNAVAILABLE')
        self.assertEqual(restarted.read(self.token)['messages'][1]['reply']['citations'][0]['pdf_page'], 12)
        for _ in range(2):
            with restarted.use(self.token) as entry:
                self.assertEqual([turn['question'] for turn in entry.turns], ['Second question', 'Third question'])
                self.assertEqual(entry.language, 'en')
        self.assertEqual(restarted.list(self.owner)[0]['title'], 'First question')

    def test_owner_isolation_unknown_credentials_and_private_file(self):
        other = self.store.create_workspace()
        token = self.store.create(other)
        self.assertEqual([row['token'] for row in self.store.list(other)], [token])
        self.assertEqual([row['token'] for row in self.store.list(self.owner)], [self.token])
        with self.assertRaises(ConversationError) as caught:
            self.store.list('unknown')
        self.assertEqual(caught.exception.status, 401)
        with self.assertRaises(ConversationError):
            self.store.read('unknown')
        self.assertEqual(self.path.stat().st_mode & 0o777, 0o600)
        self.assertEqual(asyncio.run(call('/data/history/chats.sqlite3'))[0], 404)

    def test_busy_conversation_is_not_deleted_or_overwritten_and_idle_cache_can_evict(self):
        store = ChatHistory(self.path, capacity=1)
        second = store.create(self.owner)
        with store.use(self.token) as entry:
            store.begin(entry, 'Pending question', 'zh-Hant')
            with self.assertRaises(ConversationError) as caught:
                with store.use(self.token):
                    pass
            self.assertEqual(caught.exception.status, 409)
            with self.assertRaises(ConversationError):
                store.delete(self.token)
            with self.assertRaises(ConversationError):
                with store.use(second):
                    pass
            self.assertEqual(store.read(self.token)['messages'][-1]['status'], 'pending')
            store.append(entry, 'Pending question', 'Pending question', reply('zh-Hant'))
        with store.use(second) as entry:
            self.assertEqual(entry.turns, [])
        self.assertEqual(len(store.read(self.token)['messages']), 2)

    def test_rename_delete_cascade_and_interrupted_requests(self):
        with self.store.use(self.token) as entry:
            self.store.begin(entry, 'Original question', 'zh-Hant')
        restarted = ChatHistory(self.path)
        self.assertEqual(restarted.read(self.token)['messages'][-1]['error_code'], 'REQUEST_INTERRUPTED')
        restarted.rename(self.token, 'My named chat')
        with restarted.use(self.token) as entry:
            restarted.begin(entry, 'New question', 'en')
            restarted.append(entry, 'New question', 'New question', reply('en'))
        saved = restarted.read(self.token)
        self.assertEqual(saved['title'], 'My named chat')
        self.assertEqual(len(saved['messages']), 4)
        self.assertEqual(saved['messages'][1]['error_code'], 'REQUEST_INTERRUPTED')
        restarted.delete(self.token)
        restarted.delete(self.token)
        with restarted.db() as db:
            self.assertEqual(db.execute('SELECT count(*) FROM messages').fetchone()[0], 0)
        self.assertEqual(restarted.list(self.owner), [])

    def test_routes_restore_history_and_detect_each_questions_language(self):
        def request(path, method='GET', body=None, owner=None, token=None):
            headers = []
            if owner: headers.append((b'x-workspace-token', owner.encode()))
            if token: headers.append((b'x-conversation-token', token.encode()))
            status, _, raw = asyncio.run(call(path, method, body, headers=headers))
            return status, json.loads(raw)
        with patch('app.main.conversations', self.store):
            self.assertEqual(request('/api/conversations')[0], 422)
            self.assertEqual(request('/api/conversations', owner='unknown')[0], 401)
            self.assertEqual(request('/api/conversations', owner=self.owner)[1]['conversations'][0]['token'], self.token)
            for question, expected in [('定期提款有什麼條件？', 'zh-Hant'), ('可以提款？', 'zh-Hant'),
                                       ('What about annual withdrawals?', 'en'), ('可以提款？', 'zh-Hant'), ('利率是保证的吗？', 'zh-Hans')]:
                with patch('app.main.conversational_answer', return_value=(reply(expected), question)) as model:
                    self.assertEqual(request('/api/chat', 'POST', {'message': question}, token=self.token)[0], 200)
                    self.assertEqual(model.call_args.args[1], expected)
            with patch('app.main.conversational_answer', side_effect=ModelError('provider unavailable')):
                self.assertEqual(request('/api/chat', 'POST', {'message': 'Another question'}, token=self.token)[0], 502)
            saved = request('/api/conversations/current', token=self.token)[1]
            self.assertEqual(len(saved['messages']), 12)
            self.assertEqual(saved['messages'][-1]['error_code'], 'MODEL_UNAVAILABLE')
            self.assertEqual(request('/api/conversations/current', 'PATCH', {'title': '  My title  '}, token=self.token)[0], 200)
            self.assertEqual(request('/api/conversations/current', token=self.token)[1]['title'], 'My title')
            self.assertEqual(request('/api/conversations/current', 'PATCH', {'title': '  '}, token=self.token)[0], 422)
            self.assertEqual(request('/api/conversations/current', 'DELETE', token=self.token)[0], 200)


class LanguageTests(unittest.TestCase):
    def test_script_specific_characters_english_and_shared_character_fallback(self):
        examples = [('4% 的利率是保证的吗？定期提款有什么条件？', 'zh-Hans'),
                    ('4% 的利率是保證的嗎？定期提款有什麼條件？', 'zh-Hant'),
                    ('被裁员后能停缴多久？附加保障也适用吗？', 'zh-Hans'),
                    ('被裁員後能停繳多久？附加保障也適用嗎？', 'zh-Hant'),
                    ('FLEXI-ULife Prime Saver 的保費是多少？', 'zh-Hant'),
                    ('被裁員', 'zh-Hant'), ('被裁员', 'zh-Hans'),
                    ('Is the 4% rate guaranteed?', 'en')]
        for question, expected in examples:
            self.assertEqual(detect_language(question), expected, question)
        self.assertEqual(detect_language('可以提款？', 'zh-Hant'), 'zh-Hant')
        self.assertEqual(detect_language('可以提款？', 'en'), 'zh-Hans')
        self.assertEqual(detect_language('4%?', 'en'), 'en')
        self.assertEqual(detect_language('那每年提款呢？', 'zh-Hant'), 'zh-Hant')


if __name__ == '__main__':
    unittest.main()
