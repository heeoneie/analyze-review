"""리뷰 맞춤 답변 생성 모듈

부정 리뷰에 대해 매크로가 아닌 진심 어린 맞춤 답변을 LLM으로 생성한다.
"""

import logging

from core.utils.json_utils import extract_json_from_text
from core.utils.openai_client import call_openai_json, get_client

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = (
    "당신은 이커머스 고객 서비스 전문가입니다. "
    "불만 리뷰에 대해 진심 어린 맞춤 답변을 작성합니다. "
    "매크로나 템플릿 같은 답변은 절대 금지입니다."
)

REPLY_BATCH_SIZE = 10


def _build_single_prompt(review_text: str, rating: int, category: str | None = None) -> str:
    category_line = f"\n이 리뷰의 불만 카테고리: {category}" if category else ""
    return f"""아래 고객 리뷰에 대한 판매자 답변을 작성하세요.

## 고객 리뷰 (평점: {rating}점)
{review_text}
{category_line}

## 금지 표현 (매크로/템플릿)
- "불편을 드려 죄송합니다"
- "빠른 시일 내 조치하겠습니다"
- "소중한 의견 감사합니다"
- "이용에 불편을 드려"
- 위와 유사한 형식적/반복적 표현 일체

## 답변 작성 규칙
1. 고객이 쓴 구체적 단어를 답변에 반영하세요 (예: 고객이 "곰팡이"라 썼으면 "곰팡이 문제"로 언급)
2. 공감 → 구체적 사과 → 해결 방안 순서로 구성
3. 해결 방안은 실행 가능하고 구체적이어야 함 (교환, 환불, 보상 등)
4. 한국어 존댓말, 비즈니스 톤 유지
5. 150~250자 내외

## 출력 형식 (JSON)
{{
  "reply": "답변 텍스트",
  "tone": "답변의 어조 요약 (예: 공감+사과+교환안내)",
  "key_points_addressed": ["답변에서 다룬 구체적 불만 포인트"],
  "suggested_action": "권장 후속 조치 (예: 1:1 문의 유도, 교환 접수)"
}}"""


def _build_batch_prompt(reviews: list[dict]) -> str:
    reviews_text = ""
    for i, r in enumerate(reviews, 1):
        cat = f" [카테고리: {r['category']}]" if r.get("category") else ""
        reviews_text += f"\n### 리뷰 {i} (평점: {r['rating']}점){cat}\n{r['review_text']}\n"

    return f"""아래 {len(reviews)}개의 부정 리뷰 각각에 대한 판매자 맞춤 답변을 작성하세요.

{reviews_text}

## 금지 표현 (매크로/템플릿)
- "불편을 드려 죄송합니다", "빠른 시일 내 조치하겠습니다", "소중한 의견 감사합니다"
- 위와 유사한 형식적/반복적 표현 일체
- 모든 답변이 같은 문장으로 시작하는 것도 금지

## 답변 작성 규칙
1. 각 리뷰마다 고객이 쓴 구체적 단어를 반영한 개별 맞춤 답변
2. 공감 → 구체적 사과 → 해결 방안 순서
3. 해결 방안은 실행 가능하고 구체적 (교환, 환불, 보상 등)
4. 한국어 존댓말, 비즈니스 톤, 150~250자

## 출력 형식 (JSON)
{{
  "replies": [
    {{
      "review_index": 1,
      "reply": "답변 텍스트",
      "tone": "어조 요약",
      "key_points_addressed": ["불만 포인트"],
      "suggested_action": "후속 조치"
    }}
  ]
}}"""


class ReplyGenerator:
    def __init__(self):
        self.client = get_client()

    def generate_single(
        self, review_text: str, rating: int, category: str | None = None
    ) -> dict:
        """단일 리뷰에 대한 맞춤 답변 생성."""
        prompt = _build_single_prompt(review_text, rating, category)
        raw = call_openai_json(self.client, prompt, system_prompt=SYSTEM_PROMPT)

        parsed = extract_json_from_text(raw)
        if not parsed or "reply" not in parsed:
            logger.warning("답변 생성 JSON 파싱 실패, raw: %s", raw[:200])
            return {"reply": raw, "tone": "", "key_points_addressed": [], "suggested_action": ""}

        return parsed

    def generate_batch(self, reviews: list[dict]) -> list[dict]:
        """다건 리뷰 답변 일괄 생성. REPLY_BATCH_SIZE씩 묶어 호출."""
        all_replies = []

        for start in range(0, len(reviews), REPLY_BATCH_SIZE):
            chunk = reviews[start:start + REPLY_BATCH_SIZE]
            prompt = _build_batch_prompt(chunk)
            raw = call_openai_json(self.client, prompt, system_prompt=SYSTEM_PROMPT)

            parsed = extract_json_from_text(raw)
            if parsed and "replies" in parsed:
                normalized = []
                for reply_data in parsed["replies"]:
                    reply_data["review_index"] = start + reply_data.get("review_index", 1)
                    normalized.append(reply_data)
                normalized.sort(key=lambda r: r["review_index"])
                all_replies.extend(normalized)
            else:
                logger.warning("일괄 답변 생성 파싱 실패, chunk %d~%d", start, start + len(chunk))

        return all_replies
