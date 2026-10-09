"""Conversation tutor, readiness and restricted document access."""

import json
import os
import time
from contextlib import nullcontext
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Header
from fastapi.responses import FileResponse, JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from app.services.answer import answer, readiness
from app.services.responses import ModelError
from app.services.conversations import ConversationError
from app.services.chat_history import ChatHistory
from app.services.language import detect_language
from typing import Literal
from app.services.followup import conversational_answer
from app.services.evaluations import dashboard
from app.services.streaming import StreamCancelled, event_stream

ROOT = Path(__file__).resolve().parents[2]
load_dotenv(ROOT / ".env", override=False)
PDF = ROOT / "docs/FLEXI-ULife Prime Saver.pdf"
FRONTEND = ROOT / "frontend/dist"

app = FastAPI(title="InsureTutor", version="0.1.0")
conversations = ChatHistory(os.getenv('CHAT_HISTORY_PATH', str(ROOT / 'data/history/chats.sqlite3')))


@app.exception_handler(ConversationError)
async def conversation_error(request, exc):
    return JSONResponse(status_code=exc.status, content={'detail': {'code': exc.code, 'message': exc.message}})


class DemoRequest(BaseModel):
    message: str = Field(min_length=1, max_length=2000)


@app.get("/health/live")
def live():
    return {"status": "ok", "stage": "conversation"}


@app.get("/api/status")
def status():
    manifest = ROOT / "data/processed/knowledge/manifest.json"
    counts = {}
    if manifest.is_file():
        try:
            counts = json.loads(manifest.read_text(encoding="utf-8")).get("counts", {})
        except (ValueError, OSError):
            pass
    key = os.getenv("OPENAI_API_KEY", "").strip()
    return {"stage": "conversation", "backend_ready": True, "rag_ready": readiness(),
            "model_probed": False, "session_memory": True, "persistent_history": True, "full_guardrails": False, "guardrail_mode": "rules_and_model_checks",
            "document_available": PDF.is_file(), "knowledge_counts": counts,
            "api_key_configured": bool(key and key != "your_openai_api_key_here")}


@app.get("/health/ready")
def ready():
    available = readiness()
    return JSONResponse(status_code=200 if available else 503, content={
        "status": "ready" if available else "not_ready", "mode": "conversation",
        "code": "READY" if available else "RAG_DEPENDENCIES_UNAVAILABLE",
        "model_probed": False})


@app.post("/api/demo")
def demo(body: DemoRequest):
    if not body.message.strip():
        raise HTTPException(status_code=422, detail="Message must not be blank")
    return {"mode": "connection_test", "received": body.message.strip(),
            "message": "前后端连接成功。此消息仅测试连接，尚未调用检索或模型。"}


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=2000)
    language: Literal['auto', 'en', 'zh-Hans', 'zh-Hant'] = 'auto'


@app.post("/api/chat")
def chat(body: ChatRequest, conversation_token: str | None = Header(default=None, alias='X-Conversation-Token')):
    if not body.message.strip():
        raise HTTPException(status_code=422, detail="Message must not be blank")
    try:
        if conversation_token is None:
            language = detect_language(body.message) if body.language == 'auto' else body.language
            return answer(body.message.strip(), language)
        with conversations.use(conversation_token) as entry:
            language = detect_language(body.message, getattr(entry, 'language', 'zh-Hans'), getattr(entry, 'chinese_language', None)) if body.language == 'auto' else body.language
            persistent = isinstance(conversations, ChatHistory)
            if persistent:
                conversations.begin(entry, body.message.strip(), language)
            try:
                reply, resolved = conversational_answer(body.message.strip(), language, entry.turns)
                conversations.append(entry, body.message.strip(), resolved, reply)
            except ModelError:
                if persistent:
                    conversations.fail(entry, 'MODEL_UNAVAILABLE')
                raise
            except (RuntimeError, ValueError, OSError, KeyError):
                if persistent:
                    conversations.fail(entry, 'RAG_UNAVAILABLE')
                raise
            return reply
    except ConversationError as exc:
        raise HTTPException(status_code=exc.status, detail={'code': exc.code, 'message': exc.message}) from None
    except ModelError:
        raise HTTPException(status_code=502, detail={"code": "MODEL_UNAVAILABLE",
            "message": "模型暂时未返回有效结果。请稍后手动重试。"}) from None
    except (RuntimeError, ValueError, OSError, KeyError):
        raise HTTPException(status_code=503, detail={"code": "RAG_UNAVAILABLE",
            "message": "资料或索引未就绪，或问题超出上下文预算。请检查索引或缩小问题范围。"}) from None


@app.get('/api/evaluations')
def evaluations():
    return dashboard()


