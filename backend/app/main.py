"""Application scaffold: health, document access and an explicitly labelled demo."""

import json
import os
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

ROOT = Path(__file__).resolve().parents[2]
load_dotenv(ROOT / ".env", override=False)
PDF = ROOT / "docs/FLEXI-ULife Prime Saver.pdf"
FRONTEND = ROOT / "frontend/dist"

app = FastAPI(title="InsureTutor", version="0.1.0")


class DemoRequest(BaseModel):
    message: str = Field(min_length=1, max_length=2000)


@app.get("/health/live")
def live():
    return {"status": "ok", "stage": "scaffold"}


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
    return {"stage": "scaffold", "backend_ready": True, "rag_ready": False,
            "document_available": PDF.is_file(), "knowledge_counts": counts,
            "api_key_configured": bool(key and key != "your_openai_api_key_here")}


@app.get("/health/ready")
def ready():
    # A healthy web server is not yet a working RAG tutor.
    return JSONResponse(status_code=503, content={
        "status": "not_ready", "code": "RAG_NOT_IMPLEMENTED",
        "message": "Application scaffold is running; retrieval is not connected yet."})


@app.post("/api/demo")
def demo(body: DemoRequest):
    if not body.message.strip():
        raise HTTPException(status_code=422, detail="Message must not be blank")
    return {"mode": "connection_test", "received": body.message.strip(),
            "message": "前后端连接成功。此消息仅测试连接，尚未调用检索或模型。"}


@app.post("/api/chat")
def chat():
    raise HTTPException(status_code=503, detail={"code": "RAG_NOT_IMPLEMENTED",
                                               "message": "Retrieval and model generation are not connected yet."})


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
