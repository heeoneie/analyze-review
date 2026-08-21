"""답변 텍스트 검사 도구.

매크로처럼 보이는 답변을 만들어 놓고 "매크로가 아니다"라고 주장하지 않으려면,
생성한 뒤에 기계적으로 확인하는 층이 필요하다. 여기 있는 규칙은 실제 매장의
답변 441건에서 반복 확인된 패턴을 근거로 한다.
"""

import re
import unicodedata

# 공백을 모두 제거한 문자열에 대해 검사하므로 띄어쓰기 변형을 함께 잡는다.
# (실측: "주문해 주셔서" / "주문해주셔서" 가 섞여 쓰이고 있었다)
BANNED_PATTERNS = [
    (r"(주문|선택|이용|찾아|방문)해?주셔서.{0,10}(감사|기쁩|기뻐|좋습니다|고맙)",
     "‘주문/선택해 주셔서 감사합니다’ 계열"),
    (r"맛있게드셔.{0,8}감사", "‘맛있게 드셔주셔서 감사합니다’"),
    (r"맛있게드셨다니.{0,8}감사", "‘맛있게 드셨다니 감사합니다’"),
    (r"다음에도.{0,4}찾아", "‘다음에도 찾아주세요’"),
    (r"언제든.{0,4}찾아주세요", "‘언제든 찾아주세요’"),
    (r"또.?찾아주세요", "‘또 찾아주세요’"),
    (r"소중한.{0,3}(리뷰|의견|후기|말씀).{0,4}감사", "‘소중한 리뷰 감사합니다’ 계열"),
    (r"정성(껏|을다해|스럽게|을담아)", "‘정성껏 ~하겠습니다’ 상투구"),
    (r"최선을다하", "‘최선을 다하겠습니다’ (매크로 상투구)"),
    (r"기대에부응", "‘기대에 부응하겠습니다’ (매크로 상투구)"),
    (r"더나은모습으로", "‘더 나은 모습으로 보답하겠습니다’ (매크로 상투구)"),
]

# 긍정 리뷰 답변에만 추가로 막는 표현.
# 위의 목록만 막으면 모델이 곧바로 다음 정형구로 갈아탄다. 실제 생성 결과에서
# 답변 3건이 전부 "~하셨다니 기쁩니다 … 노력하겠습니다"로 나온 것을 보고 추가했다.
BANNED_PATTERNS_POSITIVE = [
    (r"(기쁩니다|기쁘네요|기뻐요|기쁜마음|기쁠따름|행복합니다|뿌듯합니다|보람입니다|즐거운마음입니다)",
     "‘기쁩니다 / 뿌듯합니다’ 감정 보고 정형구"),
    (r"(셨다니|주셔서|하셨|드셨|셨네요|셨군요).{0,12}(기쁘|기뻐|다행|보람|뿌듯|행복)",
     "‘~하셨다니 기쁩니다’ 감정 보고 정형구"),
    (r"(노력|보답)(하겠습니다|하고있|중입니다|합니다)", "‘노력하겠습니다’ 다짐 정형구"),
    (r"힘(을)?받습니다|힘이납니다", "‘힘 받습니다’ 정형구"),
    (r"큰(힘|보람)이(됩|되)", "‘큰 힘이 됩니다’ 정형구"),
    (r"보람입니다", "‘보람입니다’ 정형구"),
    (r"말씀해주셔서.{0,4}감사", "‘말씀해 주셔서 감사합니다’"),
    (r"남겨주셔서.{0,6}감사", "‘리뷰 남겨주셔서 감사합니다’"),
]

# 부정 리뷰 답변에만 추가로 막는 표현.
BANNED_PATTERNS_NEGATIVE = [
    (r"불편을드려.{0,6}죄송", "‘불편을 드려 죄송합니다’"),
    (r"빠른시일내", "‘빠른 시일 내 조치하겠습니다’"),
    (r"불편을드린점", "‘불편을 드린 점’ 상투구"),
]

EMOJI = re.compile(
    "[\U0001F300-\U0001FAFF\U00002600-\U000027BF\U0001F1E6-\U0001F1FF⬀-⯿️]"
)

_SENTENCE_END = re.compile(r"(?<=[.!?~])\s+|\n+")
_NON_WORD = re.compile(r"[^0-9A-Za-z가-힣]+")


def _flatten(text: str) -> str:
    """공백·이모지·문장부호를 지운 비교용 문자열."""
    text = unicodedata.normalize("NFKC", text)
    text = EMOJI.sub("", text)
    return _NON_WORD.sub("", text)


