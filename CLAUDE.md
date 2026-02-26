# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Business Direction

**OntoReview** — 온톨로지 기반 글로벌 리스크 인텔리전스 플랫폼 ("Palantir for Reputation")

- **원래**: 이커머스 리뷰 관리 PoC → **전환 후**: 무사고 증명 B2B SaaS
- **차별점**: 단순 감성 통계가 아닌 온톨로지 + Knowledge Graph + AI로 리스크 인과관계 추론
- **타겟**: 병원/금융/핀테크(1티어), 글로벌 브랜드(2티어), 게임/엔터(3티어)
- **데이터 전략**: 현재 Mock → 공식 API 우선 (YouTube → Reddit → Naver 순서, 봇 크롤링 지양)
- **6개 탭 중 1개 구현**: Risk Intelligence만 완성, 나머지 5개 Coming Soon
  - ✅ Risk Intelligence (온톨로지 그래프 + 컴플라이언스 + 회의 안건)
  - 🔒 Risk Response Playbook / Agent Communication Setup / Domain Ontology Studio / Global Compliance Tracker / Trust & Safety Audit
- **설계 원칙**: 다국어 처음부터(한/영), 글로벌 타겟, 기술 2개 이상 융합, 프리미엄 포지셔닝

## Project Overview

이커머스 리뷰 분석 PoC로 시작하여 리스크 인텔리전스 플랫폼으로 발전. LLM(GPT-4o-mini)으로 리뷰/소셜 데이터를 분석해 리스크 인과관계를 추론하고, 컴플라이언스 보고서 및 긴급 회의 안건을 자동 생성한다.

## Project Structure

```
review-dashboard/
├── core/                    # Core AI analysis package
│   ├── config.py            # Environment & analysis configuration
│   ├── analyzer.py          # LLM-powered review categorization
│   ├── data_loader.py       # Data loading (Kaggle, CSV)
│   ├── report_utils.py      # Report formatting
│   ├── utils/               # Shared utilities
│   │   ├── json_utils.py
│   │   ├── openai_client.py
│   │   ├── prompt_templates.py
│   │   ├── review_categories.py
│   │   ├── cli_helpers.py
│   │   └── analysis_workflow.py
│   └── experiments/         # Experimental features
│       ├── multi_agent_analyzer.py
│       ├── rag_system.py
│       ├── evaluate.py
│       └── ...
├── backend/                 # FastAPI server
│   ├── main.py
│   ├── routers/             # API endpoints
│   └── services/            # Business logic & crawlers
├── frontend/                # React + Vite dashboard
│   └── src/
├── docs/                    # Documentation
├── main.py                  # CLI entry point (Kaggle)
└── analyze_csv.py           # CLI entry point (custom CSV)
```

## Development Commands

### Setup
```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
# Create .env file with: OPENAI_API_KEY=your_key_here
```

### Running the Web App
```bash
# Backend
uvicorn backend.main:app --reload

# Frontend
cd frontend && npm run dev
```

### Running CLI Analysis
```bash
python main.py                              # Kaggle dataset
python analyze_csv.py <path_to_csv_file>    # Custom CSV
```

### Testing
```bash
# Python tests (pytest)
pytest -v

# Frontend tests (vitest)
cd frontend && npm test
```

## Git Branch & Commit Convention

### Branch Naming
항상 `main`에서 새 브랜치를 만들어 작업하고, main에 직접 커밋하지 않는다.

| Prefix | 용도 | 예시 |
|--------|------|------|
| `feat/` | 새 기능 추가 | `feat/add-crawling` |
| `fix/` | 버그 수정 | `fix/nan-serialization` |
| `refactor/` | 리팩터링 (동작 변경 없음) | `refactor/folder-structure` |
| `test/` | 테스트 추가/수정만 | `test/add-unit-tests` |
| `docs/` | 문서만 변경 | `docs/update-readme` |
| `chore/` | 빌드/설정/의존성 | `chore/upgrade-deps` |

### Commit Message
Conventional Commits 형식을 따른다:
```
<type>: <한국어 또는 영어 요약>
```
- type: `feat`, `fix`, `refactor`, `test`, `docs`, `chore`
- 한 줄 요약, 필요시 본문에 상세 설명

### Workflow
1. `main`에서 브랜치 생성: `git checkout -b <prefix>/<설명>`
2. 작업 후 커밋 & 푸시
3. GitHub PR 생성 → main으로 머지

## Architecture

### Module Responsibilities

**core/config.py**
- Environment configuration (OpenAI API key, paths)
- Analysis parameters: `NEGATIVE_RATING_THRESHOLD` (default: 3), `RECENT_PERIOD_DAYS` (30), `COMPARISON_PERIOD_DAYS` (60)
- LLM settings: `LLM_MODEL` (gpt-4o-mini), `LLM_TEMPERATURE` (0.3)

**core/data_loader.py** (`DataLoader` class)
- `load_reviews()`: Downloads and processes Kaggle Olist dataset
- `load_custom_csv()`: Processes custom CSV with Ratings/Reviews columns
- `filter_negative_reviews()`: Extracts reviews <= threshold rating
- `split_by_period()`: Divides data into recent/comparison periods

**core/analyzer.py** (`ReviewAnalyzer` class)
- `categorize_issues()`: Batches reviews and prompts GPT to categorize into issue types
- `get_top_issues()`: Counts category frequencies and extracts top N
- `detect_emerging_issues()`: Compares recent vs comparison period counts
- `generate_action_plan()`: Generates Korean-language actionable recommendations

### Key Design Patterns

**LLM Integration:** All OpenAI calls use `response_format={"type": "json_object"}` for structured output. Temperature set to 0.3.

**Time-Series Comparison:** Dataset max date is reference point. Recent period vs comparison period enables trend detection.

**Sampling Strategy:** `categorize_issues()` caps at 200 reviews per LLM call to avoid token limits.

## Configuration

Edit `core/config.py` to adjust:
- `NEGATIVE_RATING_THRESHOLD`: Rating cutoff for negative reviews (default: 3)
- `RECENT_PERIOD_DAYS`: Time window for "recent" analysis (default: 30)
- `COMPARISON_PERIOD_DAYS`: Total time window including comparison baseline (default: 60)
- `LLM_MODEL`: OpenAI model to use (default: "gpt-4o-mini")
- `LLM_TEMPERATURE`: Response randomness (default: 0.3)

## Important Notes

**API Costs:** Each run calls OpenAI API 3+ times. Default 200-sample batches with gpt-4o-mini cost ~$0.10-0.30 per run.

**Output Language:** Action plan recommendations are generated in Korean. Issue categories use English snake_case.

**Custom CSV:** Requires exact column names `Ratings` (numeric) and `Reviews` (text). Synthetic timestamps are generated for trend detection.
