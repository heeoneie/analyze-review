"""리뷰 맞춤 답변 생성 모듈 (외식업 배달앱).

실제 매장(중식 배달) 리뷰 441건에서 확인된 문제를 푼다.

  - 별점 5점이 92%. 사과할 일이 없는 리뷰가 대부분이다.
  - 그런데 답변 첫 줄 상위 4개가 전부 같은 문장이고, 매장명으로 시작하는
    인사가 전체의 31%다. 자동으로 달고 있다는 게 티가 난다.
  - 리뷰 본문은 27%가 비어 있고, 있어도 "맛있어요" 한 줄이 흔하다.

그래서 긍정 리뷰 답변을 따로 만든다(`generate_positive`). 답변을 서로 다르게
만드는 재료는 (1) 주문한 메뉴와 (2) 매번 바꾸는 도입·끝맺음 방식 두 가지다.
생성 후에는 core.reply_text 로 금지 표현·매장명 시작·문장 중복을 기계적으로
검사하고, 걸리면 위반 내용을 알려 주며 다시 생성한다.

부정 리뷰 경로(`generate_single` / `generate_batch`)는 반환 형태를 그대로 두고
프롬프트 내용만 배달 음식 맥락으로 바꿨다.
"""

import logging
import random
from datetime import datetime

from core import config
from core.menu_profiles import (
    format_menu_block,
    format_store_menu,
    main_items,
    parse_menu,
    unordered_mentions,
)
from core.reply_text import (
    find_violations,
    first_sentence,
    last_sentence,
    opening_shape,
)
from core.utils.json_utils import extract_json_from_text
from core.utils.openai_client import call_openai_json, get_client

logger = logging.getLogger(__name__)

REPLY_BATCH_SIZE = 10
MAX_ATTEMPTS = 3

SYSTEM_PROMPT = (
    "당신은 배달앱에서 장사하는 중식당 사장님입니다. "
    "음식이나 배달에 불만을 남긴 손님에게 사장님이 직접 답글을 답니다. "
    "변명하지 않고, 무엇이 잘못됐는지 그대로 짚고, 다음 주문에서 어떻게 하겠다는 "
    "구체적인 이야기를 합니다. 매크로나 템플릿 같은 답변은 절대 금지입니다."
)

POSITIVE_SYSTEM_PROMPT = (
    "당신은 배달앱에서 장사하는 중식당 사장님입니다. "
    "손님이 남긴 좋은 리뷰에 사장님이 직접 답글을 답니다. "
    "손님은 이미 답글을 수백 개 봤습니다. 매크로처럼 읽히는 순간 실패입니다. "
    "무엇을 시켰는지에 따라 답글의 내용이 달라져야 합니다."
)

BANNED_BLOCK = """## 사용 금지 표현 (매크로/템플릿)
- "주문해 주셔서 진심으로 감사합니다" / "주문해주셔서 정말 감사합니다" 등 이 계열 전부
- "맛있게 드셔주셔서 감사합니다"
- "다음에도 찾아주세요" / "언제든 찾아주세요" / "또 찾아주세요"
- "소중한 리뷰 감사합니다" / "소중한 의견 감사합니다"
- "정성껏 준비하겠습니다" / "최선을 다하겠습니다" / "기대에 부응하겠습니다"
- 매장 이름으로 시작하는 인사 일체 (첫 문장에 매장 이름을 넣지 않는다)
- "OO님, 안녕하세요" 처럼 닉네임 + 인사로 시작하는 정형구
"""

BANNED_BLOCK_POSITIVE = BANNED_BLOCK + """- "~하셨다니 기쁩니다 / 다행입니다 / 보람입니다" 처럼 감정을 보고하는 정형구
- "노력하겠습니다" / "보답하겠습니다" / "큰 힘이 됩니다" / "말씀해 주셔서 감사합니다"
- "정성껏" / "최선을 다해" 같은 부사구
"""

