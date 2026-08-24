# 리뷰 답글 생성기 (외식업 배달앱)

배달앱 리뷰를 붙여넣으면 그 주문에 맞는 사장님 답글을 만들어 준다.
화면 하나로 끝나고, 로그인·회원가입·저장 기능은 없다.

- 공개 주소: **https://reply.ontoreview.com**
- 접속 코드: `.env` 의 `ACCESS_CODE`

## 왜 긍정 리뷰용 생성기를 따로 두는가

실제 매장(중식 배달) 리뷰 441건을 보면:

| 항목 | 수치 |
|---|---|
| 별점 5점 | 405건 (92%) |
| 3점 이하 | 17건 (4%) |
| 리뷰 본문 없음 | 119건 (27%) |
| 답변 첫 줄이 "도야짬뽕 부천시청점에서 주문해 주셔서…" 계열 | 131건 (31%) |

사과할 일이 없는 리뷰가 대부분이라 쓸 말이 없고, 그래서 같은 인사말이 반복된다.
답변을 서로 다르게 만드는 재료는 **주문한 메뉴**뿐이다.

## 구조

| 파일 | 역할 |
|---|---|
| `core/reply_generator.py` | 긍정·부정 답글 생성. 도입·끝맺음 방식을 매번 바꾸고, 검사에 걸리면 다시 생성한다 |
| `core/menu_profiles.py` | 주문메뉴 파싱(리뷰 이벤트 서비스 품목 분리), 메뉴별 표현 키워드, 매장 메뉴 목록 |
| `core/reply_text.py` | 금지 표현·매장명 시작·첫문장 골격·문장 중복 검사 |
| `backend/routers/reply.py` | `POST /api/reply/store/generate` + 접속 코드 확인 |
| `frontend/src/pages/ReplyStudio.jsx` | 입력 → 생성 → 복사 화면 |
| `scripts/verify_replies.py` | 실제 CSV로 생성하고 첫 문장 중복을 검사 |
| `tests/core/test_menu_profiles.py`, `test_reply_text.py` | 새 모듈 테스트 38건 |
| `data/store_menu.json` | 매장이 실제로 파는 메뉴 목록 (없는 메뉴 제안 방지) |

### 답글이 서로 달라지게 만드는 장치

1. **주문 메뉴 반영** — 메뉴마다 다른 표현 축(짬뽕=불맛·국물 / 짜장=춘장 향 / 탕수육=바삭함 / 만두·꽃빵=곁들임).
   힌트는 완성된 문장이 아니라 키워드로 준다. 문장을 주면 모델이 그대로 베껴 쓴다.
2. **도입 방식 8종 로테이션** — 메뉴 디테일, 리뷰 인용, 곁들임 제안, 주방 시선, 배달 상태, 시간대, 손님 반응, 주문 조합.
3. **끝맺음 방식 6종 로테이션** — 첫 문장만 돌리면 끝맺음이 "노력하겠습니다"로 수렴한다.
4. **이모지 로테이션** — 매번 허용하면 모델이 같은 이모지(🙂)로 수렴한다. 쓸지 말지와 어떤 걸 쓸지를 코드가 정한다.
5. **생성 후 검사 → 재생성** — 아래 항목에 걸리면 위반 내용을 알려 주고 다시 만든다 (최대 3회).

### 검사 항목

- 금지 표현: "주문해 주셔서 진심으로 감사", "맛있게 드셔주셔서 감사", "다음에도 찾아주세요",
  "소중한 리뷰 감사", "정성껏 준비하겠습니다", "기쁩니다/뿌듯합니다" 계열, "노력하겠습니다"
- 매장명으로 시작하는 인사
- 배치 안에서 첫 문장·끝 문장 중복 (bigram 유사도)
- 첫 문장 **골격** 중복 — 내용어만 바꾼 "~하셨네요 / ~하셨군요"의 반복
- 주문에 없는 메뉴를 드신 것처럼 언급
- 길이(긍정 100~200자 / 부정 130~250자), 이모지 개수

## 기존 기능과의 관계

대시보드에서 쓰던 경로는 그대로 둔다. 깨뜨리지 않았다.

| 경로 | 쓰는 곳 | 상태 |
|---|---|---|
| `POST /api/reply/generate` | 대시보드 `ReplyPanel.jsx` | 그대로. 반환 형태(`tone`/`key_points_addressed`) 유지 |
| `POST /api/reply/generate-batch` | 다건 처리 | 그대로 |
| `POST /api/reply/store/generate` | 사장님 단독 화면 | 신규. 접속 코드 필요 |

`ReplyGenerator` 의 `generate_single` / `generate_batch` 는 시그니처와 반환 형태를
그대로 두고 프롬프트 내용만 배달 음식 맥락으로 바꿨다. 기존 테스트
(`tests/core/test_reply_generator.py`) 는 수정 없이 통과한다.

새로 추가된 것:

- `generate_positive` — 좋은 리뷰용
- `generate_negative` — 검사·재생성이 붙은 불만 리뷰용
- `generate` — 별점으로 분기
- `generate_series` — 여러 건 순차 생성. 앞서 쓴 문장을 넘겨 중복을 막는다
  (`generate_batch` 는 한 번의 호출로 여러 건을 처리하는 기존 방식이라 그대로 둠)

## 실행

```bash
# 로컬 + 공개 터널
./scripts/run_reply_app.sh

# 로컬만
uvicorn backend.main:app --port 8011
cd frontend && npm run dev        # http://localhost:5173
```

맥북이 재부팅돼도 계속 뜨게 하려면:

```bash
cp deploy/com.dorya.reply-*.plist ~/Library/LaunchAgents/
launchctl load ~/Library/LaunchAgents/com.dorya.reply-api.plist
launchctl load ~/Library/LaunchAgents/com.dorya.reply-tunnel.plist
```

## 검증

```bash
python scripts/verify_replies.py <csv_path> --positive 10 --negative 5 --out results/reply_verification.json
```

첫 문장·끝 문장이 겹치면 종료 코드 1과 함께 어느 건끼리 겹쳤는지 출력한다.

산출물(`results/reply_verification.*`)은 **커밋하지 않는다.** 손님이 쓴 리뷰 원문이
그대로 들어가기 때문이다. 이 레포는 공개다.

마지막 실행 결과 (5점 10건 + 3점 이하 5건):

| 항목 | 결과 |
|---|---|
| 첫 문장 겹침 | 없음 |
| 끝 문장 겹침 | 없음 |
| 긍정 답변 길이 | 109~192자 (기준 100~200) |
| 재시도 후에도 남은 위반 | 15건 중 2건 |

## 다른 매장에 쓰려면

1. `.env` 의 `STORE_NAME` 변경
2. `data/store_menu.json` 을 그 매장 메뉴로 교체
3. `core/menu_profiles.py` 의 `FLAVOR_AXES` 에 그 업종의 메뉴 키워드 추가

## 컨테이너 배포

```bash
docker build -t dorya-reply .
docker run -p 8099:8000 -e OPENAI_API_KEY=... -e ACCESS_CODE=... dorya-reply
```

- **홈서버**에 올리는 절차: [deploy/HOMESERVER.md](deploy/HOMESERVER.md)
  (`docker compose up -d --build` 하나로 앱과 터널이 함께 뜬다)
  - 맥을 서버로 쓴다면 `./deploy/mac-always-on.sh` 로 잠자기·정전·FileVault 를 점검한다
- **클라우드 호스팅**(Fly.io / Render / Cloud Run): [deploy/DEPLOY.md](deploy/DEPLOY.md)
