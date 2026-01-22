"""
E-commerce Review Analysis PoC
분석 목표:
1. 부정 리뷰 기준 TOP 3 문제점 도출
2. 최근 기간 급증한 이슈 탐지
3. 개선 액션 제안 생성
"""

import sys

from analyzer import ReviewAnalyzer
from data_loader import DataLoader
from utils.analysis_workflow import (
    analyze_periods,
    generate_and_print_action_plan,
    split_by_period,
    summarize_results,
)
from utils.cli_helpers import (
    filter_and_check_negative,
    print_analysis_complete,
    print_section,
    require_openai_key,
)


def load_reviews(loader):
    """Load reviews from Kaggle dataset."""
    print_section("Step 1: Loading Data")
    try:
        df = loader.load_reviews()
    except Exception as e:  # pylint: disable=broad-except
        print(f"\n[Error] Error loading data: {e}")
        print("\nTip: Make sure you have Kaggle API configured properly.")
        sys.exit(1)
    return df


def main():
    print_section("E-commerce Review Analysis PoC")
    require_openai_key()

    loader = DataLoader()
    analyzer = ReviewAnalyzer()

    df = load_reviews(loader)
    negative_df = filter_and_check_negative(loader, df)
    recent_df, comparison_df = split_by_period(negative_df, loader)
    recent_categorization, comparison_categorization = analyze_periods(
        analyzer, recent_df, comparison_df
    )
    top_issues, emerging_issues = summarize_results(
        analyzer, recent_categorization, comparison_categorization
    )

    generate_and_print_action_plan(analyzer, top_issues, emerging_issues)
    date_range = f"분석 기간: {df['created_at'].min().date()} ~ {df['created_at'].max().date()}"
    print_analysis_complete(df, negative_df, date_range)


if __name__ == "__main__":
    main()
