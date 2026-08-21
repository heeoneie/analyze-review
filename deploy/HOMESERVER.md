# 홈서버에 올리기

지금 맥북에서 도는 것과 **똑같은 구성**을 홈서버로 옮기는 절차다.
클라우드 호스팅 대신 이걸 쓰면 비용이 들지 않고, 이미 터널을 쓰고 있어서
포트포워딩·고정 IP·DDNS가 전부 필요 없다. 집 IP도 노출되지 않는다.

`docker compose up -d --build` 하나로 앱과 터널이 같이 뜬다.
맥북에서 이 구성 그대로 검증했다 (공개 URL 응답, 접속 코드 401 차단, 실제 답글 생성).

## 홈서버가 이 맥북(MacBookPro17,1 / M1 2020)이라면

옮길 게 없다. compose 스택이 이미 여기서 돌고 있다.
남은 건 **항상 켜져 있게 만드는 것**뿐이고, 아래 스크립트가 점검해 준다.

```bash
./deploy/mac-always-on.sh          # 점검만 (아무것도 바꾸지 않음)
./deploy/mac-always-on.sh --apply  # 전원 설정 적용 (sudo)
```

### 맥을 서버로 쓸 때 걸리는 것들

| 항목 | 왜 문제인가 | 해결 |
|---|---|---|
| 뚜껑 닫기 | 잠들면서 서비스가 끊긴다 | `sudo pmset -a disablesleep 1` |
| 배터리 | 방전되면 끝 | 어댑터를 항상 연결 |
| 정전 | 저절로 켜지지 않는다 | `sudo pmset -c autorestart 1` |
| FileVault | 재부팅 시 디스크 잠금 화면에서 멈춘다 | 아래 참고 |
| Docker Desktop | 로그인해야 데몬이 뜬다 | Settings > General > "Start Docker Desktop when you sign in" |

> 개발 중에는 `caffeinate` 같은 게 잠자기를 막고 있을 수 있다.
> 그건 그 세션이 끝나면 사라진다. `disablesleep` 을 켜야 영구적이다.

### FileVault — 판단이 필요한 부분

FileVault 가 켜져 있으면 재부팅 후 **사람이 디스크 암호를 넣기 전까지** 아무것도 뜨지 않는다.
무인 복귀가 안 된다는 뜻이다. macOS 는 FileVault 가 켜져 있으면 자동 로그인도 막는다.

1. **그대로 둔다 (권장).** 뚜껑 닫기·화면 잠금 같은 평상시 동작에는 아무 문제가 없다.
   정전처럼 드문 경우에만 손이 간다.
2. **계획된 재부팅은** `sudo fdesetup authrestart` **로 한다.** 이번 한 번만 자동으로
   잠금을 풀고 올라온다. 업데이트 후 재부팅에 쓰면 된다.
3. **FileVault 를 끈다.** 무인 복귀는 되지만 `.env` 의 OpenAI API 키와 터널 자격증명이
   평문으로 남는다. 맥북을 분실하면 그대로 노출된다. 권장하지 않는다.

정전이 걱정되면 UPS 가 FileVault 를 끄는 것보다 나은 해법이다.

---

## 다른 기계로 옮기는 경우

### 홈서버에 필요한 것

- Docker 와 Docker Compose (`docker compose version` 으로 확인)
- 메모리 1GB 이상. 프론트엔드 빌드(`npm ci` + vite)가 제일 많이 먹는다.
- 부팅 시 Docker 데몬이 자동 시작되도록 설정
  (`sudo systemctl enable docker` — 시놀로지/QNAP은 기본으로 켜져 있다)

CPU 종류(arm64/x86)는 신경 쓰지 않아도 된다. **홈서버에서 직접 빌드**하므로
그 기계에 맞는 이미지가 만들어진다.

> 라즈베리파이처럼 메모리가 작은 기기라면 프론트엔드 빌드가 버거울 수 있다.
> 그럴 땐 맥북에서 `cd frontend && npm run build` 한 뒤 `frontend/dist` 를 통째로
> 복사해 가면 컨테이너 빌드 단계에서 다시 만들지 않아도 된다.

## 옮길 파일

레포는 git 으로 받고, 커밋되지 않는 두 가지만 따로 복사한다.

```bash
# 홈서버에서
git clone https://github.com/heeoneie/analyze-review.git
cd analyze-review
git checkout feat/restaurant-reply-generator
```

맥북에서 홈서버로 복사 (`<홈서버>` 는 실제 주소로):

```bash
scp .env <홈서버>:~/analyze-review/.env
scp ~/.cloudflared/0c0c0bc8-cb6b-49e2-90a1-8dd47b9773db.json \
    <홈서버>:~/analyze-review/cloudflared/
```

`cloudflared/config.yml` 은 레포에 들어 있으니 복사할 필요 없다.
자격증명 `.json` 은 **비밀**이다. 유출되면 남이 이 도메인으로 트래픽을 받을 수 있다.
`.gitignore` 에 걸어 뒀다.

## 띄우기

```bash
docker compose up -d --build
docker compose ps          # app 이 (healthy), tunnel 이 Up 이어야 한다
```

`restart: unless-stopped` 라서 재부팅해도 알아서 다시 뜬다.
LaunchAgent 같은 걸 따로 걸 필요가 없다.

## 맥북 쪽 정리 — 홈서버가 뜬 걸 확인한 다음에

같은 터널을 두 기계에서 동시에 돌리면 Cloudflare 가 양쪽으로 트래픽을 나눠 보낸다.
둘 다 정상이면 문제는 없지만, 맥북이 꺼지면 절반이 실패하므로 반드시 정리한다.

```bash
# 맥북에서
docker compose down                                  # compose 로 띄웠다면
pkill -f "cloudflared.*dorya-reply"                  # 직접 띄웠다면
launchctl unload ~/Library/LaunchAgents/com.dorya.reply-*.plist 2>/dev/null
```

`ontoreview` 터널(api.ontoreview.com)은 별개다. 건드리지 않는다.

## 확인

```bash
curl -s https://reply.ontoreview.com/api/reply/config
# {"store_name":"도야짬뽕 부천시청점","model":"gpt-4.1-mini","requires_code":true}

curl -s -o /dev/null -w "%{http_code}\n" \
     -X POST https://reply.ontoreview.com/api/reply/generate \
     -H 'Content-Type: application/json' \
     -d '{"review_text":"맛있어요","rating":5,"menu":"도야짬뽕"}'
# 401 이어야 정상. 200 이면 ACCESS_CODE 가 안 들어간 것이다.
```

마지막으로 맥북을 아예 꺼 두고 폰에서 한 번 열어 본다. 그게 진짜 확인이다.

## 나중에 코드를 고쳤을 때

```bash
git pull
docker compose up -d --build
```

## 로그 보기

```bash
docker compose logs -f app        # 답글 생성 실패, 재생성 기록
docker compose logs -f tunnel     # 터널 연결 상태
```

## 접속 코드 바꾸기

`.env` 의 `ACCESS_CODE` 를 고치고 `docker compose up -d` 하면 된다.
사장님 브라우저에는 이전 코드가 저장돼 있어서 다시 입력하는 화면이 뜬다.
