"""배달 외식업 리뷰 분류 라벨 체계 v1 (2026-09-15 확정).

이 파일이 라벨 체계의 **단일 출처**다. 라벨링 가이드 문서
(docs/evaluation/labeling-guide-v1.md)와 이 파일이 어긋나면 이 파일이 맞다.

⚠️ 사전 확정(pre-registration) 원칙
    이 체계는 어떤 모델 출력도 보기 전에 확정했다. 모델이 자주 틀리는 것을
    보고 카테고리를 쪼개거나 합치면 그 숫자는 방어할 수 없다.
    수정이 필요하면 v2 를 새로 만들고, v1/v2 수치를 **둘 다** 남긴다.
    TAXONOMY_VERSION 을 올리지 않은 변경은 금지한다.
"""

from __future__ import annotations

TAXONOMY_VERSION = "v1"
TAXONOMY_FROZEN_AT = "2026-09-15"

# ── 라벨 정의 ────────────────────────────────────────────────
#
# key: 라벨 키 (모델 프롬프트·ground truth·지표에서 쓰는 이름)
# ko: 사람이 읽는 이름 (라벨링 도구 표시용)
# hotkey: 라벨링 도구 단축키 (한 글자)
# includes / excludes: 판정 경계. 가이드 문서의 표와 동일해야 한다.

LABELS: dict[str, dict] = {
    "taste": {
        "ko": "맛",
        "hotkey": "1",
        "includes": "음식 맛 자체에 대한 불만. 싱겁다/짜다/맵다/느끼하다/맛없다, "
                    "면이 불었다, 소스 배합이 이상하다, 예전 맛과 다르다.",
        "excludes": "식어서 맛이 없는 경우는 temperature. "
                    "이물질·상한 냄새는 hygiene. 양 때문에 아쉬운 것은 portion.",
    },
    "temperature": {
        "ko": "온도",
        "hotkey": "2",
        "includes": "도착 시점 온도 불만. 식었다/미지근하다/차갑다, "
                    "튀김이 눅눅해졌다(=식어서 눅눅), 국물이 안 뜨겁다.",
        "excludes": "배달이 오래 걸렸다는 '시간' 자체 불만은 delivery_delay. "
                    "시간과 온도를 둘 다 말하면 R4 를 따른다.",
    },
    "portion": {
        "ko": "양",
        "hotkey": "3",
        "includes": "양이 적다, 건더기가 없다, 사진보다 적다, 1인분 같지 않다. "
                    "'양 대비 비싸다'에서 양이 주어인 경우.",
        "excludes": "메뉴/서비스 품목이 통째로 빠진 것은 missing_item. "
                    "가격이 주어인 불만은 price.",
    },
    "hygiene": {
        "ko": "위생·이물질",
        "hotkey": "4",
        "includes": "머리카락·비닐·벌레 등 이물질, 상한 냄새/쉰내, 곰팡이, "
                    "덜 익음, 먹고 탈이 났다, 용기가 더럽다.",
        "excludes": "단순히 맛이 없는 것은 taste. 용기 파손·국물 샘은 packaging.",
    },
    "missing_item": {
        "ko": "누락",
        "hotkey": "5",
        "includes": "주문한 메뉴가 안 왔다, 리뷰이벤트 서비스가 빠졌다, "
                    "단무지/소스/수저/포크/젓가락 누락, 음료 누락.",
        "excludes": "주문과 '다른' 것이 온 것은 wrong_item. 양이 적은 것은 portion.",
    },
    "wrong_item": {
        "ko": "오배송",
        "hotkey": "6",
        "includes": "주문한 것과 다른 메뉴가 왔다, 짜장 시켰는데 짬뽕이 왔다, "
                    "맵기·옵션이 주문과 다르다, 다른 집 음식이 왔다.",
        "excludes": "빠진 것은 missing_item.",
    },
    "packaging": {
        "ko": "포장",
        "hotkey": "7",
        "includes": "국물이 샜다, 용기가 깨졌다/찌그러졌다, 뚜껑이 열려 있었다, "
                    "음식이 쏟아져 흐트러졌다, 봉투가 터졌다.",
        "excludes": "용기가 더러운 것은 hygiene. 포장 때문에 식은 경우는 R5 를 따른다.",
    },
    "delivery_delay": {
        "ko": "배달 지연",
        "hotkey": "8",
        "includes": "배달이 오래 걸렸다, 예상 시간보다 한참 늦었다, "
                    "조리 시작이 늦었다, 주문 폭주로 지연됐다.",
        "excludes": "식어서 온 것 자체는 temperature. 라이더가 엉뚱한 곳에 둔 것은 rider.",
    },
    "rider": {
        "ko": "라이더",
        "hotkey": "9",
        "includes": "배달원 태도/말투, 문 앞 요청 무시, 엉뚱한 집에 배달, "
                    "음식 분실, 초인종 안 누름, 던지듯 놓고 감.",
        "excludes": "매장 직원·사장 응대는 store_response. 단순 지연은 delivery_delay.",
    },
    "store_response": {
        "ko": "매장 응대",
        "hotkey": "0",
        "includes": "전화 안 받음, 응대 태도 불친절, 환불/재배달 거부, "
                    "사장 답글이 성의 없다, 요청사항 무시(조리 요청).",
        "excludes": "배달원 응대는 rider. 라이더 요청사항 무시는 rider.",
    },
    "price": {
        "ko": "가격",
        "hotkey": "p",
        "includes": "비싸다, 가성비 나쁘다, 배달비가 과하다, 값을 올렸다. "
                    "'양 대비 비싸다'에서 가격이 주어인 경우.",
        "excludes": "양이 주어면 portion.",
    },
    "other": {
        "ko": "기타",
        "hotkey": "x",
        "includes": "불만은 분명하나 위 어디에도 맞지 않는 경우. "
                    "배달앱 자체 오류, 쿠폰/포인트 문제, 주차/출입 문제 등.",
        "excludes": "판정이 애매하다는 이유로 쓰지 않는다. 애매하면 R10 을 따른다.",
    },
    "no_issue": {
        "ko": "문제 없음",
        "hotkey": "n",
        "includes": "불만이 없는 리뷰. 칭찬, 중립적 감상, 재주문 의사. "
                    "별점이 낮아도 본문에 불만이 없으면 여기로 간다(R2).",
        "excludes": "'다음엔 ~해주세요' 형태의 개선 요청은 불만으로 본다(R7).",
    },
}

