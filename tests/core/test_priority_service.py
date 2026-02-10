"""priority_service 스코어링 로직 테스트"""

from datetime import datetime, timedelta

from backend.services.priority_service import (
    _keyword_score,
    _length_score,
    _rating_score,
    _recency_score,
    compute_priority,
    score_and_sort,
)

# ── 개별 스코어 함수 테스트 ──────────────────────────────────


class TestRatingScore:
    def test_one_star_gets_max(self):
        assert _rating_score(1) == 40

    def test_two_star(self):
        assert _rating_score(2) == 25

    def test_three_star(self):
        assert _rating_score(3) == 10

    def test_four_star_is_zero(self):
        assert _rating_score(4) == 0


class TestLengthScore:
    def test_long_review(self):
        assert _length_score("가" * 200) == 20

    def test_medium_review(self):
        assert _length_score("가" * 100) == 12

    def test_short_review(self):
        assert _length_score("가" * 50) == 6

    def test_very_short_review(self):
        assert _length_score("짧음") == 2

    def test_empty_review(self):
        assert _length_score("") == 2


class TestKeywordScore:
    def test_high_severity_keyword(self):
        assert _keyword_score("환불해주세요 제품이 불량입니다") == 25

    def test_medium_severity_keyword(self):
        assert _keyword_score("배송이 너무 늦었어요 실망입니다") == 15

    def test_no_severity_keyword(self):
        assert _keyword_score("별로였어요") == 5


class TestRecencyScore:
    def test_within_24h(self):
        recent = (datetime.now() - timedelta(hours=12)).isoformat()
        assert _recency_score(recent) == 15

    def test_within_3_days(self):
        date = (datetime.now() - timedelta(days=2)).isoformat()
        assert _recency_score(date) == 10

    def test_within_7_days(self):
        date = (datetime.now() - timedelta(days=5)).isoformat()
        assert _recency_score(date) == 5

    def test_old_review(self):
        date = (datetime.now() - timedelta(days=30)).isoformat()
        assert _recency_score(date) == 2

    def test_no_date(self):
        assert _recency_score(None) == 8

    def test_invalid_date(self):
        assert _recency_score("not-a-date") == 8


# ── compute_priority 통합 테스트 ─────────────────────────────


class TestComputePriority:
    def test_returns_original_fields(self):
        review = {"Ratings": 1, "Reviews": "불량 제품입니다"}
        result = compute_priority(review)
        assert result["Ratings"] == 1
        assert result["Reviews"] == "불량 제품입니다"

    def test_adds_priority_field(self):
        review = {"Ratings": 1, "Reviews": "불량 제품입니다"}
        result = compute_priority(review)
        assert "priority" in result
        assert "score" in result["priority"]
        assert "level" in result["priority"]
        assert "factors" in result["priority"]

    def test_critical_review(self):
        """1점 + 긴 리뷰 + 심각 키워드 → critical"""
        review = {
            "Ratings": 1,
            "Reviews": "환불 요청합니다. " + "불량 제품을 받았습니다. " * 20,
            "created_at": datetime.now().isoformat(),
        }
        result = compute_priority(review)
        assert result["priority"]["level"] == "critical"
        assert result["priority"]["score"] >= 80

    def test_low_review(self):
        """3점 + 짧은 리뷰 + 키워드 없음 → low"""
        review = {"Ratings": 3, "Reviews": "별로"}
        result = compute_priority(review)
        assert result["priority"]["level"] == "low"
        assert result["priority"]["score"] < 40

    def test_missing_fields_graceful(self):
        """필드 누락 시 에러 없이 기본값 사용"""
        result = compute_priority({})
        assert "priority" in result
        assert result["priority"]["score"] >= 0


# ── score_and_sort 테스트 ────────────────────────────────────


class TestScoreAndSort:
    def test_sorted_by_score_descending(self):
        reviews = [
            {"Ratings": 3, "Reviews": "괜찮아요"},
            {"Ratings": 1, "Reviews": "환불 요청합니다 불량 제품"},
            {"Ratings": 2, "Reviews": "실망입니다"},
        ]
        result = score_and_sort(reviews)
        scores = [r["priority"]["score"] for r in result]
        assert scores == sorted(scores, reverse=True)

    def test_empty_list(self):
        assert score_and_sort([]) == []

    def test_preserves_all_reviews(self):
        reviews = [
            {"Ratings": 1, "Reviews": "나쁨"},
            {"Ratings": 2, "Reviews": "별로"},
        ]
        result = score_and_sort(reviews)
        assert len(result) == 2
