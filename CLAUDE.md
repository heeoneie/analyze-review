# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is an **E-commerce Review Analysis PoC** that uses LLM (GPT-4o-mini) to analyze customer reviews and automatically extract:
1. Top 3 most frequent issues from negative reviews
2. Emerging issues showing significant increase trends
3. Actionable business recommendations

The system processes review text through OpenAI's API to categorize problems, identify patterns, and generate Korean-language improvement suggestions for e-commerce operations.

## Development Commands

### Setup
```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Configure environment
# Create .env file with: OPENAI_API_KEY=your_key_here
```

### Running the Analysis

**Main workflow (Kaggle dataset):**
```bash
python main.py
```
- First run will download Olist Brazilian E-commerce dataset from Kaggle
- Requires Kaggle API credentials configured (`~/.kaggle/kaggle.json`)

**Custom CSV analysis:**
```bash
python analyze_csv.py <path_to_csv_file>
```
- CSV must have `Ratings` and `Reviews` columns
- Example: `python analyze_csv.py APPLE_iPhone_SE.csv`

### Testing
No test suite currently implemented (this is a PoC).

## Architecture

### Core Data Flow
```
DataLoader → ReviewAnalyzer → Output
    ↓            ↓              ↓
  Filter      Categorize    Format
  Split       Detect         Display
              Generate
```

### Module Responsibilities

**config.py**
- Environment configuration (OpenAI API key, paths)
- Analysis parameters: `NEGATIVE_RATING_THRESHOLD` (default: 3), `RECENT_PERIOD_DAYS` (30), `COMPARISON_PERIOD_DAYS` (60)
- LLM settings: `LLM_MODEL` (gpt-4o-mini), `LLM_TEMPERATURE` (0.3)

**data_loader.py** (`DataLoader` class)
- Dual data source support:
  - `load_reviews()`: Downloads and processes Kaggle Olist dataset (merges reviews + orders for timestamps)
  - `load_custom_csv()`: Processes custom CSV with Ratings/Reviews columns (generates synthetic timestamps)
- Time-based filtering:
  - `filter_negative_reviews()`: Extracts reviews ≤ threshold rating
  - `split_by_period()`: Divides data into recent period and comparison period for trend detection

**analyzer.py** (`ReviewAnalyzer` class)
- LLM-powered analysis using OpenAI API with JSON mode:
  - `categorize_issues()`: Batches reviews (default 200 samples) and prompts GPT to categorize each into issue types (delivery_delay, wrong_item, poor_quality, etc.)
  - `get_top_issues()`: Counts category frequencies and extracts top N with examples
  - `detect_emerging_issues()`: Compares recent vs comparison period counts to identify surges (≥20% increase)
  - `generate_action_plan()`: Prompts GPT to create 3 Korean-language actionable recommendations

**main.py**
- Orchestrates full analysis pipeline for Kaggle dataset
- 8-step workflow: load → filter → split → analyze recent → analyze comparison → top issues → emerging issues → action plan

**analyze_csv.py**
- Same pipeline as main.py but for custom CSV files
- Takes CSV path as CLI argument
- Handles edge cases (no comparison data, missing reviews)

### Key Design Patterns

**LLM Integration Pattern:**
- All OpenAI calls use `response_format={"type": "json_object"}` for structured output
- System prompts establish domain expertise ("e-commerce feedback analyst", "business consultant")
- User prompts include data + format specification + output requirements
- Temperature set to 0.3 for consistent categorization

**Time-Series Comparison:**
- Dataset max date is reference point (not current date)
- Recent period: last N days from max date
- Comparison period: previous M-N days before recent period
- Enables trend detection even on historical datasets

**Sampling Strategy:**
- `categorize_issues()` caps at 200 reviews per LLM call to avoid token limits
- Trades complete coverage for cost efficiency (this is a PoC)

## Configuration Customization

Edit `config.py` to adjust:
- `NEGATIVE_RATING_THRESHOLD`: Rating cutoff for negative reviews (default: 3)
- `RECENT_PERIOD_DAYS`: Time window for "recent" analysis (default: 30)
- `COMPARISON_PERIOD_DAYS`: Total time window including comparison baseline (default: 60)
- `LLM_MODEL`: OpenAI model to use (default: "gpt-4o-mini")
- `LLM_TEMPERATURE`: Response randomness (default: 0.3)

## Important Notes

**Data Requirements:**
- Kaggle mode: Expects `olist_order_reviews_dataset.csv` and `olist_orders_dataset.csv` with standard Olist schema
- Custom CSV mode: Requires exact column names `Ratings` (numeric) and `Reviews` (text)

**API Costs:**
- Each run calls OpenAI API 3+ times (2 categorizations + 1 action plan generation)
- Default 200-sample batches with gpt-4o-mini cost ~$0.10-0.30 per run
- Adjust sample size in `analyzer.py:12` to control costs vs coverage

**Output Language:**
- Action plan recommendations are generated in Korean (`analyzer.py:151`)
- Issue categories use English snake_case for consistency
- Terminal output mixes Korean labels with English data

**Synthetic Timestamp Caveat:**
- Custom CSV mode generates fake timestamps (spreads data over 60 days from current date)
- Trend detection on custom CSVs is illustrative only, not based on real time data
