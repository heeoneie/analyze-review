#!/usr/bin/env bash
# 맥북을 24시간 켜두는 서버로 쓰기 위한 설정.
#
#   ./deploy/mac-always-on.sh          현재 상태만 점검 (아무것도 바꾸지 않음)
#   ./deploy/mac-always-on.sh --apply  전원 설정을 실제로 적용 (sudo 필요)
#
# FileVault 와 자동 로그인은 보안 판단이 필요해서 이 스크립트가 건드리지 않는다.
# 무엇을 왜 바꿔야 하는지 안내만 한다.
set -uo pipefail

APPLY=false
[ "${1:-}" = "--apply" ] && APPLY=true

ok()   { printf "  \033[32m✓\033[0m %s\n" "$1"; }
warn() { printf "  \033[33m!\033[0m %s\n" "$1"; }
bad()  { printf "  \033[31m✗\033[0m %s\n" "$1"; }

echo
echo "── 전원 ─────────────────────────────────────────────"

if pmset -g batt | grep -q "AC Power"; then
  ok "전원 어댑터 연결됨"
else
  bad "배터리로 돌고 있다. 어댑터를 꽂아야 한다. 서버는 항상 전원에 연결돼 있어야 한다."
fi

DISABLESLEEP=$(pmset -g | awk '/disablesleep/ {print $2}')
if [ "${DISABLESLEEP:-0}" = "1" ]; then
  ok "뚜껑을 닫아도 잠들지 않음 (disablesleep=1)"
elif $APPLY; then
  echo "  뚜껑 닫힘 잠자기를 끕니다…"
  sudo pmset -a disablesleep 1 && ok "적용됨 (disablesleep=1)"
else
  warn "뚜껑을 닫으면 잠든다 → 서비스가 끊긴다. --apply 로 끌 수 있다."
fi

AUTORESTART=$(pmset -g custom 2>/dev/null | awk '/autorestart/ {print $2; exit}')
if [ "${AUTORESTART:-0}" = "1" ]; then
  ok "정전 후 자동 재시작 켜짐"
elif $APPLY; then
  sudo pmset -c autorestart 1 && ok "적용됨 (autorestart=1)"
else
  warn "정전 후 자동으로 켜지지 않는다. --apply 로 켤 수 있다."
fi

echo
echo "── 재부팅 후 자동 복귀 ──────────────────────────────"

FV=$(fdesetup status 2>/dev/null)
if echo "$FV" | grep -q "FileVault is On"; then
  warn "FileVault 켜짐"
  echo "     재부팅되면 디스크 잠금 해제 화면에서 멈춘다. 누가 암호를 넣기 전까지"
  echo "     Docker 도 앱도 뜨지 않는다. 정전이 나면 사람이 가야 한다는 뜻이다."
  echo
  echo "     선택지:"
  echo "       1) 그대로 둔다. 평소(뚜껑 닫기·화면 잠금)에는 멀쩡하고,"
  echo "          정전 같은 드문 일에만 손이 간다. 보안이 유지된다."
  echo "       2) 계획된 재부팅은  sudo fdesetup authrestart  로 한다."
  echo "          이번 한 번만 잠금을 자동 해제하고 올라온다."
  echo "       3) FileVault 를 끈다. 무인 복귀는 되지만, 이 디스크에 OpenAI API 키가"
  echo "          평문으로 있다. 맥북을 잃어버리면 그대로 노출된다. 권장하지 않는다."
else
  ok "FileVault 꺼짐 — 재부팅 후 자동 복귀 가능"
  if defaults read /Library/Preferences/com.apple.loginwindow autoLoginUser >/dev/null 2>&1; then
    ok "자동 로그인 켜짐"
  else
    warn "자동 로그인이 꺼져 있다. 시스템 설정 > 사용자 및 그룹 > 자동 로그인 을 켜야"
    echo "     재부팅 후 Docker Desktop 이 스스로 뜬다."
  fi
fi

echo
echo "── Docker ───────────────────────────────────────────"

if ! command -v docker >/dev/null 2>&1; then
  bad "docker 명령을 찾을 수 없다. Docker Desktop 을 설치해야 한다."
elif ! docker info >/dev/null 2>&1; then
  bad "Docker 데몬이 안 떠 있다. Docker Desktop 을 실행한다."
else
  ok "Docker 실행 중"
  warn "Docker Desktop 설정에서 'Start Docker Desktop when you sign in' 을 켰는지 확인한다."
  echo "     (Settings > General) 이게 꺼져 있으면 재부팅 후 컨테이너가 안 뜬다."
fi

echo
echo "── 서비스 ───────────────────────────────────────────"

cd "$(dirname "${BASH_SOURCE[0]}")/.." || exit 1
if docker compose ps --format '{{.Service}} {{.Status}}' 2>/dev/null | grep -q .; then
  docker compose ps --format '  {{.Service}}: {{.Status}}'
else
  warn "컨테이너가 떠 있지 않다.  docker compose up -d --build"
fi

echo
if curl -sf --max-time 15 https://reply.ontoreview.com/api/health >/dev/null 2>&1; then
  ok "https://reply.ontoreview.com 응답 정상"
else
  bad "공개 주소가 응답하지 않는다.  docker compose logs tunnel  을 확인한다."
fi

CODE=$(curl -s -o /dev/null -w "%{http_code}" --max-time 15 \
  -X POST https://reply.ontoreview.com/api/reply/store/generate \
  -H 'Content-Type: application/json' \
  -d '{"review_text":"맛있어요","rating":5,"menu":"도야짬뽕"}' 2>/dev/null)
if [ "$CODE" = "401" ]; then
  ok "접속 코드 잠금 동작 중 (401)"
else
  bad "코드 없이 호출했는데 $CODE 가 나왔다. ACCESS_CODE 가 안 걸렸다."
fi

echo
$APPLY || echo "점검만 했다. 전원 설정을 실제로 바꾸려면: ./deploy/mac-always-on.sh --apply"
echo
