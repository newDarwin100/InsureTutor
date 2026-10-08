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
echo '构建并启动应用。首次启动会将已核对的 PDF 文本发送到 embedding API，产生用量；以后复用索引。'
docker compose up --build -d
container_id="$(docker compose ps --all -q app)"
if [[ -z "$container_id" ]]; then
  echo '应用容器未启动。请执行 docker compose logs app 查看原因。' >&2
  docker compose logs --tail=40 app >&2
  exit 1
fi
echo '等待索引和 RAG 就绪（最多 10 分钟）。另开终端运行 docker compose logs -f app 可看进度。'
deadline=$((SECONDS + 600))
while (( SECONDS < deadline )); do
  container_state="$(docker inspect --format '{{.State.Status}}' "$container_id")"
  if [[ "$container_state" == 'exited' || "$container_state" == 'dead' ]]; then
    break
  fi
  health_status="$(docker inspect --format '{{if .State.Health}}{{.State.Health.Status}}{{else}}starting{{end}}' "$container_id")"
  if [[ "$health_status" == 'healthy' ]]; then
    echo '应用已启动：http://127.0.0.1:8000'
    echo '配置、来源和索引已就绪；健康检查不会调用模型或验证 API 余额。'
    echo '日志：docker compose logs -f app；停止：docker compose down'
    exit 0
  fi
  if [[ "$health_status" == 'unhealthy' ]]; then
    break
  fi
  sleep 2
done
echo '应用启动失败或尚未就绪。以下是最近日志：' >&2
docker compose logs --tail=40 app >&2
echo '修复配置后重新运行 bash scripts/start.sh。索引已写入的批次会复用，不会自动反复付费重试。' >&2
exit 1