#: 닫힌 라벨 집합. 모델 프롬프트와 ground truth 가 공유한다.
LABEL_KEYS: tuple[str, ...] = tuple(LABELS)

#: 불만 카테고리 (no_issue 제외). "부정 리뷰 TOP 3" 집계 대상이다.
COMPLAINT_KEYS: tuple[str, ...] = tuple(k for k in LABEL_KEYS if k != "no_issue")

#: 표본에서 빼는 표시. 라벨이 아니라 제외 사유다.
#: 본문이 없거나(이모지·자음만), 무슨 말인지 판정할 수 없는 리뷰.
EXCLUDE = "EXCLUDE"

HOTKEYS: dict[str, str] = {v["hotkey"]: k for k, v in LABELS.items()}
assert len(HOTKEYS) == len(LABELS), "단축키가 겹친다"


def is_valid_label(value: str) -> bool:
    return value in LABELS


def build_category_block() -> str:
    """모델 프롬프트에 넣을 카테고리 설명 블록.

    라벨링 가이드가 사람에게 준 경계와 **같은 문장**을 모델에게도 준다.
    사람은 상세한 기준을 보고 모델은 라벨 이름만 보는 상태에서 나온 격차는
    모델의 실력이 아니라 정보량 차이다.
    """
    lines = []
    for key, spec in LABELS.items():
        lines.append(f"- {key} ({spec['ko']}): {spec['includes']}")
    return "\n".join(lines)


# ── 레거시 이커머스 10종과의 대응 ──────────────────────────────
#
# core/utils/review_categories.py 의 기존 영어 10종은 이커머스(의류·공산품)
# 기준이라 배달 음식에 '맛'과 '온도'가 없다. 그래서 v1 을 새로 만들었다.
# 과거 수치와 대조할 때만 쓰는 참고용 대응표이며, 손실이 있는 사상이다.
# (taste/temperature/hygiene → poor_quality 로 뭉개지므로 역방향은 불가능하다.)

LEGACY_ECOMMERCE_MAP: dict[str, str] = {
    "taste": "poor_quality",
    "temperature": "poor_quality",
    "hygiene": "poor_quality",
    "portion": "size_issue",
    "missing_item": "missing_parts",
    "wrong_item": "wrong_item",
    "packaging": "damaged_packaging",
    "delivery_delay": "delivery_delay",
    "rider": "customer_service",
    "store_response": "customer_service",
    "price": "price_issue",
    "other": "other",
    "no_issue": "other",
}


# ── 층화 추출용 불만 어휘 사전 ────────────────────────────────
#
# ⚠️ 이 사전은 **표본을 나누는 용도로만** 쓴다.
#    라벨을 정하는 데도, 모델 예측에도 쓰지 않는다.
#    사전이 놓치는 불만을 재기 위해 S4(사전 미검출 5점) 층을 반드시 표본에
#    포함시킨다. 그래야 사전의 누락률을 숫자로 말할 수 있다.
#
# LLM 을 쓰지 않는 규칙 기반이다. 모델이 표본 구성에 개입하면 안 된다.

COMPLAINT_LEXICON: tuple[str, ...] = (
    # 맛·상태
    "맛없", "맛이없", "별로", "싱겁", "짜요", "짜서", "짜고", "느끼", "비려", "비린",
    "불었", "퍼졌", "눅눅", "질겨", "질기", "딱딱", "덜익", "설익",
    # 온도
    "식어", "식었", "미지근", "차갑", "차가웠", "안뜨겁", "안 뜨겁",
    # 양
    "양이적", "양이 적", "양적", "양 적", "부족", "건더기", "적어요", "적네",
    # 위생
    "머리카락", "이물질", "벌레", "곰팡이", "쉰내", "상한", "냄새나", "더러",
    "배탈", "탈났", "탈이", "설사",
    # 누락·오배송
    "누락", "안왔", "안 왔", "빠졌", "빠져", "안줬", "안 줬", "안보내", "없어서",
    "다른게", "다른 게", "잘못왔", "잘못 왔", "잘못보내", "바뀌",
    # 포장
    "샜", "새서", "터졌", "쏟아", "엎어", "깨졌", "찌그", "열려있", "흐트러",
    # 배달·라이더
    "늦게", "늦었", "지연", "오래걸", "오래 걸", "한시간", "1시간", "두시간",
    "기다렸", "안오", "안 오", "라이더", "배달원", "던지",
    # 응대·가격
    "불친절", "환불", "전화", "안받", "안 받", "무시", "비싸", "비쌈", "가성비",
    "실망", "최악", "다신", "다시는", "안시켜", "안 시켜", "취소",
)


def has_complaint_signal(text: str) -> bool:
    """규칙 기반 불만 신호 검출 (층화 추출 전용)."""
    if not text:
        return False
    normalized = text.replace(" ", "")
    return any(
        token in text or token.replace(" ", "") in normalized
        for token in COMPLAINT_LEXICON
    )
