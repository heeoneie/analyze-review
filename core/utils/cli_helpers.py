"""
CLI 공통 유틸리티 함수
main.py, analyze_csv.py 등에서 사용하는 공통 함수
"""

import sys

from core import config


def print_section(title):
    """Print a formatted section header"""
    print("\n" + "=" * 80)
    print(f"  {title}")
    print("=" * 80)


def require_openai_key():
    """Exit if OPENAI_API_KEY is missing."""
    if not config.OPENAI_API_KEY:
        print("\n[Error] OPENAI_API_KEY not found in .env file")
        print("Please create a .env file with your OpenAI API key:")
        print("  OPENAI_API_KEY=your_api_key_here")
        sys.exit(1)


def check_negative_reviews(negative_df):
    """Exit if no negative reviews found."""
    if len(negative_df) == 0:
        print("\n[Error] No negative reviews found. Cannot proceed with analysis.")
        sys.exit(1)


def filter_and_check_negative(loader, df):
    """Filter negative reviews and exit if none found."""
    print_section("Step 2: Filtering Negative Reviews")
    negative_df = loader.filter_negative_reviews(df)
    check_negative_reviews(negative_df)
    return negative_df


def print_analysis_complete(df, negative_df, extra_info=""):
    """Print analysis complete summary."""
    print_section("Analysis Complete")
    extra_line = f"\n{extra_info}" if extra_info else ""
    print(
        f"""
[OK] 분석 완료

총 리뷰 수: {len(df):,}
부정 리뷰 수: {len(negative_df):,}{extra_line}

이 분석 결과를 바탕으로 즉시 개선 작업을 시작할 수 있습니다.
    """
    )
