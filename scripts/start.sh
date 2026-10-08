#!/usr/bin/env bash
set -euo pipefail
project_root="$(cd "$(dirname "$0")/.." && pwd)"
cd "$project_root"

if ! command -v docker >/dev/null || ! docker compose version >/dev/null 2>&1; then
  echo '请安装并启动 Docker（含 Docker Compose）。' >&2
  exit 1
fi
if ! docker info >/dev/null 2>&1; then
  echo 'Docker 引擎未启动，请启动后重试。' >&2
  exit 1
fi
if [[ ! -f .env ]]; then
  echo '请先复制 .env.example 为 .env，填写自己的 API key。' >&2
  exit 1
fi
docker compose up --build -d
container_id="$(docker compose ps -q app)"
if [[ -z "$container_id" ]]; then
  echo '应用容器未启动。请执行 docker compose logs app 查看原因。' >&2
  exit 1
fi
for attempt in {1..60}; do
  health_status="$(docker inspect --format '{{.State.Health.Status}}' "$container_id")"
  if [[ "$health_status" == 'healthy' ]]; then
    echo '应用已启动：http://127.0.0.1:8000'
    echo '当前为连接测试；网页健康不代表 RAG 已就绪。'
    echo '日志：docker compose logs -f app；停止：docker compose down'
    exit 0
  fi
  if [[ "$health_status" == 'unhealthy' ]]; then
    break
  fi
  sleep 2
done
echo '应用未在等待时间内通过健康检查。请执行 docker compose logs app 查看原因。' >&2
exit 1
