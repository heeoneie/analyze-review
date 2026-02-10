"""카테고리별 답변 품질 가이드 모듈

주요 불만 카테고리별 답변 톤, 구조, 필수 포인트, 좋은/나쁜 예시를 제공한다.
미등록 카테고리에 대해서는 LLM으로 가이드를 자동 생성한다.
"""

import logging

from core.utils.json_utils import extract_json_from_text
from core.utils.openai_client import call_openai_json, get_client

logger = logging.getLogger(__name__)

# ── 정적 지식 베이스 ────────────────────────────────────────

GUIDE_DB: dict[str, dict] = {
    "배송 지연": {
        "tone": "공감 + 사과 + 구체적 해결",
        "structure": [
            "배송 지연 상황에 대한 진심 어린 공감",
            "지연 원인 간단 설명 (물류 사정 등)",
            "구체적 해결 방안 (배송 조회, 보상 등)",
        ],
        "must_address": ["예상 배송일 안내", "추적 방법 안내", "보상/할인 제안"],
        "good_example": "주문하신 상품이 아직 도착하지 않아 정말 답답하셨을 것 같습니다. "
        "현재 물류센터에서 출고 지연이 발생하여, 내일 중 배송될 예정입니다. "
        "불편하신 점에 대해 5% 할인 쿠폰을 발급해드렸으니 확인 부탁드립니다.",
        "bad_example": "불편을 드려 죄송합니다. 빠른 시일 내 배송될 수 있도록 최선을 다하겠습니다.",
    },
    "품질 불량": {
        "tone": "즉시 사과 + 책임 인정 + 신속 교환",
        "structure": [
            "불량 제품을 받으신 것에 대한 즉각적 사과",
            "고객이 언급한 구체적 문제 인용",
            "교환/환불/보상 중 선택지 제시",
        ],
        "must_address": ["불량 내용 구체적 언급", "교환 또는 환불 절차 안내", "품질 관리 개선 약속"],
        "good_example": "받으신 제품에서 스크래치가 발견되었다니 정말 죄송합니다. "
        "바로 새 제품으로 교환 또는 전액 환불 처리해드리겠습니다. "
        "1:1 채팅으로 연락주시면 가장 빠르게 도와드리겠습니다.",
        "bad_example": "소중한 의견 감사합니다. 품질 관리에 더욱 힘쓰겠습니다.",
    },
    "상품 불일치": {
        "tone": "당혹감 공감 + 사과 + 즉시 조치",
        "structure": [
            "기대와 다른 상품을 받으신 데 대한 공감",
            "어떤 부분이 다른지 확인 요청",
            "교환/반품 절차 구체적 안내",
        ],
        "must_address": ["사진/상세 설명과 차이점 인정", "반품 비용 판매자 부담", "정확한 교환 절차"],
        "good_example": "상품 이미지와 실제 제품이 달라 당황하셨을 것 같습니다. "
        "색상이 다르게 보이신 거라면 즉시 반품 접수 도와드리겠습니다. "
        "반품 택배비는 저희가 부담합니다.",
        "bad_example": "이용에 불편을 드려 죄송합니다. 교환/반품 신청해주시면 처리해드리겠습니다.",
    },
    "고객 서비스": {
        "tone": "깊은 사과 + 문제 인정 + 재발 방지",
        "structure": [
            "불쾌한 경험에 대한 깊은 사과",
            "해당 상담원/부서 확인 의지 표명",
            "직접 연락처 제공 또는 상위 담당자 연결",
        ],
        "must_address": ["불쾌한 경험 인정", "직접 해결 의지", "재발 방지 약속"],
        "good_example": "상담 과정에서 불쾌한 경험을 하셨다니 정말 죄송합니다. "
        "해당 내용을 확인하여 내부 교육에 반영하겠습니다. "
        "제가 직접 도와드리겠으니 010-XXXX-XXXX로 연락 부탁드립니다.",
        "bad_example": "고객님의 소중한 의견 감사드립니다. 더 나은 서비스를 위해 노력하겠습니다.",
    },
    "가격 불만": {
        "tone": "이해 + 가치 설명 + 혜택 안내",
        "structure": [
            "가격에 대한 부담 공감",
            "제품 가치/차별점 구체적 설명",
            "할인/적립/쿠폰 등 혜택 안내",
        ],
        "must_address": ["가격 대비 가치 설명", "진행 중인 프로모션 안내", "적립금/쿠폰 혜택"],
        "good_example": "가격이 기대보다 높으셨군요. 저희 제품은 국내산 원료만 사용하여 "
        "가격이 다소 높은 편입니다. 현재 재구매 고객님께 15% 할인 쿠폰을 "
        "드리고 있으니 활용해보시기 바랍니다.",
        "bad_example": "죄송합니다. 가격 정책은 저희도 어쩔 수 없는 부분입니다.",
    },
    "포장 문제": {
        "tone": "공감 + 사과 + 개선 약속",
        "structure": [
            "포장 상태에 대한 실망 공감",
            "파손/부실 포장 상황 인정",
            "포장 개선 + 재발송/보상 제안",
        ],
        "must_address": ["포장 문제 인정", "제품 파손 여부 확인", "포장 개선 조치"],
        "good_example": "포장이 부실하여 상품이 훼손된 상태로 도착했다니 정말 죄송합니다. "
        "즉시 새 제품을 에어캡 이중 포장으로 재발송해드리겠습니다. "
        "포장 기준도 강화하여 재발을 방지하겠습니다.",
        "bad_example": "불편을 드려 죄송합니다. 포장에 더 신경 쓰도록 하겠습니다.",
    },
}

