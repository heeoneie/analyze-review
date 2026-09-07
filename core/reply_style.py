"""사장님이 실제로 게시한 답글에서 말투를 뽑아낸다.

few-shot 예시를 프롬프트에 넣는 것만으로는 말투가 따라오지 않는다. 검사기가
강제하는 길이가 사장님이 쓰는 길이와 다르면, 짧게 쓴 답글이 규칙 위반으로
걸려 길어질 때까지 재생성된다. 실제로 도입 매장의 답글은 긍정 30자·부정
70자 안팎인데 기본값은 긍정 100~200자·부정 130~250자였다. 예시를 아무리
넣어도 세 배 긴 글이 나온다.

그래서 예시와 함께 **길이 기준도 표본에서 뽑는다**. 표본이 모자라면 기존
기본값을 그대로 쓴다 — 새로 가입한 사장님의 답글이 갑자기 달라지면 안 된다.

DB 를 모르는 순수 함수로 둔다. 라우터가 ReplySample 을 평범한 dict 로
바꿔서 넘긴다.
"""

from dataclasses import dataclass

# 이 개수 미만이면 표본을 신뢰하지 않고 기본값으로 간다. 한두 건으로 폭을
# 정하면 우연히 길었던 답글 하나가 기준이 된다.
MIN_SAMPLES_FOR_LENGTH = 2

# 표본 길이에 주는 여유. 사장님도 매번 같은 길이로 쓰지는 않는다.
LOWER_SLACK = 0.7
UPPER_SLACK = 1.4

# 여유를 줘도 이보다 짧으면 답글 구실을 못 한다.
FLOOR_CHARS = 20

# 프롬프트에 넣을 예시 개수 상한. 더 넣어도 나아지지 않고 토큰만 든다.
MAX_EXAMPLES_IN_PROMPT = 6

# 인사말 습관으로 인정할 최소 비율. 절반을 넘게 같은 말로 시작하면 습관이다.
OPENING_HABIT_RATIO = 0.5

# 인사말로 볼 앞머리 어절 수. "죄송합니다 고객님" 처럼 두 어절이 흔하다.
OPENING_WORDS = 2


@dataclass(frozen=True)
class StyleProfile:
    """한 매장의 말투 요약.

    examples : 프롬프트에 넣을 (리뷰, 답글) 짝
    min_chars/max_chars : 표본에서 뽑은 길이 기준. 표본이 모자라면 None 이고
                          그때는 부르는 쪽이 기본값을 쓴다.
    """

    examples: tuple[dict, ...] = ()
    min_chars: int | None = None
    max_chars: int | None = None
    # 표본 과반이 같은 말로 시작하면 그 인사말. 없으면 None.
    common_opening: str | None = None

    def __bool__(self) -> bool:
        return bool(self.examples)


def _common_opening(replies: list[str]) -> str | None:
    """표본 과반이 공유하는 첫머리.

    예시만 보여 주면 모델이 사장님 인사말을 자주 흘린다. 습관이 분명하면
    따로 뽑아서 "이렇게 시작하라" 고 못박는 편이 확실하다.
    """
    heads = []
    for reply in replies:
        words = reply.strip().split()
        if len(words) >= OPENING_WORDS:
            heads.append(" ".join(words[:OPENING_WORDS]))

    if not heads:
        return None

    top = max(set(heads), key=heads.count)
    if heads.count(top) / len(replies) > OPENING_HABIT_RATIO:
        return top
    return None


def _lengths(samples: list[dict]) -> list[int]:
    return [len(s["reply"].strip()) for s in samples if s.get("reply", "").strip()]


def build_profile(samples: list[dict]) -> StyleProfile:
    """같은 성향(긍정/부정)의 표본에서 말투 프로필을 만든다.

    samples 는 최근 것이 앞에 오도록 이미 정렬돼 있다고 본다
    (`reply_history.style_examples` 가 고쳐 쓴 답글을 앞에 놓는다).
    각 항목은 {"review": str, "rating": int, "reply": str} 이다.
    """
    usable = [s for s in samples if s.get("reply", "").strip()]
    if not usable:
        return StyleProfile()

    examples = tuple(usable[:MAX_EXAMPLES_IN_PROMPT])

    replies = [s["reply"].strip() for s in usable]
    opening = _common_opening(replies)

    lengths = _lengths(usable)
    if len(lengths) < MIN_SAMPLES_FOR_LENGTH:
        # 예시는 주되 길이 기준은 건드리지 않는다.
        return StyleProfile(examples=examples, common_opening=opening)

    low = max(FLOOR_CHARS, int(min(lengths) * LOWER_SLACK))
    high = int(max(lengths) * UPPER_SLACK)
    # 표본이 전부 같은 길이여도 폭이 0 이 되면 안 된다.
    if high <= low:
        high = low + FLOOR_CHARS

    return StyleProfile(
        examples=examples, min_chars=low, max_chars=high, common_opening=opening,
    )


def prompt_block(profile: StyleProfile) -> str:
    """프롬프트에 붙일 말투 예시 블록. 예시가 없으면 빈 문자열."""
    if not profile:
        return ""

    lines = [
        "\n## 이 사장님이 실제로 단 답글 (말투를 그대로 따를 것)",
        "아래는 이 매장 사장님이 손님에게 직접 올린 답글이다. 인사말 습관,",
        "문장 길이, 자주 쓰는 표현, 마무리 방식을 그대로 가져와라. 내용은",
        "이번 리뷰에 맞게 새로 쓰되 **말투는 아래와 같아야 한다**.",
        "",
        "맞춤법이나 띄어쓰기를 사장님보다 더 반듯하게 고치지 마라. 다만",
        "일부러 틀리게 쓰지도 마라 — 문장 구조와 표현을 따르라는 뜻이다.",
        "",
    ]
    for i, ex in enumerate(profile.examples, 1):
        review = (ex.get("review") or "").strip() or "(리뷰 본문 없음)"
        lines.append(f"{i}) 손님 리뷰: {review}")
        lines.append(f"   사장님 답글: {ex['reply'].strip()}")

    if profile.common_opening:
        lines.append("")
        lines.append(
            f'이 사장님은 답글을 거의 항상 "{profile.common_opening}" 로 시작한다. '
            "이번 답글도 그렇게 시작하라."
        )
    lines.append("")
    return "\n".join(lines)
