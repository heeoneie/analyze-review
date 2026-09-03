# CLAUDE.md

이 저장소에서 작업하기 전에 전부 읽는다.

## 무엇을 만드는가

**배달 매장 사장님을 위한 리뷰 답글 도구.** 기능 축은 두 개다.

1. **리뷰 수집** — 사장님 가게에 달린 리뷰를 모아서 한 곳에서 본다
2. **답글 생성** — 리뷰 한 건마다 사장님 말투에 맞는 답글 초안을 만든다

실제 중식 배달 매장에 도입해 운영 중이다. 가상의 사용자가 아니라 매일 이 화면을 쓰는 사장님이 있고, 화면이 깨지면 그날 장사에 영향이 간다.

> 이 저장소는 한때 미국 진출 브랜드의 소송 리스크를 다루는 **OntoReview** 갈래를 함께 갖고 있었다. 그 방향은 별도 프로젝트로 분리했고 관련 코드는 전부 제거했다. 판례 매칭 · 법적 노출 금액 · 온톨로지 그래프 · 플레이북 이야기가 나오면 그건 이 저장소의 일이 아니다.

## 지금 어디까지 됐는가

**동작하는 것**

- 답글 생성 — 별점에 따라 긍정/부정 경로가 갈린다 (`core/reply_generator.py`)
- 카카오 로그인과 매장 계정 (`backend/routers/auth.py`, `User`/`Store` 모델)
- 사장님이 실제로 게시한 답글의 이력 저장 (`ReplySample`, `backend/services/reply_history.py`)
- 쿠팡 · 네이버 스마트스토어 수집 **API** (`backend/services/crawler_service.py`, `POST /api/data/crawl`)

**아직 안 되는 것**

- **수집 · 리뷰 목록 화면이 없다.** 백엔드 엔드포인트는 살아 있는데 부르는 UI가 없다. `ReviewList` `PriorityReviewList` `MetricsOverview` `TopIssuesCard` `CategoryChart` `EmergingIssues` `ActionPlan` `FileUpload` 는 이 용도로 남겨 둔 것이지 죽은 코드가 아니다. **지우지 말 것.**
- **말투 학습 루프가 닫히지 않았다.** `reply_history.style_examples()` 를 호출하는 곳이 없고, `ReplyGenerator.generate()` 에 few-shot 예시를 받을 인자가 없다. 답글을 모으기만 하고 생성에 반영하지 않는다.
- **온보딩이 없다.** `record_onboarding()` 은 테스트에서만 불린다. 가입 직후 사장님이 자기 답글을 써넣는 경로가 없어서 첫 사용자는 예시 풀이 비어 있다.
- **배달앱 수집기가 없다.** 지금은 사장님이 리뷰를 복사해서 붙여넣는다.
- **보관기간 · 파기, 재위탁 동의가 없다.** 아래 법적 제약 참고.

## 넘지 말아야 할 선

조사해서 결론 낸 것들이다. 재검토 없이 뒤집지 않는다.

### 1. 플랫폼 자격증명을 저장하지 않는다 — 자동 게시는 하지 않는다

사장님의 배민/쿠팡이츠/요기요 계정을 받아 대신 로그인해 답글을 게시하는 방식은 **구조적으로 불가능하다.**

「개인정보의 안전성 확보조치 기준」 제7조 ① 단서가 비밀번호를 복호화되지 않는 일방향 암호화로 저장하도록 요구한다. 대리 로그인은 원문 비밀번호가 필요하므로 AES 로 암호화해도 충족할 수 없다. 기술적 타협점이 없다. 접근권한의 판단 주체가 서비스제공자라는 법리(대법원 2005도870 계열, 2024년 2021도5555 재확인)도 같은 방향이다.

→ **`Store` 모델에 플랫폼 자격증명 컬럼을 만들지 말 것.** 게시는 클립보드 복사 + 딥링크로 사장님이 직접 한다. 구글 비즈니스 프로필만 유일한 합법 자동화 경로이므로, 자동 게시를 다시 검토한다면 거기서 시작한다.

### 2. 매장 간 데이터를 섞지 않는다

우리는 개인정보보호법 제26조의 **수탁자**다. 위탁사무 대가 외의 독자적 이익을 가지면 이 구성이 깨지고 제17조 제3자 제공으로 재평가된다(대법원 2016도13263). 그때는 손님 동의가 필요한데 확보할 방법이 없다.