BANNED_BLOCK_NEGATIVE = BANNED_BLOCK + """- "불편을 드려 죄송합니다"
- "빠른 시일 내 조치하겠습니다"
"""

# 배달 음식에서 실제로 벌어지는 문제. 이커머스의 "교환·환불·배송 지연"과 다르다.
DELIVERY_ISSUES = """## 배달 음식에서 실제로 벌어지는 문제 (해당하는 것만 짚을 것)
- 음식 상태: 면이 불음, 튀김이 눅눅해지거나 서로 들러붙음, 식어서 도착, 국물이 졸아듦
- 간과 양: 짜거나 싱거움, 소스나 국물이 모자람, 건더기·해물 양이 적음
- 누락: 시킨 메뉴나 서비스 품목이 빠짐, 요청사항이 반영되지 않음
- 배달: 도착이 늦음, 포장이 새거나 쏟아짐
- 조리: 고기가 질김, 기름을 많이 먹음, 재료 상태가 좋지 않음"""

NEGATIVE_RULES = """## 답변 작성 규칙
1. 손님이 쓴 구체적인 단어를 그대로 받아 쓴다 ("면이 다 불어서"라고 썼으면 "불어버린 면"으로 짚는다).
2. 무엇이 잘못됐는지 → 왜 그렇게 나갔을 수 있는지(변명 아님, 짧게) → 다음에 어떻게 할 것인지 순서로 쓴다.
3. 해결 방안은 배달 매장이 실제로 할 수 있는 것만 쓴다:
   다음 주문 때 해당 메뉴를 다시 챙겨 보내기, 누락분에 대한 직접 연락, 조리·포장 방식 변경,
   면과 국물 분리 포장, 튀김 포장 통풍 처리 등. 교환·환불·배송 지연 같은 이커머스 표현은 쓰지 않는다.
4. 손님이 연락을 원할 수 있으면 매장으로 직접 연락 달라는 한 줄을 넣는다.
5. 원인을 모르면 추측해서 단정하지 않는다. 확인해 보겠다고 쓴다.
6. 매장 이름으로 시작하지 않는다. 닉네임 + 인사 정형구로 시작하지 않는다.
7. 이모지를 쓰지 않는다. 한국어 존댓말, 130~250자.
8. 과하게 굽신대지 말고, 사장이 직접 상황을 파악하고 있다는 태도로 쓴다."""

# 도입 방식을 매번 바꾸는 것이 첫 문장 중복을 막는 가장 확실한 수단이다.
OPENING_ANGLES = [
    {"key": "menu_detail",
     "instruction": "주문한 메인 메뉴 이름을 첫 단어로 꺼내고, 그 메뉴의 조리 포인트를 한 줄로 붙이며 시작한다."},
    {"key": "review_quote",
     "instruction": "손님이 리뷰에 쓴 단어나 표현을 그대로 첫 문장에 받아 쓰며 시작한다.",
     "requires_review": True},
    {"key": "pairing",
     "instruction": "이번에 시킨 메뉴에 다음번 곁들이면 좋을 메뉴를 짚어 주는 문장으로 시작한다."},
    {"key": "kitchen_voice",
     "instruction": "주방에서 그 메뉴를 만드는 사람 시선의 한마디로 시작한다. 인사말 없이 바로 들어간다."},
    {"key": "delivery_care",
     "instruction": "포장·온도·도착 상태 등 배달로 나갈 때 신경 쓰는 지점을 언급하며 시작한다."},
    {"key": "time_of_day",
     "instruction": "주문한 시간대나 계절과 그 메뉴를 엮은 한마디로 시작한다.",
     "requires_time": True},
    {"key": "guest_reaction",
     "instruction": "별점이나 짧은 한마디에 대한 담백한 반응으로 시작한다. 감사 인사로 시작하지 않는다."},
    {"key": "order_combo",
     "instruction": "손님이 고른 메뉴 조합 자체에 대한 가벼운 감상으로 시작한다."},
]

