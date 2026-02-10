"""Prompt template helpers."""

# JSON output format for single review categorization
SINGLE_REVIEW_JSON_FORMAT = (
    "Output JSON:\n"
    "{\n"
    '  "category": "category_name",\n'
    '  "confidence": 0.9,\n'
    '  "reasoning": "brief explanation"\n'
    "}\n"
)


def format_reviews(sampled_reviews):
    return "\n---\n".join(
        [f"{i + 1}. {text[:500]}" for i, text in enumerate(sampled_reviews)]
    )


def build_zero_shot_prompt(reviews_text, review_count):
    return (
        "이커머스 플랫폼의 고객 리뷰를 분석합니다.\n\n"
        f"아래는 {review_count}개의 부정 리뷰입니다 (평점 3점 이하).\n\n"
        "작업:\n"
        "1. 모든 리뷰를 읽고\n"
        "2. 각 리뷰에 하나의 문제 카테고리를 배정하세요\n\n"
        "카테고리 이름 규칙:\n"
        "- 반드시 한국어 2~4글자로 작성 (예: 배송 지연, 품질 불량, 사이즈 불만)\n"
        "- 상품 특성에 맞는 구체적 카테고리 사용\n"
        "- brief_issue도 한국어로 작성\n\n"
        "리뷰:\n"
        f"{reviews_text}\n\n"
        "출력 형식 (JSON):\n"
        "{\n"
        '  "categories": [\n'
        "    {\n"
        '      "review_number": 1,\n'
        '      "category": "배송 지연",\n'
        '      "brief_issue": "주문 후 2주나 걸림"\n'
        "    },\n"
        "    ...\n"
        "  ]\n"
        "}\n"
    )
