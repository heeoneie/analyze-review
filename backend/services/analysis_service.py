from collections import Counter

from analyzer import ReviewAnalyzer
from data_loader import DataLoader


def _compute_stats(df, negative_df, rating_threshold):
    """통계 및 평점 분포 계산"""
    rating_dist = df["rating"].value_counts().sort_index().to_dict()
    rating_dist = {
        str(int(k)) if float(k) == int(k) else str(k): int(v)
        for k, v in rating_dist.items()
    }
    return {
        "total_reviews": len(df),
        "negative_reviews": len(negative_df),
        "negative_ratio": round(
            len(negative_df) / max(len(df), 1) * 100, 1
        ),
        "rating_distribution": rating_dist,
        "rating_threshold": rating_threshold,
    }


def _categorize_periods(loader, analyzer, negative_df):
    """기간별 LLM 분류 수행"""
    recent_df, comparison_df = loader.split_by_period(negative_df)

    recent_reviews = recent_df["review_text"].dropna().tolist()
    if not recent_reviews:
        recent_reviews = negative_df["review_text"].dropna().tolist()

    recent_cat = analyzer.categorize_issues(recent_reviews)

    comparison_reviews = comparison_df["review_text"].dropna().tolist()
    comparison_cat = (
        analyzer.categorize_issues(comparison_reviews)
        if comparison_reviews
        else {"categories": []}
    )

    return recent_cat, comparison_cat


def run_full_analysis(csv_path: str, rating_threshold: int = 3) -> dict:
    loader = DataLoader()
    analyzer = ReviewAnalyzer()

    df = loader.load_custom_csv(csv_path)
    negative_df = loader.filter_negative_reviews(
        df, threshold=rating_threshold
    )
    stats = _compute_stats(df, negative_df, rating_threshold)

    if len(negative_df) == 0:
        return {
            "stats": stats,
            "top_issues": [],
            "all_categories": {},
            "emerging_issues": [],
            "recommendations": ["부정 리뷰가 없습니다."],
        }

    recent_cat, comparison_cat = _categorize_periods(
        loader, analyzer, negative_df
    )

    top_issues = analyzer.get_top_issues(recent_cat, top_n=3)
    all_cats = [
        item["category"]
        for item in recent_cat.get("categories", [])
    ]
    emerging_issues = analyzer.detect_emerging_issues(
        recent_cat, comparison_cat
    )
    recommendations = analyzer.generate_action_plan(
        top_issues, emerging_issues
    )

    return {
        "stats": stats,
        "top_issues": top_issues,
        "all_categories": dict(Counter(all_cats)),
        "emerging_issues": emerging_issues,
        "recommendations": recommendations,
    }
