# CLAUDE.md - Master AI Development Roadmap & Constraints

This file provides STRICT guidance to Claude Code (claude.ai/code) when working with code in this repository. Read this entirely before executing any prompt.

## 🎯 Business Direction & Identity

**OntoReview** — Litigation Prevention OS for K-Brands entering the US market ("Palantir for Reputation")

- **Target Event:** Amazon Hackathon (Mar 16) & YC Pitch (Mar 26) - **We have less than 13 days.**
- **Core Value:** Not just review analysis. We prove "Duty of Care" (Audit Logs) and calculate "Financial Risk" (Estimated Legal Loss via Case Law).
- **Target Audience:** K-Beauty / K-Food companies facing strict US Product Liability (PL) and Class Action lawsuits.

## ⚠️ STRICT AI CODING CONSTRAINTS (READ BEFORE CODING)

1. **NO OVER-ENGINEERING:** We are in a 13-day Hackathon Sprint. Do NOT build complex infrastructures (No Vector DBs like Chroma/Pinecone, No complex Auth, No broad web crawlers).
2. **THE B2B VALUE:** Every feature must highlight "Legal Exposure ($)" or "Compliance (Audit)".
3. **DO NOT RELY ON KAGGLE/CSV:** We are moving away from local CSVs. Focus on the Amazon pipeline and mock ingestion for the demo.
4. **TECH STACK:** React (Tailwind dark mode), FastAPI, SQLite (SQLAlchemy), GPT-4o-mini.

## 🗺️ THE 13-DAY HACKATHON SPRINT ROADMAP

### Phase 1 & 2: Legal Risk Engine & Micro-RAG 👈 [CURRENT STAGE]
- **Goal:** Upgrade from "Keyword Filter" to a mathematically calculable "Legal Risk Engine".
- **Tasks:** - Classify risks into specific legal categories (e.g., Product Liability, Regulatory Risk).
  - Calculate `overall_risk_score` using weighted severities.
  - Implement a scoring-based Micro-RAG using `backend/data/legal_cases.json` (US Precedents with integer USD loss values).
  - Expose `total_legal_exposure_usd` to the KPI dashboard.

### Phase 3: The Shield (Audit Log)
- **Goal:** Prove the company's "Duty of Care".
- **Tasks:** Build an append-only `audit_events` SQLite table and a dashboard view showing real-time scanning activity. Enable simple PDF export.

### Phase 4: End-to-End Demo Polish
- **Goal:** A flawless 3-minute demo flow.
- **Flow:** Amazon ASIN Ingestion -> Risk Detected -> US Precedent Matched -> $5M Loss Warned -> Playbook Generated -> Audit Logged.

---

## 💻 Development Commands

### Setup
```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
# Create .env file with: OPENAI_API_KEY=your_key_here
```

### Running the App
```bash
# Backend
uvicorn backend.main:app --reload

# Frontend
cd frontend && npm run dev
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