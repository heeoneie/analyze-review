"""
E-commerce Review Analysis PoC - Custom CSV Version
커스텀 CSV 파일을 분석하여:
1. 부정 리뷰 기준 TOP 3 문제점 도출
2. 최근 기간 급증한 이슈 탐지
3. 개선 액션 제안 생성
"""

import os
import sys

from core.analyzer import ReviewAnalyzer
from core.data_loader import DataLoader
from core.utils.analysis_workflow import (
    analyze_periods,
    generate_and_print_action_plan,
    split_by_period,
    summarize_results,
)
from core.utils.cli_helpers import (
    filter_and_check_negative,
    print_analysis_complete,
    print_section,
    require_openai_key,
)


def validate_csv_path():
    """Validate CLI args and return the CSV path."""
    if len(sys.argv) < 2:
        print("Usage: python analyze_csv.py <path_to_csv_file>")
        print("\nExample:")
        print("  python analyze_csv.py APPLE_iPhone_SE.csv")
        sys.exit(1)
    return sys.argv[1]


def load_reviews(csv_path, loader):
    """Load reviews from custom CSV file."""
    if not os.path.exists(csv_path):
        print(f"\n[Error] File not found: {csv_path}")
        sys.exit(1)

    print_section("E-commerce Review Analysis PoC - Custom CSV")
    print_section("Step 1: Loading Data")

    try:
        df = loader.load_custom_csv(csv_path)
    except Exception as e:  # pylint: disable=broad-except
        print(f"\n[Error] Error loading data: {e}")
        sys.exit(1)
    return df


def main():
    csv_path = validate_csv_path()
    require_openai_key()

    loader = DataLoader()
    analyzer = ReviewAnalyzer()

    df = load_reviews(csv_path, loader)
    negative_df = filter_and_check_negative(loader, df)
    recent_df, comparison_df = split_by_period(negative_df, loader)
    recent_categorization, comparison_categorization = analyze_periods(
        analyzer, recent_df, comparison_df, allow_empty_comparison=True
    )
    top_issues, emerging_issues = summarize_results(
        analyzer, recent_categorization, comparison_categorization
    )

    generate_and_print_action_plan(analyzer, top_issues, emerging_issues)
    print_analysis_complete(df, negative_df, f"분석 파일: {csv_path}")


if __name__ == "__main__":
    main()
