from collections import Counter

from analyzer import ReviewAnalyzer
from data_loader import DataLoader


def run_full_analysis(csv_path: str, rating_threshold: int = 3) -> dict:
    loader = DataLoader()
    analyzer = ReviewAnalyzer()

    # Step 1: 데이터 로드
    df = loader.load_custom_csv(csv_path)

    # 평점 분포
    rating_dist = df["rating"].value_counts().sort_index().to_dict()
    rating_dist = {str(int(k)): int(v) for k, v in rating_dist.items()}

    # Step 2: 부정 리뷰 필터링 (사용자 설정 기준)
    negative_df = loader.filter_negative_reviews(df, threshold=rating_threshold)

    stats = {
        "total_reviews": len(df),
        "negative_reviews": len(negative_df),
        "negative_ratio": round(len(negative_df) / max(len(df), 1) * 100, 1),
        "rating_distribution": rating_dist,
        "rating_threshold": rating_threshold,
    }

    if len(negative_df) == 0:
        return {
            "stats": stats,
            "top_issues": [],
            "all_categories": {},
            "emerging_issues": [],
            "recommendations": ["부정 리뷰가 없습니다."],
        }

    # Step 3: 기간 분할
    recent_df, comparison_df = loader.split_by_period(negative_df)

    # Step 4-5: LLM 분류
    recent_reviews = recent_df["review_text"].dropna().tolist()
    if not recent_reviews:
        recent_reviews = negative_df["review_text"].dropna().tolist()

    recent_categorization = analyzer.categorize_issues(recent_reviews)

    comparison_reviews = comparison_df["review_text"].dropna().tolist()
    if comparison_reviews:
        comparison_categorization = analyzer.categorize_issues(comparison_reviews)
    else:
        comparison_categorization = {"categories": []}

    # Step 6: Top 이슈
    top_issues = analyzer.get_top_issues(recent_categorization, top_n=3)

    # 전체 카테고리 카운트
    all_cats = [item["category"] for item in recent_categorization.get("categories", [])]
    all_category_counts = dict(Counter(all_cats))

    # Step 7: 급증 이슈
    emerging_issues = analyzer.detect_emerging_issues(
        recent_categorization, comparison_categorization
    )

    # Step 8: 액션 플랜
    recommendations = analyzer.generate_action_plan(top_issues, emerging_issues)

    return {
        "stats": stats,
        "top_issues": top_issues,
        "all_categories": all_category_counts,
        "emerging_issues": emerging_issues,
        "recommendations": recommendations,
    }