# 첫 문장만 돌리면 모델이 끝맺음을 정형구로 통일해 버린다("~노력하겠습니다 😊").
CLOSING_MOVES = [
    {"key": "next_pick",
     "instruction": "다음에 시켜볼 만한 메뉴나 조합을 하나 짚어 주며 끝낸다."},
    {"key": "specific_promise",
     "instruction": "이번에 시킨 그 메뉴에 대해서만 계속 지키겠다는 것 한 가지를 말하며 끝낸다. "
                    "‘최선을’, ‘노력’ 같은 두루뭉술한 다짐은 금지."},
    {"key": "plain_signoff",
     "instruction": "짧은 한 문장으로 담백하게 끝낸다. 다짐도 감사 인사도 붙이지 않는다."},
    {"key": "packaging_note",
     "instruction": "배달 나갈 때의 포장이나 온도 관리 이야기 한 줄로 끝낸다."},
    {"key": "ask_back",
     "instruction": "다음에 어떤 걸 드셔보고 싶은지, 또는 입맛에 맞춰 조절해 드릴 수 있다는 점을 "
                    "가볍게 물으며 끝낸다."},
    {"key": "menu_note",
     "instruction": "메뉴 이야기로 그냥 끝낸다. 마지막 문장에 인사도 다짐도 넣지 않는다."},
]

ANGLE_BY_KEY = {a["key"]: a for a in OPENING_ANGLES}
CLOSING_BY_KEY = {c["key"]: c for c in CLOSING_MOVES}


