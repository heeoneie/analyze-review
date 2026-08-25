# 상시 호스팅 배포

지금은 맥북의 cloudflared 터널로 서비스되고 있어 맥북이 꺼지면 끊긴다.
컨테이너를 올리면 그럴 일이 없다.

컨테이너는 로컬에서 검증했다: health, 정적 파일, 매장 메뉴 41종 로드, 실제 답글 생성 모두 정상.

```bash
docker build -t dorya-reply .
docker run -p 8099:8000 -e OPENAI_API_KEY=... -e ACCESS_CODE=... dorya-reply
```

---

## 권장: Fly.io (도쿄 리전)

사장님이 하루에 몇 번 열어보는 패턴이라 **콜드 스타트**가 가장 중요하다.
Fly 의 `suspend` 는 메모리 스냅샷을 남겨 두므로 깨어나는 데 1초 안팎이다.
(Render 무료 플랜은 15분 놀면 내려가고 다시 뜨는 데 50초쯤 걸린다 — 리뷰 답글 달다가
기다리기엔 길다.)

```bash
fly auth login                                   # 브라우저 열림. 카드 등록 필요
fly launch --no-deploy --copy-config --name dorya-reply
fly secrets set OPENAI_API_KEY="$(grep '^OPENAI_API_KEY=' .env | cut -d= -f2-)" \
                ACCESS_CODE="$(grep '^ACCESS_CODE=' .env | cut -d= -f2-)"
fly deploy
```

`dorya-reply` 이름이 이미 쓰이고 있으면 `--name` 을 다른 걸로 바꾸고
`fly.toml` 의 `app` 값도 같이 고친다.

배포되면 `https://<app>.fly.dev` 로 확인:

```bash
curl -s https://dorya-reply.fly.dev/api/health
```

예상 비용: 대부분 시간 suspend 상태라 월 $0~2 수준.

### 기존 주소(reply.ontoreview.com) 그대로 쓰려면

사장님께 이미 링크를 보냈다면 주소를 바꾸지 않는 편이 낫다.

```bash
fly certs add reply.ontoreview.com
fly ips list                    # A / AAAA 주소 확인
```

그다음 Cloudflare 대시보드에서 `reply.ontoreview.com` 의 **CNAME(터널) 레코드를 지우고**
위 A/AAAA 레코드로 바꾼다. 프록시는 꺼도(DNS only) 켜도 된다.

바뀐 게 확인되면 맥북 쪽 터널은 정리한다:

```bash
launchctl unload ~/Library/LaunchAgents/com.dorya.reply-*.plist 2>/dev/null
pkill -f "cloudflared.*dorya-reply"
cloudflared tunnel delete dorya-reply
```

`ontoreview` 터널(api.ontoreview.com)은 별개라 건드리지 않는다.

---

## 대안 1: Render — CLI 없이 대시보드만으로

`render.yaml` 이 이미 있다. GitHub 레포를 연결하면 그대로 읽는다.

1. Render → New → Blueprint → 이 레포 선택
2. `OPENAI_API_KEY`, `ACCESS_CODE` 입력 (render.yaml 에 `sync: false` 로 표시돼 있음)
3. 배포

무료 플랜은 콜드 스타트 50초. 상시 가동은 Starter $7/월.
리전은 싱가포르가 제일 가깝다.

## 대안 2: Google Cloud Run — 이 사용량이면 사실상 $0

서울 리전(asia-northeast3)을 쓸 수 있고 무료 한도 안에 들어간다.
gcloud 설치와 결제 계정 활성화가 필요하다.

```bash
gcloud run deploy dorya-reply \
  --source . --region asia-northeast3 --allow-unauthenticated \
  --set-env-vars STORE_NAME="도야짬뽕 부천시청점",REPLY_LLM_MODEL=gpt-4.1-mini \
  --set-secrets OPENAI_API_KEY=openai-key:latest,ACCESS_CODE=access-code:latest
```

Cloud Run 은 `PORT` 를 주입하므로 Dockerfile 이 그대로 동작한다.

---

## 어느 쪽이든 확인할 것

```bash
curl -s https://<주소>/api/health                      # {"status":"ok"}
curl -s https://<주소>/api/reply/config                # requires_code: true 인지
curl -s -o /dev/null -w "%{http_code}\n" \
     -X POST https://<주소>/api/reply/generate \
     -H 'Content-Type: application/json' \
     -d '{"review_text":"맛있어요","rating":5,"menu":"도야짬뽕"}'   # 401 이어야 정상
```

마지막이 401 이 아니면 `ACCESS_CODE` 가 안 들어간 것이다. 그대로 두면
링크를 아는 사람이 누구나 OpenAI 요금을 쓰게 된다.