def first_sentence(reply: str) -> str:
    """답변의 첫 문장. 첫 줄이 짧은 인사면 다음 문장까지 붙이지 않고 그대로 본다."""
    stripped = reply.strip()
    if not stripped:
        return ""
    parts = [p.strip() for p in _SENTENCE_END.split(stripped) if _flatten(p)]
    return parts[0] if parts else stripped


def last_sentence(reply: str) -> str:
    """답변의 마지막 문장. 끝맺음이 매번 똑같아지는 것도 매크로로 읽힌다."""
    stripped = reply.strip()
    if not stripped:
        return ""
    parts = [p.strip() for p in _SENTENCE_END.split(stripped) if _flatten(p)]
    return parts[-1] if parts else stripped


# 첫 문장의 어미 형태. 내용어가 달라도 골격이 같으면 매크로로 읽힌다.
# ("새우고추짬뽕을 선택하셨네요" / "아침에 짬뽕을 선택하셨군요" / "짬뽕을 드셨군요")
OPENING_SHAPES = [
    (re.compile(r"(셨|시)(네요|군요|구나|죠)[.!~]?$"), "손님 행동 확인형(‘~하셨네요/셨군요’)"),
    (re.compile(r"(하|드|이)?셨(어요|습니다)[.!~]?$"), "손님 행동 서술형(‘~하셨습니다/셨어요’)"),
    (re.compile(r"(이|가|은|는)?\s?(맛있|좋)(죠|지요|네요)[.!~]?$"), "동의 유도형(‘~맛있죠’)"),
]


def opening_shape(sentence: str) -> str:
    """첫 문장의 골격 이름. 없으면 빈 문자열."""
    text = EMOJI.sub("", sentence).strip()
    for pattern, label in OPENING_SHAPES:
        if pattern.search(text):
            return label
    return ""


def _bigrams(text: str) -> set:
    return {text[i:i + 2] for i in range(len(text) - 1)} or {text}


def openings_collide(a: str, b: str, threshold: float = 0.55) -> bool:
    """두 첫 문장이 사실상 같은 문장인지."""
    fa, fb = _flatten(a), _flatten(b)
    if not fa or not fb:
        return False
    if fa == fb:
        return True
    # 짧은 쪽이 긴 쪽에 통째로 들어가면 같은 인사말의 길이 변형이다.
    if len(fa) >= 8 and len(fb) >= 8 and (fa in fb or fb in fa):
        return True
    ba, bb = _bigrams(fa), _bigrams(fb)
    return len(ba & bb) / len(ba | bb) >= threshold


def find_violations(
    reply: str,
    store_name: str,
    *,
    min_chars: int | None = None,
    max_chars: int | None = None,
    max_emoji: int = 1,
    negative: bool = False,
    avoid_openings: list[str] | None = None,
    avoid_closings: list[str] | None = None,
    avoid_shapes: list[str] | None = None,
) -> list[str]:
    """규칙 위반 목록. 비어 있으면 통과."""
    problems: list[str] = []
    flat = _flatten(reply)

    patterns = BANNED_PATTERNS + (
        BANNED_PATTERNS_NEGATIVE if negative else BANNED_PATTERNS_POSITIVE
    )
    for pattern, label in patterns:
        match = re.search(pattern, flat)
        if match:
            # 걸린 조각을 함께 알려 줘야 모델이 무엇을 지울지 안다.
            problems.append(f"금지 표현 사용: {label} — 걸린 부분: “{match.group(0)}”")

    opening = first_sentence(reply)
    store_flat = _flatten(store_name)
    if store_flat and store_flat in _flatten(opening):
        problems.append("첫 문장에 매장 이름이 들어감 — 매장명으로 시작하는 인사 금지")

    emoji_count = len(EMOJI.findall(reply))
    if emoji_count > max_emoji:
        problems.append(f"이모지 {emoji_count}개 — 최대 {max_emoji}개")

    length = len(reply.strip())
    if min_chars and length < min_chars:
        problems.append(f"{length}자 — {min_chars}자 이상이어야 함")
    if max_chars and length > max_chars:
        problems.append(f"{length}자 — {max_chars}자 이하여야 함")

    for used in avoid_openings or []:
        if openings_collide(opening, used):
            problems.append(f"이미 쓴 첫 문장과 겹침: “{used[:30]}”")
            break

    shape = opening_shape(opening)
    if shape and shape in (avoid_shapes or []):
        problems.append(f"이미 쓴 첫 문장 골격과 같음: {shape}")

    closing = last_sentence(reply)
    for used in avoid_closings or []:
        if openings_collide(closing, used):
            problems.append(f"이미 쓴 끝 문장과 겹침: “{used[:30]}”")
            break

    return problems
