"""주문 메뉴 파싱과 메뉴별 표현 축.

배달앱 리뷰는 본문이 "맛있어요" 한 줄이거나 아예 비어 있는 경우가 많다
(실측: 441건 중 119건이 본문 없음). 답변을 서로 다르게 만드는 유일한
재료가 주문 메뉴이므로, 메뉴 문자열을 쓸 수 있는 형태로 정규화하고
메뉴마다 다른 표현 축을 제공한다.
"""

import json
import os
import re
from functools import lru_cache

# 리뷰 이벤트로 1원에 붙는 서비스 품목에는 안내 문구가 그대로 따라온다.
# 예: "군만두3P 찜과ZI뷰항상감사드립니다"
SERVICE_ITEM_SUFFIX = re.compile(r"\s*찜과\s*[a-zA-Z]*뷰.*$")

# 세트 메뉴는 "짜장+짬뽕+미니탕수육" 형태로 한 품목 안에 여러 음식이 들어온다.
SET_SPLIT = re.compile(r"\s*\+\s*")

# 앞선 항목이 뒤 항목의 부분 문자열이면 안 되므로 구체적인 것부터 나열한다.
# 값은 "다듬어진 문장"이 아니라 키워드다. 완성된 문구를 주면 모델이 그대로 베껴
# 쓰기 때문에, 여러 답변에 같은 표현이 반복된다. 키워드만 주고 문장은 모델이 짓게 한다.
FLAVOR_AXES = [
    ("굴짬뽕", "굴향·겨울한정·시원한국물"),
    ("해물백짬뽕", "맑은국물·안맵다·담백"),
    ("해물쟁반짬뽕", "넓은팬·나눠먹기·해물양"),
    ("해물짬뽕탕", "안주·국물·건더기"),
    ("해물짬뽕", "해물·시원함·불맛"),
    ("새우고추짬뽕", "청양고추·칼칼함·새우단맛"),
    ("소고기짬뽕", "소고기육향·진한국물"),
    ("순두부짬뽕", "순두부·부드러움·숟가락"),
    ("크림짬뽕", "크림·고소함·안맵다"),
    ("마라짬뽕", "마라·얼얼함·매운정도"),
    ("도야짬뽕", "웍불맛·매콤·국물"),
    ("짬뽕", "매콤·불맛·국물"),
    ("해물쟁반짜장", "넓은팬·비벼먹기·해물"),
    ("새우고추짜장", "매콤·새우·짜장"),
    ("도야간짜장", "따로볶은소스·비비기·면"),
    ("간짜장", "따로볶은소스·비비기·면"),
    ("도야짜장면", "춘장향·고소함·면발"),
    ("짜장", "춘장향·고소함"),
    ("미니탕수육", "곁들임·적당한양·바삭"),
    ("탕수육", "튀김옷·바삭·소스"),
    ("유린기", "바삭·간장소스·새콤"),
    ("크림새우", "새우탱탱·크림소스·달콤"),
    ("양장피", "겨자소스·해파리·채소식감"),
    ("고추잡채", "꽃빵조합·고추향"),
    ("불고기잡채밥", "불고기·잡채·밥"),
    ("불고기잡채", "불고기·달큰함·잡채"),
    ("마라마파두부", "마라·얼얼함·두부"),
    ("중화 제육덮밥", "센불·제육·덮밥"),
    ("덮밥", "센불·볶음·밥"),
    ("볶음밥", "불향·밥알"),
    ("연유꽃빵", "찍어먹기·연유·달콤"),
    ("꽃빵", "찍어먹기·곁들임"),
    ("군만두", "곁들임·바삭"),
    ("만두", "곁들임·바삭"),
    ("술안주", "안주구성"),
]


def _strip_service_suffix(raw: str) -> tuple[str, bool]:
    """서비스 품목 안내 문구를 떼고, 서비스 품목이었는지 함께 돌려준다."""
    cleaned = SERVICE_ITEM_SUFFIX.sub("", raw).strip()
    return cleaned, cleaned != raw.strip()


def _flavor_axis(name: str) -> str:
    for keyword, axis in FLAVOR_AXES:
        if keyword in name:
            return axis
    return ""


