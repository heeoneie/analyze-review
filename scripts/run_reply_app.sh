#!/usr/bin/env bash
# 답글 생성기를 로컬에서 띄우고 Cloudflare 터널로 공개한다.
#   ./scripts/run_reply_app.sh
# 종료: Ctrl+C (uvicorn 과 cloudflared 를 함께 내린다)
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PORT="${PORT:-8011}"
TUNNEL_CONFIG="${TUNNEL_CONFIG:-$HOME/.cloudflared/dorya-reply.yml}"
PYTHON="${PYTHON:-$ROOT/.venv/bin/python}"

cd "$ROOT"

if [ ! -d frontend/dist ]; then
  echo "프론트엔드 빌드가 없습니다. 빌드합니다…"
  (cd frontend && npm ci && npm run build)
fi

cleanup() {
  echo
  echo "종료합니다…"
  kill "${UVICORN_PID:-}" "${TUNNEL_PID:-}" 2>/dev/null || true
  wait 2>/dev/null || true
}
trap cleanup EXIT INT TERM

echo "API 서버 시작 (포트 $PORT)"
"$PYTHON" -m uvicorn backend.main:app --host 127.0.0.1 --port "$PORT" &
UVICORN_PID=$!

# 고정 시간 대기는 느린 기계에서 터널이 먼저 떠 502 를 내보낸다. 준비될 때까지 본다.
echo "API 준비 대기 중…"
for _ in $(seq 1 30); do
  if curl -sf "http://127.0.0.1:$PORT/api/health" >/dev/null 2>&1; then
    echo "API 준비됨"
    break
  fi
  sleep 1
done

if ! curl -sf "http://127.0.0.1:$PORT/api/health" >/dev/null 2>&1; then
  echo "API 가 30초 안에 뜨지 않았습니다. 터널을 시작하지 않습니다." >&2
  exit 1
fi

if [ -f "$TUNNEL_CONFIG" ]; then
  echo "Cloudflare 터널 시작 → https://reply.ontoreview.com"
  cloudflared --config "$TUNNEL_CONFIG" tunnel run dorya-reply &
  TUNNEL_PID=$!
else
  echo "터널 설정($TUNNEL_CONFIG)이 없어 로컬에서만 뜹니다: http://127.0.0.1:$PORT"
fi

wait
