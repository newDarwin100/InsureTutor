#!/usr/bin/env bash
set -euo pipefail
project_root="$(cd "$(dirname "$0")/.." && pwd)"
cd "$project_root"

if ! command -v node >/dev/null || ! command -v npm >/dev/null; then
  echo '请先安装 Node.js 22.12+（或 20.19+）和 npm。' >&2
  exit 1
fi
if [[ ! -x .venv/bin/python ]] || ! .venv/bin/python -c 'import fastapi, uvicorn, dotenv' >/dev/null 2>&1; then
  echo '请准备 Python 3.12 的 .venv，然后执行：.venv/bin/python -m pip install -r backend/requirements.txt' >&2
  exit 1
fi
if [[ ! -d frontend/node_modules ]]; then
  echo '请先在 frontend 目录执行 npm ci。' >&2
  exit 1
fi
if [[ ! -f .env ]]; then
  echo '请复制 .env.example 为 .env，填写自己的 API key。' >&2
  exit 1
fi

backend_pid=''
frontend_pid=''
cleanup() {
  trap - EXIT INT TERM
  [[ -z "$frontend_pid" ]] || kill "$frontend_pid" 2>/dev/null || true
  [[ -z "$backend_pid" ]] || kill "$backend_pid" 2>/dev/null || true
  wait 2>/dev/null || true
}
trap cleanup EXIT
trap 'exit 130' INT
trap 'exit 143' TERM

.venv/bin/python -m uvicorn app.main:app --app-dir backend --host 127.0.0.1 --port 8000 --reload --no-access-log &
backend_pid=$!
node frontend/node_modules/vite/bin/vite.js frontend --host 127.0.0.1 &
frontend_pid=$!
echo '开发界面：http://127.0.0.1:5173'
echo '接口文档：http://127.0.0.1:8000/docs'
echo 'Ctrl+C 停止两端。当前为连接测试，RAG 尚未接入。'
while kill -0 "$backend_pid" 2>/dev/null && kill -0 "$frontend_pid" 2>/dev/null; do
  sleep 1
done
echo '开发服务已退出，请检查上方日志。' >&2
exit 1