def _time_hint(ordered_at) -> str:
    """주문 시각을 '점심시간', '늦은 저녁' 같은 힌트로 바꾼다."""
    if not ordered_at:
        return ""
    if isinstance(ordered_at, str):
        for fmt in ("%Y-%m-%d %H:%M", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M:%S"):
            try:
                ordered_at = datetime.strptime(ordered_at[:19], fmt)
                break
            except ValueError:
                continue
    if not isinstance(ordered_at, datetime):
        return ""

    hour = ordered_at.hour
    if 5 <= hour < 11:
        slot = "아침"
    elif 11 <= hour < 15:
        slot = "점심시간"
    elif 15 <= hour < 17:
        slot = "애매한 오후"
    elif 17 <= hour < 21:
        slot = "저녁시간"
    elif 21 <= hour < 24:
        slot = "늦은 저녁"
    else:
        slot = "새벽"

    month = ordered_at.month
    season = {12: "겨울", 1: "겨울", 2: "겨울"}.get(month) or (
        "봄" if month <= 5 else "여름" if month <= 8 else "가을"
    )
    return f"{ordered_at.month}월 {ordered_at.day}일 {slot} ({season})"


def pick_angle(review_text, ordered_at=None, exclude=None, seed=None) -> dict:
    """이번 답변에 쓸 도입 방식을 고른다."""
    exclude = set(exclude or [])
    has_review = bool(review_text and review_text.strip())
    has_time = bool(_time_hint(ordered_at))

    pool = [
        a for a in OPENING_ANGLES
        if a["key"] not in exclude
        and (has_review or not a.get("requires_review"))
        and (has_time or not a.get("requires_time"))
    ]
    if not pool:
        pool = [a for a in OPENING_ANGLES
                if not a.get("requires_review") and not a.get("requires_time")]

    rng = random.Random(seed) if seed is not None else random
    return rng.choice(pool)


def pick_closing(exclude=None, seed=None) -> dict:
    """이번 답변의 끝맺음 방식을 고른다."""
    exclude = set(exclude or [])
    pool = [c for c in CLOSING_MOVES if c["key"] not in exclude] or CLOSING_MOVES
    rng = random.Random(seed) if seed is not None else random
    return rng.choice(pool)


def pick_emoji(exclude=None, seed=None):
    """이모지를 쓸지, 쓴다면 무엇을 쓸지 정한다. 매번 허용하면 같은 걸로 수렴한다."""
    rng = random.Random(seed) if seed is not None else random
    if rng.random() >= config.POSITIVE_EMOJI_RATE:
        return None
    pool = [e for e in config.POSITIVE_EMOJI_POOL if e not in (exclude or [])]
    return rng.choice(pool or config.POSITIVE_EMOJI_POOL)


def _review_block(review_text) -> str:
    text = (review_text or "").strip()
    if not text:
        return "리뷰 본문: (본문 없이 별점만 남기셨습니다 — 없는 말을 지어내지 말 것)"
    return f"리뷰 본문: {text}"


def _menu_block(menu) -> str:
    items = parse_menu(menu)
    if not items:
        return ""
    return f"\n주문 메뉴:\n{format_menu_block(items)}"


def _build_single_prompt(
    review_text: str, rating: int, category: str | None = None, menu: str | None = None
) -> str:
    """불만 리뷰 한 건에 대한 프롬프트. 배달 음식 맥락."""
    category_line = f"\n이 리뷰의 불만 분류: {category}" if category else ""
    return f"""배달앱에 달린 불만 리뷰입니다. 사장님이 직접 다는 답글을 쓰세요.

## 고객 리뷰 (평점: {rating}점)
{review_text}
{category_line}{_menu_block(menu)}

{BANNED_BLOCK_NEGATIVE}
{DELIVERY_ISSUES}

{NEGATIVE_RULES}

## 출력 형식 (JSON)
{{
  "reply": "답변 텍스트",
  "tone": "답변의 어조 요약 (예: 상황 인정+원인+다음 주문 보완)",
  "key_points_addressed": ["답변에서 다룬 구체적 불만 포인트"],
  "suggested_action": "다음 주문에서 하겠다고 약속한 구체적 조치"
}}"""


def _build_batch_prompt(reviews: list[dict]) -> str:
    """불만 리뷰 여러 건을 한 번에 처리하는 프롬프트."""
    reviews_text = ""
    for i, r in enumerate(reviews, 1):
        cat = f" [분류: {r['category']}]" if r.get("category") else ""
        menu = f"\n주문 메뉴: {r['menu']}" if r.get("menu") else ""
        reviews_text += f"\n### 리뷰 {i} (평점: {r['rating']}점){cat}{menu}\n{r['review_text']}\n"

    return f"""배달앱에 달린 불만 리뷰 {len(reviews)}개입니다. 각각에 대한 사장님 답글을 쓰세요.

{reviews_text}

{BANNED_BLOCK_NEGATIVE}- 모든 답변이 같은 문장으로 시작하는 것도 금지

{DELIVERY_ISSUES}

{NEGATIVE_RULES}

## 출력 형식 (JSON)
{{
  "replies": [
    {{
      "review_index": 1,
      "reply": "답변 텍스트",
      "tone": "어조 요약",
      "key_points_addressed": ["불만 포인트"],
      "suggested_action": "다음 주문에서의 조치"
    }}
  ]
}}"""


def _build_positive_prompt(
    review_text, rating, menu_items, angle, closing,
    ordered_at=None, order_type=None,
    avoid_openings=None, avoid_closings=None, avoid_shapes=None,
    emoji=None, violations=None,
):
    """좋은 리뷰에 대한 프롬프트. 도입·끝맺음 방식이 매번 다르다."""
    time_hint = _time_hint(ordered_at)
    main_names = ", ".join(i["name"] for i in main_items(menu_items)) or "(정보 없음)"

    context_lines = [f"별점: {rating}점"]
    if order_type:
        context_lines.append(f"주문 방식: {order_type}")
    if time_hint:
        context_lines.append(f"주문 시각: {time_hint}")

    avoid_block = ""
    if avoid_openings:
        avoid_block += "\n## 이미 다른 답변에 쓴 첫 문장 (비슷하게도 쓰지 말 것)\n" + \
            "\n".join(f"- {o}" for o in avoid_openings) + "\n"
    if avoid_closings:
        avoid_block += "\n## 이미 다른 답변에 쓴 끝 문장 (비슷하게도 쓰지 말 것)\n" + \
            "\n".join(f"- {o}" for o in avoid_closings) + "\n"
    if avoid_shapes:
        avoid_block += "\n## 이미 다 써 버린 첫 문장 골격 (내용어만 바꾼 같은 형태 금지)\n" + \
            "\n".join(f"- {o}" for o in avoid_shapes) + "\n"

    retry_block = ""
    if violations:
        retry_block = (
            "\n\n## 직전 시도가 이 규칙에 걸렸다. 같은 실수를 반복하지 말 것\n"
            + "\n".join(f"- {v}" for v in violations)
            + "\n걸린 표현은 문장째 다시 쓴다. 단어만 바꾸지 말 것."
        )

    emoji_rule = (
        f"이모지는 {emoji} 하나만, 마지막에 한 번 쓴다. 다른 이모지는 쓰지 않는다."
        if emoji else "이모지를 쓰지 않는다."
    )

    return f"""배달앱에 달린 좋은 리뷰입니다. 사장님이 직접 다는 답글을 쓰세요.

## 리뷰
{chr(10).join(context_lines)}
주문 메뉴:
{format_menu_block(menu_items)}
{_review_block(review_text)}

{format_store_menu()}

## 이번 답변의 도입 방식 (반드시 이대로 시작할 것)
{angle["instruction"]}

## 이번 답변의 끝맺음 방식 (반드시 이대로 끝낼 것)
{closing["instruction"]}
{avoid_block}
{BANNED_BLOCK_POSITIVE}

## 작성 규칙
1. 주문한 메인 메뉴({main_names}) 중 하나를 골라 이름 그대로 답변에 넣는다.
2. 그 메뉴에만 해당하는 이야기를 쓴다. 다른 메뉴로 바꿔 넣어도 말이 되는 문장이면 실패다.
   (짬뽕=매콤함·불맛·국물 / 짜장=고소한 춘장 향·면과 소스 / 탕수육=바삭함·소스 /
    만두·꽃빵=곁들임 — 이런 식으로 축이 다르다)
3. 리뷰 본문에 구체적인 단어가 있으면 그 단어를 그대로 받아 쓴다. 본문이 없으면 메뉴로만 쓴다.
   메뉴 키워드는 방향만 알려 주는 것이다. 키워드를 나열하거나 그대로 옮겨 적지 않는다.
4. 사과하거나 해명하지 않는다. 좋은 리뷰다.
5. 매장에 대한 사실을 지어내지 않는다. 신메뉴, 수상 이력, 원산지, 조리 시간처럼
   확인할 수 없는 내용은 쓰지 않는다.
6. 위 주문 메뉴 목록에 없는 메뉴를 손님이 드신 것처럼 쓰지 않는다. 다른 메뉴는
   "다음에 ~ 드셔 보세요" 같은 제안으로만 언급하고, 매장 메뉴 목록에 있는 이름만 쓴다.
7. 손님이 질문을 남겼는데 확실한 답을 모르면 추측해서 답하지 않는다.
   ("아마 ~일 겁니다" 금지) 대신 매장으로 연락 주시면 확인해 드리겠다고 쓴다.
8. 손님을 향한 문장이 최소 한 번은 들어가야 한다. 메뉴 설명만 늘어놓으면 안내문이지 답글이 아니다.
   단, 감정 보고나 감사 인사가 아니라 손님이 쓴 내용을 받는 방식으로 쓴다.
9. {emoji_rule}
10. 공백 포함 {config.POSITIVE_REPLY_MIN_CHARS}자 이상 {config.POSITIVE_REPLY_MAX_CHARS}자 이하.
11. 배달 주문이다. 매장으로 오라는 인사가 아니라, 다음에 또 시키고 싶게 만드는 것이 목적이다.
12. 사장님이 직접 쓴 것처럼 담백한 존댓말. 과장된 미사여구와 나열식 감탄 금지.
13. 이 답글은 같은 매장의 다른 답글 수백 개 옆에 나란히 붙는다. 문장 골격이 남들과
    같으면 메뉴 이름만 바꾼 매크로로 읽힌다. 첫 문장과 끝 문장의 형태를 특히 다르게 쓴다.

## 출력 형식 (JSON)
{{
  "reply": "답글 본문",
  "menu_mentioned": ["답글에 실제로 언급한 메뉴"],
  "opening_move": "첫 문장이 어떤 방식으로 시작하는지 한 줄 설명"
}}{retry_block}"""


class ReplyGenerator:
    """리뷰 한 건 또는 여러 건에 대한 사장님 답글 생성기."""

    def __init__(self, store_name: str | None = None, model: str | None = None):
        self.client = get_client()
        self.store_name = store_name or config.STORE_NAME
        self.model = model or config.REPLY_LLM_MODEL

    # ── 부정 리뷰 (기존 경로, 반환 형태 유지) ────────────────

    def generate_single(
        self, review_text: str, rating: int,
        category: str | None = None, menu: str | None = None,
    ) -> dict:
        """단일 불만 리뷰에 대한 맞춤 답변 생성."""
        prompt = _build_single_prompt(review_text, rating, category, menu)
        raw = call_openai_json(
            self.client, prompt, system_prompt=SYSTEM_PROMPT, model=self.model
        )

        parsed = extract_json_from_text(raw)
        if not parsed or "reply" not in parsed:
            logger.warning("답변 생성 JSON 파싱 실패, raw: %s", raw[:200])
            return {"reply": raw, "tone": "", "key_points_addressed": [], "suggested_action": ""}

        return parsed

    def generate_batch(self, reviews: list[dict]) -> list[dict]:
        """다건 불만 리뷰 답변 일괄 생성. REPLY_BATCH_SIZE씩 묶어 호출."""
        all_replies = []

        for start in range(0, len(reviews), REPLY_BATCH_SIZE):
            chunk = reviews[start:start + REPLY_BATCH_SIZE]
            prompt = _build_batch_prompt(chunk)
            raw = call_openai_json(
                self.client, prompt, system_prompt=SYSTEM_PROMPT, model=self.model
            )

            parsed = extract_json_from_text(raw)
            if parsed and "replies" in parsed:
                # 청크마다 LLM 이 1부터 다시 세므로 오프셋을 더해 전역 순번으로 맞춘다
                normalized = []
                for reply_data in parsed["replies"]:
                    reply_data["review_index"] = start + reply_data.get("review_index", 1)
                    normalized.append(reply_data)
                normalized.sort(key=lambda r: r["review_index"])
                all_replies.extend(normalized)
            else:
                logger.warning("일괄 답변 생성 파싱 실패, chunk %d~%d", start, start + len(chunk))

        return all_replies

    # ── 검사 ────────────────────────────────────────────────

    def _positive_violations(self, reply, menu, avoid_openings, avoid_closings,
                             avoid_shapes, max_emoji=1):
        problems = find_violations(
            reply, self.store_name,
            min_chars=config.POSITIVE_REPLY_MIN_CHARS,
            max_chars=config.POSITIVE_REPLY_MAX_CHARS,
            max_emoji=max_emoji,
            avoid_openings=avoid_openings,
            avoid_closings=avoid_closings,
            avoid_shapes=avoid_shapes,
        )
        wrong = unordered_mentions(reply, menu)
        if wrong:
            ordered = ", ".join(i["name"] for i in parse_menu(menu)) or "(없음)"
            problems.append(
                f"주문에 없는 메뉴를 드신 것처럼 언급함: {', '.join(wrong)}. "
                f"이 손님이 실제로 시킨 것은 [{ordered}] 뿐이다. "
                "다른 메뉴는 '다음에 ~ 드셔 보세요' 형태로만 쓴다."
            )
        return problems

    def _call(self, prompt, system_prompt, temperature):
        raw = call_openai_json(
            self.client, prompt, system_prompt=system_prompt,
            model=self.model, temperature=temperature,
        )
        parsed = extract_json_from_text(raw)
        if not parsed or not parsed.get("reply"):
            logger.warning("답변 JSON 파싱 실패: %s", (raw or "")[:200])
            return None
        return parsed

    # ── 긍정 리뷰 ────────────────────────────────────────────

    def generate_positive(
        self, review_text, rating=5, menu=None, *,
        ordered_at=None, order_type=None,
        avoid_openings=None, avoid_closings=None, avoid_shapes=None, avoid_emojis=None,
        exclude_angles=None, exclude_closings=None, angle=None, closing=None,
    ) -> dict:
        """좋은 리뷰에 대한 답글. 주문 메뉴와 도입·끝맺음 방식으로 매번 다르게 만든다."""
        menu_items = parse_menu(menu)
        chosen = ANGLE_BY_KEY.get(angle) or pick_angle(
            review_text, ordered_at, exclude=exclude_angles
        )
        chosen_closing = CLOSING_BY_KEY.get(closing) or pick_closing(exclude=exclude_closings)
        chosen_emoji = pick_emoji(exclude=avoid_emojis)

        violations: list[str] = []
        parsed = None
        # 재시도가 JSON 파싱에 실패해도 앞서 성공한 답변을 버리지 않는다.
        best, best_violations = None, []

        for attempt in range(MAX_ATTEMPTS):
            prompt = _build_positive_prompt(
                review_text, rating, menu_items, chosen, chosen_closing,
                ordered_at=ordered_at, order_type=order_type,
                avoid_openings=avoid_openings, avoid_closings=avoid_closings,
                avoid_shapes=avoid_shapes, emoji=chosen_emoji, violations=violations,
            )
            parsed = self._call(prompt, POSITIVE_SYSTEM_PROMPT,
                                config.REPLY_POSITIVE_TEMPERATURE)
            if not parsed:
                continue

            violations = self._positive_violations(
                parsed["reply"], menu, avoid_openings, avoid_closings, avoid_shapes,
                max_emoji=1 if chosen_emoji else 0,
            )
            if best is None or len(violations) < len(best_violations):
                best, best_violations = parsed, violations
            if not violations:
                break

            logger.info("긍정 답변 재생성 (%d회차): %s", attempt + 1, violations)
            # 문장이 겹쳤다면 도입·끝맺음 방식 자체를 바꿔서 다시 시도한다.
            if any("첫 문장" in v for v in violations):
                chosen = pick_angle(
                    review_text, ordered_at,
                    exclude=list(set(exclude_angles or []) | {chosen["key"]}),
                )
            if any("끝 문장" in v for v in violations):
                chosen_closing = pick_closing(
                    exclude=list(set(exclude_closings or []) | {chosen_closing["key"]})
                )

        if best is None:
            raise RuntimeError("답변 생성에 실패했습니다. 잠시 후 다시 시도해 주세요.")

        parsed, violations = best, best_violations
        reply = parsed["reply"].strip()
        return {
            "reply": reply,
            "sentiment": "positive",
            "opening_angle": chosen["key"],
            "closing_move": chosen_closing["key"],
            "emoji": chosen_emoji or "",
            "opening_sentence": first_sentence(reply),
            "opening_shape": opening_shape(first_sentence(reply)),
            "closing_sentence": last_sentence(reply),
            "menu_mentioned": parsed.get("menu_mentioned", []),
            "violations": violations,
        }

    # ── 부정 리뷰 (검사 포함, 새 화면용) ──────────────────────

    def generate_negative(
        self, review_text, rating, menu=None, *,
        ordered_at=None, order_type=None, category=None,
    ) -> dict:
        """불만 리뷰 답글. 배달 맥락으로 짚고 다음 주문 보완을 약속한다."""
        violations: list[str] = []
        parsed = None
        best, best_violations = None, []

        for attempt in range(MAX_ATTEMPTS):
            prompt = _build_single_prompt(review_text, rating, category, menu)
            if violations:
                prompt += "\n\n## 직전 시도가 걸린 규칙 (반드시 고칠 것)\n" + \
                    "\n".join(f"- {v}" for v in violations)
            parsed = self._call(prompt, SYSTEM_PROMPT, config.REPLY_NEGATIVE_TEMPERATURE)
            if not parsed:
                continue

            violations = find_violations(
                parsed["reply"], self.store_name,
                min_chars=130, max_chars=250, max_emoji=0, negative=True,
            )
            if best is None or len(violations) < len(best_violations):
                best, best_violations = parsed, violations
            if not violations:
                break
            logger.info("부정 답변 재생성 (%d회차): %s", attempt + 1, violations)

        if best is None:
            raise RuntimeError("답변 생성에 실패했습니다. 잠시 후 다시 시도해 주세요.")

        parsed, violations = best, best_violations
        reply = parsed["reply"].strip()
        return {
            "reply": reply,
            "sentiment": "negative",
            "opening_angle": "",
            "closing_move": "",
            "emoji": "",
            "opening_sentence": first_sentence(reply),
            "opening_shape": "",
            "closing_sentence": last_sentence(reply),
            "issues_addressed": parsed.get("key_points_addressed", []),
            "next_action": parsed.get("suggested_action", ""),
            "violations": violations,
        }

    # ── 진입점 ───────────────────────────────────────────────

    def generate(self, review_text=None, rating=5, menu=None, **kwargs) -> dict:
        """별점에 따라 긍정·부정 경로로 보낸다."""
        if rating >= config.POSITIVE_RATING_THRESHOLD:
            return self.generate_positive(review_text, rating, menu, **kwargs)
        for positive_only in (
            "avoid_openings", "avoid_closings", "avoid_shapes", "avoid_emojis",
            "exclude_angles", "exclude_closings", "angle", "closing",
        ):
            kwargs.pop(positive_only, None)
        return self.generate_negative(review_text, rating, menu, **kwargs)

    def generate_series(self, reviews: list[dict]) -> list[dict]:
        """여러 건을 순차 생성한다. 앞서 쓴 문장을 계속 넘겨 중복을 막는다.

        `generate_batch` 와 달리 한 번에 한 건씩 부르고, 배치 안의 중복을 검사한다.
        """
        results = []
        used_openings: list[str] = []
        used_closings: list[str] = []
        used_shapes: list[str] = []
        used_angles: list[str] = []
        used_closing_moves: list[str] = []
        used_emojis: list[str] = []

        for index, item in enumerate(reviews):
            rating = int(item.get("rating", 5))
            kwargs = {
                "ordered_at": item.get("ordered_at"),
                "order_type": item.get("order_type"),
            }
            if rating >= config.POSITIVE_RATING_THRESHOLD:
                kwargs["avoid_openings"] = list(used_openings)
                kwargs["avoid_closings"] = list(used_closings)
                kwargs["avoid_shapes"] = sorted(set(used_shapes))
                kwargs["avoid_emojis"] = used_emojis[-3:]
                kwargs["exclude_angles"] = used_angles[-3:]
                kwargs["exclude_closings"] = used_closing_moves[-3:]
            else:
                kwargs["category"] = item.get("category")

            try:
                result = self.generate(
                    item.get("review_text"), rating, item.get("menu"), **kwargs
                )
            except Exception:  # pylint: disable=broad-except
                logger.exception("리뷰 %d번 답변 생성 실패", index)
                continue

            result["review_index"] = index
            results.append(result)
            used_openings.append(result["opening_sentence"])
            used_closings.append(result["closing_sentence"])
            if result.get("opening_angle"):
                used_angles.append(result["opening_angle"])
            if result.get("closing_move"):
                used_closing_moves.append(result["closing_move"])
            if result.get("opening_shape"):
                used_shapes.append(result["opening_shape"])
            if result.get("emoji"):
                used_emojis.append(result["emoji"])

        return results