# ── LLM 폴백 가이드 생성 ─────────────────────────────────────

_LLM_CACHE: dict[str, dict] = {}


def _generate_guide_via_llm(category: str) -> dict:
    """미등록 카테고리에 대해 LLM으로 가이드 생성 후 캐시."""
    if category in _LLM_CACHE:
        return _LLM_CACHE[category]

    prompt = f"""이커머스 리뷰 답변 전문가로서, 아래 불만 카테고리에 대한 답변 작성 가이드를 JSON으로 작성하세요.

카테고리: {category}

## 출력 형식
{{
  "tone": "권장 어조 (예: 공감+사과+해결)",
  "structure": ["답변 구조 1단계", "답변 구조 2단계", "답변 구조 3단계"],
  "must_address": ["반드시 다뤄야 할 포인트1", "포인트2", "포인트3"],
  "good_example": "좋은 답변 예시 (150~250자, 구체적)",
  "bad_example": "나쁜 답변 예시 (매크로/형식적 답변)"
}}"""

    try:
        client = get_client()
        raw = call_openai_json(client, prompt)
        parsed = extract_json_from_text(raw)
        if parsed and "tone" in parsed:
            _LLM_CACHE[category] = parsed
            return parsed
    except (RuntimeError, ValueError, KeyError):
        logger.exception("가이드 LLM 생성 실패: %s", category)

    return {
        "tone": "공감 + 사과 + 해결",
        "structure": ["고객 불만 공감", "구체적 사과", "해결 방안 제시"],
        "must_address": ["고객 언급 문제 반영", "구체적 조치 안내"],
        "good_example": "",
        "bad_example": "",
    }


# ── 공개 API ──────────────────────────────────────────────

def get_guide(category: str) -> dict:
    """카테고리에 해당하는 답변 가이드 반환.

    정적 DB에 있으면 즉시 반환, 없으면 LLM 생성 후 캐시.
    """
    if category in GUIDE_DB:
        return {"category": category, "source": "static", **GUIDE_DB[category]}

    generated = _generate_guide_via_llm(category)
    return {"category": category, "source": "generated", **generated}


def list_guides() -> list[dict]:
    """등록된 모든 정적 가이드 목록 반환."""
    return [
        {"category": cat, **guide}
        for cat, guide in GUIDE_DB.items()
    ]
