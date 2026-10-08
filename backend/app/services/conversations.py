"""Bounded, process-local conversations; tokens are bearer credentials, not URL IDs."""
import secrets
import threading
import time
from contextlib import contextmanager
from dataclasses import dataclass, field


class ConversationError(Exception):
    def __init__(self, status, code, message):
        self.status, self.code, self.message = status, code, message


@dataclass
class Conversation:
    touched: float
    turns: list = field(default_factory=list)
    lock: object = field(default_factory=threading.Lock)


class Conversations:
    def __init__(self, ttl=1800, capacity=100, max_turns=8, max_chars=24000, clock=time.monotonic):
        self.ttl, self.capacity, self.max_turns, self.max_chars, self.clock = ttl, capacity, max_turns, max_chars, clock
        self.entries = {}
        self.lock = threading.Lock()

    def _purge(self):
        for token, entry in list(self.entries.items()):
            if self.clock()-entry.touched >= self.ttl and not entry.lock.locked():
                del self.entries[token]

    def create(self):
        with self.lock:
            self._purge()
            if len(self.entries) >= self.capacity:
                raise ConversationError(429, 'CONVERSATION_LIMIT', '会话数量达到上限，请稍后再试。')
            token = secrets.token_urlsafe(32)
            self.entries[token] = Conversation(self.clock())
            return token

    @contextmanager
    def use(self, token):
        with self.lock:
            self._purge()
            entry = self.entries.get(token)
            if entry is None:
                raise ConversationError(410, 'CONVERSATION_EXPIRED', '会话已失效，请清空后重新开始。')
            if not entry.lock.acquire(blocking=False):
                raise ConversationError(409, 'CONVERSATION_BUSY', '这个会话正在回答，请等待完成。')
            entry.touched = self.clock()
        try:
            yield entry
        finally:
            with self.lock:
                entry.touched = self.clock()
                entry.lock.release()

    def append(self, entry, question, resolved, reply):
        if reply['action'] not in ['answered', 'source_conflict', 'clarify']:
            return
        assistant = ('\n'.join(c['text'] for c in reply['claims']) or reply.get('message', ''))[:3000]
        entry.turns.append({'question': question[:2000], 'resolved_question': resolved[:2000], 'assistant': assistant})
        while len(entry.turns) > self.max_turns or sum(len(str(t)) for t in entry.turns) > self.max_chars:
            entry.turns.pop(0)

    def delete(self, token):
        with self.lock:
            entry = self.entries.get(token)
            if entry is None:
                return  # Clearing an already expired conversation is safe and idempotent.
            if entry.lock.locked():
                raise ConversationError(409, 'CONVERSATION_BUSY', '请等待当前回答完成后清空。')
            del self.entries[token]