크로스-머천트 분석 · 벤치마킹 · 여러 매장 데이터를 합친 자체 모델 학습으로 넘어가면 제26조 ⑤ 위반이고, 제71조 2호에 따라 **5년 이하 징역**이다. 과태료가 아니라 형사처벌이다.

→ `style_examples()` 는 `store_id` 로 필터링하고 테스트로 고정돼 있다. **이 성질을 유지할 것.**

### 3. 손님 개인정보는 저장할 자리를 만들지 않는다

`ReplySample` 에는 손님 닉네임 컬럼이 없다. 저장할 자리가 없으면 실수로도 들어가지 않는다. 리뷰 본문은 `reply_history.sanitize()` 를 거친다.

**리뷰 원문을 저장소에 커밋하지 않는다.** 과거에 손님 리뷰가 공개 저장소에 올라가 되돌린 적이 있다(`b906c47`). 테스트 픽스처에도 실제 리뷰를 쓰지 않는다.

### 4. 외부 LLM 호출은 재위탁이다

OpenAI 에 리뷰 본문을 보내는 것은 제26조 ⑥ 의 재위탁이고 위탁자(사장님)의 동의가 필요하다. **아직 구현하지 않았다.** 보관기간 경과 시 파기(제21조 ①)도 마찬가지다. 새 사장님을 받기 전에 둘 다 해결해야 한다. "가명처리했으니 영구보관 가능"은 틀렸다 — 제21조 ① 이 가명정보의 처리 기간 경과를 파기 사유로 명시한다.

## 코딩 제약

- **과설계 금지.** 사용자는 아직 매장 한 곳이다. 벡터 DB(Chroma/Pinecone), 메시지 큐, 마이크로서비스를 도입하지 않는다. SQLite 로 충분하다.
- **슬림 배포를 깨지 않는다.** `requirements-web.txt` 만 설치한 이미지가 부팅돼야 한다. pandas · curl_cffi 에 의존하는 라우터는 `backend/main.py` 에서 `try/except ImportError` 로 감싸 선택 의존성으로 둔다. 무거운 패키지는 함수 안에서 지연 임포트한다(`core/utils/openai_client.py` 의 genai 참고).
- **스키마 변경은 alembic 으로.** `create_all` 이 아니라 마이그레이션을 추가한다. 기동 시 `upgrade_database()` 가 head 까지 올린다. 다운그레이드에서 데이터가 소실되지 않는지 확인한다.
- **테스트를 통과시킨다.** `pytest`, `cd frontend && npm test`, `pylint --rcfile=.pylintrc $(git ls-files '*.py')` 셋 다 CI 에서 돈다.

## 기술 스택

| 영역 | 사용 기술 |
|---|---|
| 백엔드 | Python, FastAPI, SQLAlchemy 2.0 (SQLite), Alembic |
| 프론트엔드 | React, Vite, Tailwind (다크), Recharts |
| LLM | OpenAI `gpt-4.1-mini` (답글), `gpt-4o-mini` (분석) / Gemini 폴백 |
| 수집 | curl_cffi (쿠팡, Chrome TLS 위장), Firecrawl (네이버) |
| 품질 | pytest, vitest, pylint, pre-commit, GitHub Actions, CodeRabbit |

## 개발 명령

```bash
# 설치
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env          # OPENAI_API_KEY 등 입력

# 실행
uvicorn backend.main:app --reload
cd frontend && npm run dev

# 테스트
pytest -v
cd frontend && npm test

# 린트 (CI 와 동일)
pylint --rcfile=.pylintrc $(git ls-files '*.py')
```

## Git 규칙

### 브랜치

항상 `main` 에서 새 브랜치를 만들어 작업하고, main 에 직접 커밋하지 않는다.

| Prefix | 용도 | 예시 |
|--------|------|------|
| `feat/` | 새 기능 추가 | `feat/add-crawling` |
| `fix/` | 버그 수정 | `fix/nan-serialization` |
| `refactor/` | 리팩터링 (동작 변경 없음) | `refactor/folder-structure` |
| `test/` | 테스트 추가/수정만 | `test/add-unit-tests` |
| `docs/` | 문서만 변경 | `docs/update-readme` |
| `chore/` | 빌드/설정/의존성 | `chore/upgrade-deps` |

### 커밋 메시지

Conventional Commits 형식을 따른다.

```
<type>: <한국어 또는 영어 요약>
```

- type: `feat`, `fix`, `refactor`, `test`, `docs`, `chore`
- 한 줄 요약, 필요시 본문에 상세 설명