@app.post('/api/chat/stream')
def chat_stream(body: ChatRequest, conversation_token: str | None = Header(default=None, alias='X-Conversation-Token')):
    if not body.message.strip():
        raise HTTPException(status_code=422, detail='Message must not be blank')
    started = time.perf_counter()

    def run(send):
        first_text = None

        def emit(event, data):
            nonlocal first_text
            if event == 'delta' and data.get('text', '').strip() and first_text is None:
                first_text = round((time.perf_counter()-started)*1000, 2)
            send(event, data)

        try:
            with conversations.use(conversation_token) if conversation_token else nullcontext(None) as entry:
                language = detect_language(body.message, getattr(entry, 'language', 'zh-Hans'), getattr(entry, 'chinese_language', None)) if body.language == 'auto' else body.language
                persistent = entry is not None and isinstance(conversations, ChatHistory)
                if persistent:
                    conversations.begin(entry, body.message.strip(), language)
                committed = False
                try:
                    emit('meta', {'language': language})
                    if entry is None:
                        reply = answer(body.message.strip(), language, emit=emit)
                        resolved = body.message.strip()
                    else:
                        reply, resolved = conversational_answer(body.message.strip(), language, entry.turns, emit=emit)
                    # Check the channel before committing a reply after a slow audit.
                    emit('status', {'stage': 'complete'})
                    reply['metrics']['ttft_ms'] = first_text
                    reply['metrics']['total_ms'] = round((time.perf_counter()-started)*1000, 2)
                    if entry is not None:
                        conversations.append(entry, body.message.strip(), resolved, reply)
                    committed = True
                    emit('done', reply)
                except Exception as exc:
                    if persistent and not committed:
                        conversations.fail(entry, 'REQUEST_INTERRUPTED' if isinstance(exc, StreamCancelled) else
                            'MODEL_UNAVAILABLE' if isinstance(exc, ModelError) else 'RAG_UNAVAILABLE')
                    raise
        except StreamCancelled:
            raise
        except ConversationError as exc:
            send('error', {'code': exc.code})
        except ModelError:
            send('error', {'code': 'MODEL_UNAVAILABLE'})
        except (RuntimeError, ValueError, OSError, KeyError):
            send('error', {'code': 'RAG_UNAVAILABLE'})

    return StreamingResponse(event_stream(run), media_type='text/event-stream', headers={
        'Cache-Control': 'no-cache, no-transform', 'X-Accel-Buffering': 'no'})


@app.post('/api/workspaces', status_code=201)
def create_workspace():
    return {'token': conversations.create_workspace()}


@app.get('/api/conversations')
def list_conversations(workspace_token: str = Header(alias='X-Workspace-Token')):
    return {'conversations': conversations.list(workspace_token)}


@app.get('/api/conversations/current')
def get_conversation(conversation_token: str = Header(alias='X-Conversation-Token')):
    return conversations.read(conversation_token)


class RenameRequest(BaseModel):
    title: str = Field(min_length=1, max_length=80)


@app.patch('/api/conversations/current')
def rename_conversation(body: RenameRequest, conversation_token: str = Header(alias='X-Conversation-Token')):
    if not body.title.strip():
        raise HTTPException(status_code=422, detail='Title must not be blank')
    conversations.rename(conversation_token, body.title.strip())
    return {'renamed': True}


@app.post('/api/conversations', status_code=201)
def create_conversation(workspace_token: str | None = Header(default=None, alias='X-Workspace-Token')):
    try:
        token = conversations.create(workspace_token) if workspace_token else conversations.create()
        return {'token': token, 'persistent': isinstance(conversations, ChatHistory)}
    except ConversationError as exc:
        raise HTTPException(status_code=exc.status, detail={'code': exc.code, 'message': exc.message}) from None


@app.delete('/api/conversations/current')
def clear_conversation(conversation_token: str = Header(alias='X-Conversation-Token')):
    try:
        conversations.delete(conversation_token)
        return {'cleared': True}
    except ConversationError as exc:
        raise HTTPException(status_code=exc.status, detail={'code': exc.code, 'message': exc.message}) from None


@app.get("/api/documents/{document_id}")
def document(document_id: str):
    if document_id != "flexi-ulife-prime-saver" or not PDF.is_file():
        raise HTTPException(status_code=404, detail="Document not found")
    return FileResponse(PDF, media_type="application/pdf", headers={
        "Content-Disposition": 'inline; filename="FLEXI-ULife-Prime-Saver.pdf"'})


app.mount("/assets", StaticFiles(directory=FRONTEND / "assets", check_dir=False), name="assets")


@app.get("/", include_in_schema=False)
def home():
    index = FRONTEND / "index.html"
    if not index.is_file():
        return JSONResponse(status_code=503, content={
            "code": "FRONTEND_NOT_BUILT", "message": "Run npm run build in frontend, or use the Vite development server."})
    return FileResponse(index, media_type="text/html")
