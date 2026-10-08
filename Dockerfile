FROM node:22-slim AS frontend-build
WORKDIR /build
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci --no-audit --no-fund
COPY frontend/ ./
RUN npm run build

FROM python:3.12-slim AS runtime
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app
COPY backend/requirements.txt /app/backend/requirements.txt
RUN pip install --no-cache-dir -r backend/requirements.txt \
    && useradd --uid 10001 --create-home appuser
COPY --chown=appuser:appuser backend/app/ /app/backend/app/
COPY --chown=appuser:appuser evaluation/results/ /app/evaluation/results/
COPY --chown=appuser:appuser data/reviewed/ /app/data/reviewed/
COPY --chown=appuser:appuser data/processed/ /app/data/processed/
COPY --chown=appuser:appuser ["docs/FLEXI-ULife Prime Saver.pdf", "/app/docs/"]
COPY --from=frontend-build --chown=appuser:appuser /build/dist/ /app/frontend/dist/
RUN mkdir -p /app/data/chroma && chown appuser:appuser /app/data/chroma
USER appuser
EXPOSE 8000
HEALTHCHECK --interval=15s --timeout=5s --start-period=15s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health/live', timeout=3)"
CMD ["python", "-m", "uvicorn", "app.main:app", "--app-dir", "backend", "--host", "0.0.0.0", "--port", "8000", "--no-access-log"]
