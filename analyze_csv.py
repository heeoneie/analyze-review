"""
E-commerce Review Analysis PoC - Custom CSV Version
커스텀 CSV 파일을 분석하여:
1. 부정 리뷰 기준 TOP 3 문제점 도출
2. 최근 기간 급증한 이슈 탐지
3. 개선 액션 제안 생성
"""

import sys
import os
from data_loader import DataLoader
from analyzer import ReviewAnalyzer
from report_utils import print_top_issues, print_emerging_issues


def print_section(title):
    """Print a formatted section header"""
    print("\n" + "=" * 80)
    print(f"  {title}")
    print("=" * 80)


def main():
    # Check for CSV file argument
    if len(sys.argv) < 2:
        print("Usage: python analyze_csv.py <path_to_csv_file>")
        print("\nExample:")
        print("  python analyze_csv.py APPLE_iPhone_SE.csv")
        sys.exit(1)

    csv_path = sys.argv[1]

    if not os.path.exists(csv_path):
        print(f"\n❌ Error: File not found: {csv_path}")
        sys.exit(1)

    print_section("E-commerce Review Analysis PoC - Custom CSV")

    # Check if OpenAI API key is set
    import config
    if not config.OPENAI_API_KEY:
        print("\n❌ Error: OPENAI_API_KEY not found in .env file")
        print("Please create a .env file with your OpenAI API key:")
        print("  OPENAI_API_KEY=your_api_key_here")
        sys.exit(1)

    # Initialize components
    loader = DataLoader()
    analyzer = ReviewAnalyzer()

    # Step 1: Load data
    print_section("Step 1: Loading Data")
    try:
        df = loader.load_custom_csv(csv_path)
    except Exception as e:  # pylint: disable=broad-except
        # Data loading can fail for multiple IO or parsing reasons.
        print(f"\n❌ Error loading data: {e}")
        sys.exit(1)

    # Step 2: Filter negative reviews
    print_section("Step 2: Filtering Negative Reviews")
    negative_df = loader.filter_negative_reviews(df)

    if len(negative_df) == 0:
        print("\n❌ No negative reviews found. Cannot proceed with analysis.")
        sys.exit(1)

    # Step 3: Split by time period
    print_section("Step 3: Splitting Data by Time Period")
    recent_df, comparison_df = loader.split_by_period(negative_df)

    # Step 4: Analyze recent reviews
    print_section("Step 4: Analyzing Recent Reviews")
    print(f"Processing {len(recent_df)} recent negative reviews...")
    print("(This may take a few minutes...)")

    recent_reviews = recent_df['review_text'].dropna().tolist()
    recent_categorization = analyzer.categorize_issues(recent_reviews)

    # Step 5: Analyze comparison period reviews
    print_section("Step 5: Analyzing Comparison Period Reviews")
    print(f"Processing {len(comparison_df)} comparison period negative reviews...")

    comparison_reviews = comparison_df['review_text'].dropna().tolist()
    if len(comparison_reviews) > 0:
        comparison_categorization = analyzer.categorize_issues(comparison_reviews)
    else:
        print("Not enough data in comparison period, using empty categorization")
        comparison_categorization = {'categories': []}

    # Step 6: Extract top issues
    print_section("Step 6: Identifying Top 3 Issues")
    top_issues = analyzer.get_top_issues(recent_categorization, top_n=3)

    print_top_issues(
        top_issues,
        header="[TOP 3 문제점 (부정 리뷰 기준)]",
        count_format="   빈도: {count}회 ({percentage}%)",
        examples_label="   예시:"
    )

    # Step 7: Detect emerging issues
    print_section("Step 7: Detecting Emerging Issues")
    emerging_issues = analyzer.detect_emerging_issues(
        recent_categorization,
        comparison_categorization
    )

    print_emerging_issues(
        emerging_issues,
        header="[최근 급증한 이슈]",
        empty_message="[OK] 최근 급증한 이슈 없음 (안정적 상태)",
        increase_format="   증가율: +{increase_rate}%",
        comparison_format="   이전: {comparison_count}회 → 최근: {recent_count}회"
    )

    # Step 8: Generate action plan
    print_section("Step 8: Generating Action Plan")
    print("AI가 개선 액션을 생성하는 중...")

    recommendations = analyzer.generate_action_plan(top_issues, emerging_issues)

    print("\n[개선 액션 제안]\n")
    for i, rec in enumerate(recommendations, 1):
        print(f"{i}. {rec}")

    # Summary
    print_section("Analysis Complete")
    print(f"""
[OK] 분석 완료

총 리뷰 수: {len(df):,}
부정 리뷰 수: {len(negative_df):,}
분석 파일: {csv_path}

이 분석 결과를 바탕으로 즉시 개선 작업을 시작할 수 있습니다.
    """)


if __name__ == "__main__":
    main()
