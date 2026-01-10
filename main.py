"""
E-commerce Review Analysis PoC
분석 목표:
1. 부정 리뷰 기준 TOP 3 문제점 도출
2. 최근 기간 급증한 이슈 탐지
3. 개선 액션 제안 생성
"""

import sys
from data_loader import DataLoader
from analyzer import ReviewAnalyzer


def print_section(title):
    """Print a formatted section header"""
    print("\n" + "=" * 80)
    print(f"  {title}")
    print("=" * 80)


def main():
    print_section("E-commerce Review Analysis PoC")

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
        df = loader.load_reviews()
    except Exception as e:
        print(f"\n❌ Error loading data: {e}")
        print("\nTip: Make sure you have Kaggle API configured properly.")
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
    comparison_categorization = analyzer.categorize_issues(comparison_reviews)

    # Step 6: Extract top issues
    print_section("Step 6: Identifying Top 3 Issues")
    top_issues = analyzer.get_top_issues(recent_categorization, top_n=3)

    print("\n📊 TOP 3 문제점 (부정 리뷰 기준):\n")
    for i, issue in enumerate(top_issues, 1):
        print(f"{i}. {issue['category'].replace('_', ' ').title()}")
        print(f"   빈도: {issue['count']}회 ({issue['percentage']}%)")
        print(f"   예시:")
        for example in issue['examples']:
            print(f"   - {example}")
        print()

    # Step 7: Detect emerging issues
    print_section("Step 7: Detecting Emerging Issues")
    emerging_issues = analyzer.detect_emerging_issues(
        recent_categorization,
        comparison_categorization
    )

    if emerging_issues:
        print("\n📈 최근 급증한 이슈:\n")
        for i, issue in enumerate(emerging_issues, 1):
            print(f"{i}. {issue['category'].replace('_', ' ').title()}")
            print(f"   증가율: +{issue['increase_rate']}%")
            print(f"   이전: {issue['comparison_count']}회 → 최근: {issue['recent_count']}회")
            print()
    else:
        print("\n✓ 최근 급증한 이슈 없음 (안정적 상태)")

    # Step 8: Generate action plan
    print_section("Step 8: Generating Action Plan")
    print("AI가 개선 액션을 생성하는 중...")

    recommendations = analyzer.generate_action_plan(top_issues, emerging_issues)

    print("\n💡 개선 액션 제안:\n")
    for i, rec in enumerate(recommendations, 1):
        print(f"{i}. {rec}")

    # Summary
    print_section("Analysis Complete")
    print(f"""
✓ 분석 완료

총 리뷰 수: {len(df):,}
부정 리뷰 수: {len(negative_df):,}
분석 기간: {df['created_at'].min().date()} ~ {df['created_at'].max().date()}

이 분석 결과를 바탕으로 즉시 개선 작업을 시작할 수 있습니다.
    """)


if __name__ == "__main__":
    main()
