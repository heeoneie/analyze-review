import logging
from collections import Counter

from backend.services.priority_service import score_and_sort
from backend.services.progress import update as update_progress
from core.analyzer import ReviewAnalyzer
from core.data_loader import DataLoader

logger = logging.getLogger(__name__)

MAX_REVIEW_SAMPLE = 200


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
    """기간별 LLM 분류 수행 (최대 200건 샘플링)"""
    update_progress("기간별 데이터 분할 중", 30)
    recent_df, comparison_df = loader.split_by_period(
        negative_df
    )

    recent_reviews = (
        recent_df["review_text"].dropna().tolist()
    )
    if not recent_reviews:
        logger.warning(
            "최근 기간 리뷰가 없어 emerging issues 감지가 "
            "제한됩니다."
        )

    update_progress("최근 리뷰 GPT 분류 중", 35)
    recent_cat = (
        analyzer.categorize_issues(
            recent_reviews[:MAX_REVIEW_SAMPLE]
        )
        if recent_reviews
        else {"categories": []}
    )

    update_progress("이전 리뷰 GPT 분류 중", 55)
    comparison_reviews = (
        comparison_df["review_text"].dropna().tolist()
    )
    comparison_cat = (
        analyzer.categorize_issues(
            comparison_reviews[:MAX_REVIEW_SAMPLE]
        )
        if comparison_reviews
        else {"categories": []}
    )

    return recent_cat, comparison_cat


def run_full_analysis(
    csv_path: str, rating_threshold: int = 3
) -> dict:
    loader = DataLoader()
    analyzer = ReviewAnalyzer()

    update_progress("데이터 로딩 중", 22)
    df = loader.load_custom_csv(csv_path)

    update_progress("부정 리뷰 필터링 중", 25)
    negative_df = loader.filter_negative_reviews(
        df, threshold=rating_threshold
    )
    stats = _compute_stats(df, negative_df, rating_threshold)

    if len(negative_df) == 0:
        update_progress("완료", 100)
        return {
            "stats": stats,
            "top_issues": [],
            "all_categories": {},
            "emerging_issues": [],
            "recommendations": ["부정 리뷰가 없습니다."],
            "priority_reviews": [],
        }

    recent_cat, comparison_cat = _categorize_periods(
        loader, analyzer, negative_df
    )

    update_progress("Top 이슈 분석 중", 75)
    top_issues = analyzer.get_top_issues(
        recent_cat, top_n=3
    )
    all_cats = [
        item["category"]
        for item in recent_cat.get("categories", [])
    ]

    update_progress("급증 이슈 탐지 중", 78)
    emerging_issues = analyzer.detect_emerging_issues(
        recent_cat, comparison_cat
    )

    update_progress("AI 개선 액션 생성 중", 80)
    recommendations = analyzer.generate_action_plan(
        top_issues, emerging_issues,
        categorization_result=recent_cat,
    )

    update_progress("우선순위 스코어링 중", 90)
    negative_reviews_raw = (
        negative_df.fillna("").rename(
            columns={"review_text": "Reviews", "rating": "Ratings"}
        ).to_dict(orient="records")
    )
    priority_reviews = score_and_sort(negative_reviews_raw)[:20]

    update_progress("완료", 100)
    return {
        "stats": stats,
        "top_issues": top_issues,
        "all_categories": dict(Counter(all_cats)),
        "emerging_issues": emerging_issues,
        "recommendations": recommendations,
        "priority_reviews": priority_reviews,
    }
