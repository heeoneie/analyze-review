"""
분석 워크플로우 공통 함수
main.py, analyze_csv.py에서 사용하는 분석 파이프라인 공통 로직
"""

from core.report_utils import print_emerging_issues, print_top_issues
from core.utils.cli_helpers import print_section


def split_by_period(negative_df, loader):
    """Split reviews into recent and comparison periods."""
    print_section("Step 3: Splitting Data by Time Period")
    return loader.split_by_period(negative_df)


def analyze_periods(analyzer, recent_df, comparison_df, allow_empty_comparison=False):
    """Analyze recent and comparison reviews."""
    print_section("Step 4: Analyzing Recent Reviews")
    print(f"Processing {len(recent_df)} recent negative reviews...")
    print("(This may take a few minutes...)")

    recent_reviews = recent_df['review_text'].dropna().tolist()
    recent_categorization = analyzer.categorize_issues(recent_reviews)

    print_section("Step 5: Analyzing Comparison Period Reviews")
    print(f"Processing {len(comparison_df)} comparison period negative reviews...")

    comparison_reviews = comparison_df['review_text'].dropna().tolist()
    if allow_empty_comparison and not comparison_reviews:
        print("Not enough data in comparison period, using empty categorization")
        comparison_categorization = {'categories': []}
    else:
        comparison_categorization = analyzer.categorize_issues(comparison_reviews)

    return recent_categorization, comparison_categorization


def summarize_results(analyzer, recent_categorization, comparison_categorization):
    """Summarize top and emerging issues."""
    print_section("Step 6: Identifying Top 3 Issues")
    top_issues = analyzer.get_top_issues(recent_categorization, top_n=3)

    print_top_issues(
        top_issues,
        header="[TOP 3 문제점 (부정 리뷰 기준)]",
        count_format="   빈도: {count}회 ({percentage}%)",
        examples_label="   예시:",
    )

    print_section("Step 7: Detecting Emerging Issues")
    emerging_issues = analyzer.detect_emerging_issues(
        recent_categorization,
        comparison_categorization,
    )

    print_emerging_issues(
        emerging_issues,
        header="[최근 급증한 이슈]",
        empty_message="[OK] 최근 급증한 이슈 없음 (안정적 상태)",
        increase_format="   증가율: +{increase_rate}%",
        comparison_format="   이전: {comparison_count}회 → 최근: {recent_count}회",
    )

    return top_issues, emerging_issues


def generate_and_print_action_plan(analyzer, top_issues, emerging_issues):
    """Generate action plan and print recommendations."""
    print_section("Step 8: Generating Action Plan")
    print("AI가 개선 액션을 생성하는 중...")
    recommendations = analyzer.generate_action_plan(top_issues, emerging_issues)

    print("\n[개선 액션 제안]\n")
    for i, rec in enumerate(recommendations, 1):
        print(f"{i}. {rec}")

    return recommendations
