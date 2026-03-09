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
        "당신은 이커머스 플랫폼의 고객 리뷰를 분석하는 전문가입니다.\n\n"
        f"아래는 {review_count}개의 부정적 고객 리뷰 (별점 3점 이하)입니다.\n\n"
        "작업 지침:\n"
        "1. 모든 리뷰를 주의 깊게 읽으세요\n"
        "2. 주요 문제 카테고리를 식별하세요 (예: 배송 문제, 품질 불량, "
        "오배송, 포장 불량, 고객 서비스 등)\n"
        "3. 각 리뷰에 하나의 주요 문제 카테고리를 지정하세요\n\n"
        "리뷰 목록:\n"
        f"{reviews_text}\n\n"
        "출력 형식 (JSON):\n"
        "{\n"
        '  "categories": [\n'
        "    {\n"
        '      "review_number": 1,\n'
        '      "category": "delivery_delay",\n'
        '      "brief_issue": "택배가 2주 늦게 도착함"\n'
        "    },\n"
        "    ...\n"
        "  ]\n"
        "}\n\n"
        "IMPORTANT RULES:\n"
        "- category는 반드시 아래 영어 키 중 하나를 사용하세요:\n"
        "  delivery_delay, wrong_item, poor_quality, damaged_packaging, "
        "size_issue, missing_parts, not_as_described, customer_service, "
        "price_issue, overheating, battery_issue, network_issue, "
        "display_issue, software_issue, sound_issue, positive_review, other\n"
        "- brief_issue는 반드시 한국어로 작성하세요 (리뷰가 영어여도 한국어로 번역)\n"
        "- 위 목록에 정확히 맞는 카테고리가 없으면 가장 가까운 것을 선택하세요\n"
    )
