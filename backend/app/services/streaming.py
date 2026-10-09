"""Bounded SSE delivery from the synchronous RAG worker; cancellation keeps drafts out of history."""
import asyncio
import json
import queue
import threading


class StreamCancelled(RuntimeError):
    pass


WORKERS = threading.BoundedSemaphore(8)


async def event_stream(run):
    if not WORKERS.acquire(blocking=False):
        yield 'event: error\ndata: {"code":"STREAM_BUSY"}\n\n'
        return
    mailbox = queue.Queue(maxsize=64)
    stopped = threading.Event()

    def emit(event, data):
        while not stopped.is_set():
            try:
                mailbox.put((event, data), timeout=.2)
                return
            except queue.Full:
                continue
        raise StreamCancelled('Client disconnected')

    def worker():
        try:
            run(emit)
        except StreamCancelled:
            pass
        except Exception:
            # No exception text, credentials or draft content in transport errors.
            try:
                emit('error', {'code': 'REQUEST_FAILED'})
            except StreamCancelled:
                pass
        finally:
            WORKERS.release()

    threading.Thread(target=worker, daemon=True, name='chat-stream').start()
    try:
        while True:
            try:
                event, data = await asyncio.to_thread(mailbox.get, True, 10)
            except queue.Empty:
                yield ': heartbeat\n\n'
                continue
            yield f'event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n'
            if event in ('done', 'error'):
                return
    finally:
        stopped.set()
