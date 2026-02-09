# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is an **E-commerce Review Analysis PoC** that uses LLM (GPT-4o-mini) to analyze customer reviews and automatically extract:
1. Top 3 most frequent issues from negative reviews
2. Emerging issues showing significant increase trends
3. Actionable business recommendations

The system processes review text through OpenAI's API to categorize problems, identify patterns, and generate Korean-language improvement suggestions for e-commerce operations.

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
No test suite currently implemented (this is a PoC).

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
