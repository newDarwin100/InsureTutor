"""SQLite transcripts and bounded model context, isolated by browser credentials."""
import hashlib
import json
import secrets
import sqlite3
import time
from pathlib import Path
from contextlib import contextmanager

from app.services.conversations import Conversations, Conversation, ConversationError


class ChatHistory(Conversations):
    def __init__(self, path, **kwargs):
        super().__init__(**kwargs)
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        with self.db() as db:
            db.executescript('''
                PRAGMA journal_mode=WAL;
                CREATE TABLE IF NOT EXISTS workspaces (owner TEXT PRIMARY KEY);
                CREATE TABLE IF NOT EXISTS chats (
                    token TEXT PRIMARY KEY, owner TEXT, title TEXT NOT NULL DEFAULT '',
                    created REAL NOT NULL, updated REAL NOT NULL,
                    language TEXT NOT NULL DEFAULT 'zh-Hans', turns TEXT NOT NULL DEFAULT '[]'
                );
                CREATE INDEX IF NOT EXISTS chats_owner ON chats(owner, updated DESC);
                CREATE TABLE IF NOT EXISTS messages (
                    id INTEGER PRIMARY KEY, chat TEXT NOT NULL REFERENCES chats(token) ON DELETE CASCADE,
                    role TEXT NOT NULL, text TEXT NOT NULL DEFAULT '', reply TEXT,
                    language TEXT NOT NULL, status TEXT NOT NULL, error_code TEXT, created REAL NOT NULL
                );
                CREATE INDEX IF NOT EXISTS messages_chat ON messages(chat, id);
            ''')
        self.path.chmod(0o600)

    @contextmanager
    def db(self):
        db = sqlite3.connect(self.path, timeout=5)
        db.row_factory = sqlite3.Row
        db.execute('PRAGMA foreign_keys=ON')
        try:
            with db:
                yield db
        finally:
            db.close()

    @staticmethod
    def owner(token):
        return hashlib.sha256(token.encode()).hexdigest()

    def create_workspace(self):
        token = secrets.token_urlsafe(32)
        with self.db() as db:
            db.execute('INSERT INTO workspaces VALUES (?)', (self.owner(token),))
        return token

    def check_owner(self, db, token):
        if not token or not db.execute('SELECT 1 FROM workspaces WHERE owner=?', (self.owner(token),)).fetchone():
            raise ConversationError(401, 'WORKSPACE_EXPIRED', '浏览器会话凭证已失效。')
        return self.owner(token)

    def create(self, owner_token=None):
        token, now = secrets.token_urlsafe(32), time.time()
        with self.db() as db:
            owner = self.check_owner(db, owner_token) if owner_token is not None else None
            db.execute('INSERT INTO chats(token,owner,created,updated) VALUES (?,?,?,?)', (token, owner, now, now))
        return token

    def list(self, owner_token):
        with self.db() as db:
            owner = self.check_owner(db, owner_token)
            return [dict(row) for row in db.execute(
                'SELECT token,title,created,updated,language FROM chats WHERE owner=? ORDER BY updated DESC', (owner,))]

    @contextmanager
    def use(self, token):
        with self.lock:
            self._purge()  # Evict cached context only; never delete the saved transcript.
            with self.db() as db:
                row = db.execute('SELECT * FROM chats WHERE token=?', (token,)).fetchone()
                chinese = db.execute("SELECT language FROM messages WHERE chat=? AND role='user' AND language IN ('zh-Hans','zh-Hant') ORDER BY id DESC LIMIT 1", (token,)).fetchone()
            if row is None:
                raise ConversationError(410, 'CONVERSATION_EXPIRED', '会话不存在或已删除。')
            entry = self.entries.get(token)
            if entry is None:
                if len(self.entries) >= self.capacity:
                    idle = [key for key, item in self.entries.items() if not item.lock.locked()]
                    if not idle:
                        raise ConversationError(429, 'CONVERSATION_LIMIT', '活动会话达到上限。')
                    del self.entries[min(idle, key=lambda key: self.entries[key].touched)]
                entry = self.entries[token] = Conversation(self.clock())
            if not entry.lock.acquire(blocking=False):
                raise ConversationError(409, 'CONVERSATION_BUSY', '这个会话正在回答，请等待完成。')
            entry.turns = json.loads(row['turns'])
            entry.language, entry.token, entry.pending = row['language'], token, None
            entry.chinese_language = chinese['language'] if chinese else 'zh-Hans'
            entry.touched = self.clock()
        try:
            yield entry
        finally:
            with self.lock:
                entry.touched = self.clock()
                entry.lock.release()

    def begin(self, entry, question, language):
        now = time.time()
        with self.db() as db:
            # A previous process may have stopped while a model request was pending.
            db.execute("UPDATE messages SET status='error', error_code='REQUEST_INTERRUPTED' WHERE chat=? AND status='pending'", (entry.token,))
            db.execute('INSERT INTO messages(chat,role,text,language,status,created) VALUES (?,?,?,?,?,?)',
                       (entry.token, 'user', question, language, 'complete', now))
            entry.pending = db.execute('INSERT INTO messages(chat,role,language,status,created) VALUES (?,?,?,?,?)',
                                       (entry.token, 'assistant', language, 'pending', now)).lastrowid
            title = ' '.join(question.split())[:42]
            db.execute("UPDATE chats SET title=CASE WHEN title='' THEN ? ELSE title END, language=?,updated=? WHERE token=?",
                       (title, language, now, entry.token))
        entry.language = language

    def append(self, entry, question, resolved, reply):
        super().append(entry, question, resolved, reply)
        with self.db() as db:
            db.execute("UPDATE messages SET text=?,reply=?,status='complete' WHERE id=? AND chat=?",
                       (reply.get('message', ''), json.dumps(reply, ensure_ascii=False), entry.pending, entry.token))
            db.execute('UPDATE chats SET turns=?, updated=? WHERE token=?',
                       (json.dumps(entry.turns, ensure_ascii=False), time.time(), entry.token))

    def fail(self, entry, code):
        with self.db() as db:
            db.execute("UPDATE messages SET status='error',error_code=? WHERE id=? AND chat=?", (code, entry.pending, entry.token))

    def read(self, token):
        with self.db() as db:
            chat = db.execute('SELECT token,title,created,updated,language FROM chats WHERE token=?', (token,)).fetchone()
            if chat is None:
                raise ConversationError(410, 'CONVERSATION_EXPIRED', '会话不存在或已删除。')
            rows = [dict(row) for row in db.execute('SELECT role,text,reply,language,status,error_code,created FROM messages WHERE chat=? ORDER BY id', (token,))]
        with self.lock:
            active = token in self.entries and self.entries[token].lock.locked()
        for row in rows:
            if row['reply']:
                row['reply'] = json.loads(row['reply'])
            if row['status'] == 'pending' and not active:
                row.update(status='error', error_code='REQUEST_INTERRUPTED')
        return {**dict(chat), 'messages': rows}

    def rename(self, token, title):
        with self.db() as db:
            if not db.execute('UPDATE chats SET title=? WHERE token=?', (title, token)).rowcount:
                raise ConversationError(410, 'CONVERSATION_EXPIRED', '会话不存在或已删除。')

    def delete(self, token):
        with self.lock:
            entry = self.entries.get(token)
            if entry and entry.lock.locked():
                raise ConversationError(409, 'CONVERSATION_BUSY', '请等待当前回答完成后删除。')
            with self.db() as db:
                db.execute('DELETE FROM chats WHERE token=?', (token,))
            self.entries.pop(token, None)