def parse_menu(menu_text: str | None) -> list[dict]:
    """주문메뉴 문자열을 품목 리스트로 파싱.

    "해물짬뽕 | 군만두3P 찜과ZI뷰항상감사드립니다" 같은 입력을
    [{name, axis, is_service}, ...] 로 바꾼다. 세트 메뉴는 통째로 한 품목이되
    구성 음식의 표현 축을 모아 준다.
    """
    if not menu_text or not menu_text.strip():
        return []

    items: list[dict] = []
    seen: set[str] = set()

    for raw in re.split(r"[|,/]", menu_text):
        raw = raw.strip()
        if not raw:
            continue

        name, is_service = _strip_service_suffix(raw)
        if not name or name in seen:
            continue
        seen.add(name)

        axes = []
        for part in SET_SPLIT.split(name):
            axis = _flavor_axis(part.strip())
            if axis and axis not in axes:
                axes.append(axis)

        items.append({
            "name": name,
            "axis": " / ".join(axes),
            "is_service": is_service,
        })

    return items


def main_items(items: list[dict]) -> list[dict]:
    """리뷰 이벤트 서비스 품목을 뺀 메인 메뉴. 전부 서비스면 원본을 돌려준다."""
    mains = [i for i in items if not i["is_service"]]
    return mains or items


def format_menu_block(items: list[dict]) -> str:
    """프롬프트에 넣을 메뉴 설명 블록."""
    if not items:
        return "(주문 메뉴 정보 없음)"

    lines = ["※ 아래 키워드는 방향 힌트다. 그대로 옮겨 적지 말고 사장님 말투의 문장으로 새로 쓸 것.", ""]
    for item in items:
        tag = " [리뷰 이벤트 서비스 품목 — 이 메뉴를 답변의 중심으로 삼지 말 것]" if item["is_service"] else ""
        axis = f"  (키워드: {item['axis']})" if item["axis"] else ""
        lines.append(f"- {item['name']}{tag}{axis}")
    return "\n".join(lines)


# 답변이 주문에 없는 메뉴를 "드셨다"고 쓰는 것을 잡기 위한 굵은 단위 음식 이름.
# (실제 사고: 짬뽕+미니탕수육만 시킨 손님에게 "바삭한 군만두도 함께하니"라고 답한 적 있음)
COARSE_DISHES = [
    "짬뽕", "짜장", "탕수육", "군만두", "만두", "꽃빵", "볶음밥", "덮밥",
    "양장피", "고추잡채", "유린기", "크림새우", "마파두부", "잡채", "쟁반",
]

# 다음 주문을 제안하는 맥락이면 주문에 없는 메뉴를 말해도 된다.
# 미래를 가리키는 표현만 넣는다. "곁들이는 재미" 같은 서술까지 제안으로 봐 주면
# "군만두 바삭함도 함께 하셨다니"가 그냥 통과해 버린다.
_SUGGESTION_MARKERS = (
    "다음", "이번엔", "이번에는", "한번", "한 번", "추천", "드셔보", "시켜보",
    "즐겨보", "해보시", "보시면", "보시겠", "보세요", "어떠", "괜찮으시",
)

_SENTENCE_SPLIT = re.compile(r"(?<=[.!?~])\s+|\n+")


def unordered_mentions(reply: str, menu_text: str | None) -> list[str]:
    """주문에 없는 메뉴를 제안이 아닌 방식으로 언급한 경우를 찾는다."""
    ordered = " ".join(i["name"] for i in parse_menu(menu_text))
    if not ordered:
        return []

    found = []
    for sentence in _SENTENCE_SPLIT.split(reply):
        if any(marker in sentence for marker in _SUGGESTION_MARKERS):
            continue
        for dish in COARSE_DISHES:
            if dish in sentence and dish not in ordered and dish not in found:
                found.append(dish)
    # "군만두"를 이미 잡았으면 "만두"는 같은 건이다.
    return [d for d in found if not any(d != o and d in o for o in found)]


_MENU_CATALOG_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "store_menu.json"
)


@lru_cache(maxsize=1)
def store_menu_items() -> tuple[str, ...]:
    """매장이 실제로 파는 메뉴 목록.

    없으면 빈 튜플. 이게 있어야 답변이 "왕만두" 같은 없는 메뉴를 제안하지 않는다.
    """
    try:
        with open(_MENU_CATALOG_PATH, encoding="utf-8") as fp:
            return tuple(json.load(fp).get("items", []))
    except (OSError, ValueError):
        return ()


def format_store_menu() -> str:
    """프롬프트에 넣을 매장 메뉴 목록."""
    items = store_menu_items()
    if not items:
        return (
            "## 매장 메뉴\n"
            "메뉴 목록이 없다. 이번 주문에 없는 메뉴는 아예 언급하지 않는다."
        )
    return (
        "## 매장이 실제로 파는 메뉴 (다른 메뉴를 제안한다면 반드시 이 안에서 고를 것)\n"
        + ", ".join(items)
    )
