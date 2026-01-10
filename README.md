# 커머스 리뷰 분석 PoC (E-commerce Review Analysis)

## 프로젝트 목적

이 프로젝트는 **커머스 리뷰 텍스트를 AI로 분석**하여, 사람이 직접 읽지 않아도 다음을 자동으로 도출하는 PoC(Proof of Concept)입니다.

- 지금 가장 큰 문제 (TOP 3)
- 우선 개선해야 할 포인트 (최근 급증 이슈)
- 즉시 실행 가능한 개선 액션 제안

### 해결하려는 문제

현재 커머스 환경에서 리뷰는 많이 쌓이지만:
- 어떤 문제가 가장 빈번한지
- 최근 들어 급증한 이슈는 무엇인지
- 지금 당장 고치면 효과가 큰 부분이 어디인지

를 한눈에 파악하기 어렵습니다.

이 PoC는 **리뷰 데이터를 매출·운영 의사결정에 활용**하는 가능성을 검증합니다.

---

## 핵심 기능

### 1. 부정 리뷰 기준 TOP 3 문제점 도출
평점 3점 이하 리뷰를 분석하여 가장 빈번한 문제점 3가지를 자동으로 추출합니다.

**예시 출력:**
```
1. Delivery Delay
   빈도: 145회 (32.1%)
   예시:
   - Package arrived 2 weeks late
   - Delivery took too long
   - Expected delivery in 5 days, took 15

2. Wrong Item
   빈도: 89회 (19.7%)
   ...
```

### 2. 최근 기간 급증 이슈 탐지
이전 기간 대비 언급 빈도가 빠르게 증가한 문제를 식별합니다.

**예시 출력:**
```
📈 최근 급증한 이슈:

1. Packaging Damage
   증가율: +156.3%
   이전: 16회 → 최근: 41회
```

### 3. AI 기반 개선 액션 제안
분석 결과를 바탕으로 즉시 실행 가능한 개선 방안을 제시합니다.

**예시 출력:**
```
💡 개선 액션 제안:

1. 배송 파트너사와 긴급 미팅을 통해 최근 지연 원인을 파악하고, 2주 내 배송 프로세스 개선 계획을 수립하세요
2. 포장 품질 점검 프로세스를 강화하고, 파손 위험이 높은 상품군에 대해 이중 포장을 적용하세요
3. 상품 상세 페이지에 사이즈 가이드와 실측 정보를 추가하여 오배송을 줄이세요
```

---

## 기술 스택

- **Python 3.8+**
- **Pandas**: 데이터 전처리
- **OpenAI API (GPT-4o-mini)**: LLM 기반 리뷰 분석
- **Kaggle Hub**: Olist Brazilian E-commerce 데이터셋 다운로드

---

## 데이터셋

**Olist Brazilian E-commerce Dataset** 사용
- 출처: Kaggle
- 포함 정보: 실제 커머스 리뷰 텍스트, 평점, 주문 시간 등
- 사용 컬럼:
  - `review_id`: 리뷰 고유 ID
  - `review_text`: 리뷰 텍스트
  - `rating`: 평점 (1-5)
  - `created_at`: 리뷰 작성 시간

---

## 설치 및 실행

### 1. 저장소 클론
```bash
git clone <repository-url>
cd analyze-review
```

### 2. 가상환경 생성 (권장)
```bash
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
```

### 3. 패키지 설치
```bash
pip install -r requirements.txt
```

### 4. 환경변수 설정
`.env` 파일을 생성하고 OpenAI API 키를 추가합니다:

```bash
OPENAI_API_KEY=your_openai_api_key_here
```

### 5. 실행
```bash
python main.py
```

**첫 실행 시:**
- Kaggle에서 자동으로 데이터셋을 다운로드합니다
- Kaggle API 인증이 필요할 수 있습니다 ([설정 가이드](https://github.com/Kaggle/kaggle-api#api-credentials))

---

## 프로젝트 구조

```
analyze-review/
├── main.py              # 메인 실행 스크립트
├── data_loader.py       # 데이터 다운로드 및 전처리
├── analyzer.py          # LLM 기반 분석 로직
├── config.py            # 설정 파일
├── requirements.txt     # 패키지 의존성
├── .env.example         # 환경변수 예시
├── .gitignore
└── README.md
```

---

## 설정 커스터마이징

[config.py](config.py)에서 분석 파라미터를 조정할 수 있습니다:

```python
# 부정 리뷰 기준 (이 점수 이하를 부정 리뷰로 간주)
NEGATIVE_RATING_THRESHOLD = 3

# 최근 기간 (일)
RECENT_PERIOD_DAYS = 30

# 비교 기간 (일)
COMPARISON_PERIOD_DAYS = 60

# LLM 모델
LLM_MODEL = "gpt-4o-mini"
```

---

## 예상 결과 예시

```
================================================================================
  Step 6: Identifying Top 3 Issues
================================================================================

📊 TOP 3 문제점 (부정 리뷰 기준):

1. Delivery Delay
   빈도: 145회 (32.1%)
   예시:
   - Package arrived 2 weeks late
   - Delivery took too long
   - Expected delivery in 5 days, took 15

2. Wrong Item
   빈도: 89회 (19.7%)
   예시:
   - Received different color than ordered
   - Wrong size delivered
   - Got a completely different product

3. Poor Quality
   빈도: 67회 (14.8%)
   예시:
   - Material feels cheap
   - Broke after first use
   - Not as described in photos

================================================================================
  Step 7: Detecting Emerging Issues
================================================================================

📈 최근 급증한 이슈:

1. Packaging Damage
   증가율: +156.3%
   이전: 16회 → 최근: 41회

================================================================================
  Step 8: Generating Action Plan
================================================================================

💡 개선 액션 제안:

1. 배송 파트너사와 긴급 미팅을 통해 최근 지연 원인을 파악하고, 배송 프로세스 개선 계획을 수립하세요
2. 포장 품질 점검을 강화하고, 파손 위험 상품에 이중 포장을 적용하세요
3. 상품 상세 페이지에 정확한 사이즈 가이드를 추가하여 오배송을 줄이세요
```

---

## 제한사항 및 범위

이 프로젝트는 **PoC(Proof of Concept)** 수준입니다:

- ✅ 가능성 검증용
- ❌ 상용 서비스 아님
- ❌ 결제/유저 관리 없음
- ❌ 정확도 최적화 없음
- ❌ 프로덕션 레벨 에러 핸들링 없음

**목적:** "리뷰 데이터를 활용하면 의사결정에 어떤 도움이 되는가" 검증

---

## 비용 안내

- OpenAI API 사용료가 발생합니다
- 기본 설정(GPT-4o-mini, 샘플 200개)으로 실행 시 약 $0.10-0.30 정도 예상
- 대량 데이터 분석 시 샘플 크기를 조정하여 비용을 조절할 수 있습니다

---

## 라이선스

MIT License

---

## 문의 및 기여

이슈나 개선 제안은 GitHub Issues를 통해 등록해주세요.
