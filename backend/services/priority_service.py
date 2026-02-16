"""리뷰 우선순위 스코어링 서비스

LLM 호출 없이 로컬에서 별점/키워드/길이/최신성 기준으로
부정 리뷰의 대응 우선순위를 점수화한다.
"""

from datetime import datetime, timedelta, timezone

# 심각 키워드 (환불/결함/파손 등)
_KEYWORDS_HIGH = [
    "환불", "사기", "고장", "불량", "파손", "위험", "가짜",
    "거짓", "망가", "부러", "깨진", "찢어", "곰팡이",
]

# 중간 키워드 (실망/지연 등)
_KEYWORDS_MED = [
    "실망", "늦", "지연", "다름", "불만", "교환",
    "냄새", "얼룩", "흠집", "빠짐", "누락", "안 옴",
    "안옴", "오배송", "반품",
]


def _rating_score(rating: int) -> int:
    """별점 심각도 점수 (40점 만점)"""
    return {1: 40, 2: 25, 3: 10}.get(rating, 0)


def _length_score(text: str) -> int:
    """리뷰 길이/상세도 점수 (20점 만점)"""
    length = len(text)
    if length >= 200:
        return 20
    if length >= 100:
        return 12
    if length >= 50:
        return 6
    return 2


def _keyword_score(text: str) -> int:
    """키워드 심각도 점수 (25점 만점)"""
    text_lower = text.lower()
    if any(kw in text_lower for kw in _KEYWORDS_HIGH):
        return 25
    if any(kw in text_lower for kw in _KEYWORDS_MED):
        return 15
    return 5


def _recency_score(created_at: str | None) -> int:
    """최신성 점수 (15점 만점)"""
    if not created_at:
        return 8  # 날짜 정보 없으면 중간값

    try:
        dt = datetime.fromisoformat(str(created_at).replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        now = datetime.now(timezone.utc)
    except (ValueError, TypeError):
        return 8

    diff = now - dt
    if diff <= timedelta(days=1):
        return 15
    if diff <= timedelta(days=3):
        return 10
    if diff <= timedelta(days=7):
        return 5
    return 2


def _score_to_level(score: int) -> str:
    """점수를 레벨로 변환"""
    if score >= 80:
        return "critical"
    if score >= 60:
        return "high"
    if score >= 40:
        return "medium"
    return "low"


def compute_priority(review: dict) -> dict:
    """단일 리뷰의 우선순위 점수 계산.

    Args:
        review: {"Ratings": int, "Reviews": str, "created_at": str|None, ...}

    Returns:
        원본 리뷰 dict에 "priority" 필드가 추가된 dict.
        priority: {"score": int, "level": str,
                   "factors": {"rating": int, "length": int,
                               "keyword": int, "recency": int}}
    """
    text = str(review.get("Reviews", ""))
    try:
        rating = int(float(review.get("Ratings", 3)))
    except (ValueError, TypeError):
        rating = 3
    created_at = review.get("created_at")

    factors = {
        "rating": _rating_score(rating),
        "length": _length_score(text),
        "keyword": _keyword_score(text),
        "recency": _recency_score(created_at),
    }
    score = sum(factors.values())
    level = _score_to_level(score)

    return {
        **review,
        "priority": {
            "score": score,
            "level": level,
            "factors": factors,
        },
    }


def score_and_sort(reviews: list[dict]) -> list[dict]:
    """리뷰 리스트에 우선순위 점수를 부여하고 점수 내림차순 정렬.

    Args:
        reviews: [{"Ratings": int, "Reviews": str, ...}, ...]

    Returns:
        우선순위 점수가 추가된 리뷰 리스트 (점수 내림차순)
    """
    scored = [compute_priority(r) for r in reviews]
    scored.sort(key=lambda x: x["priority"]["score"], reverse=True)
    return scored
