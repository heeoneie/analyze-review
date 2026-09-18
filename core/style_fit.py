"""답글이 사장님께 맞는지를 잰다 — 편집률과 반복률, 둘을 같이 본다.

말투 학습을 더 붙이기 전에 자가 필요하다. 지금도 예시·길이·인사말을 뽑아
프롬프트에 넣고는 있지만 그게 실제로 듣는지 재는 숫자가 없다. 숫자 없이
학습을 더 만들면 좋아졌다는 근거 없이 코드만 늘어난다.

## 편집률 — "맞았는가"

사장님이 생성본을 고치지 않고 그대로 게시했으면 맞은 것이고, 고쳤으면
어딘가 자기 말투가 아니었다는 뜻이다. 사람이 따로 라벨을 달 필요가 없고
쓰는 동안 저절로 쌓인다. `ReplySample` 의 `generated_reply`/`final_reply`
가 이미 그 데이터다.

## 반복률 — "매크로가 되지 않았는가"

편집률만 쫓으면 잘못된 곳으로 간다. 이 매장 사장님의 기존 답변 441건 중
131건(31%)이 같은 인사말 계열로 시작했고, 그게 손님에게 매크로로 읽히는
것이 애초에 이 도구를 만든 이유였다. 사장님 말투를 완벽하게 따라 하면 그
매크로를 그대로 복제한다. `reply_style.common_opening` 은 "이 사장님은 거의
항상 이렇게 시작한다" 를 프롬프트에 못박으므로 특히 그쪽으로 당긴다.

두 지표는 서로 반대로 당긴다. 하나만 보면 안 된다.

    편집률만 낮추면  → 사장님 매크로를 복제한다
    반복률만 낮추면  → 사장님 말투가 아니게 된다

## 이 지표가 증명하지 못하는 것

편집률은 **대리 지표**다. 사장님이 바빠서 그냥 게시했을 수도, 마음에 안
들지만 고치기 귀찮아서 넘겼을 수도 있다. 낮은 편집률이 "맞았다" 를 증명하지는
않는다. 반대 방향 — 편집률이 높으면 안 맞았다 — 이 훨씬 믿을 만하다.
리포트에 이 한계를 같이 적는다.

학습 곡선도 관측이지 실험이 아니다. 표본이 쌓이는 동안 프롬프트도 같이
바뀌었다면 무엇이 원인인지 가를 수 없다. 인과로 읽지 않는다.

DB 를 모르는 순수 함수로 둔다 — `core/reply_style.py` 와 같은 규칙이고,
부르는 쪽이 `ReplySample` 을 평범한 dict 로 바꿔서 넘긴다.
"""

from dataclasses import dataclass
from difflib import SequenceMatcher

from core import config
from core.reply_text import first_sentence, last_sentence, openings_collide

# 정규분포 양측 95%.
Z_95 = 1.959963984540054

# 표본이 이 수에 못 미치면 비율을 단일 값으로 인용하지 않는다. 3건 중 1건을
# 33% 라고 적으면 신뢰구간이 사실상 2~88% 인데 숫자만 남는다.
MIN_SAMPLES_TO_CITE = 10

# 학습 곡선 구간. 경계 2 는 임의가 아니다 — `reply_style.MIN_SAMPLES_FOR_LENGTH`
# 가 2라서, 표본이 그 아래면 길이 기준이 아예 안 걸리고 기본값으로 생성된다.
# 즉 0~1 구간은 "말투 학습이 꺼진 상태" 의 편집률이고 이게 기준선이 된다.
CURVE_BUCKETS = ((0, 1), (2, 4), (5, 9), (10, None))


def wilson_interval(successes: int, total: int, z: float = Z_95) -> tuple[float, float]:
    """이항 비율의 Wilson score 구간.

    정규근사(p ± z·√(p(1-p)/n))를 쓰지 않는다. 편집률이 0% 나 100% 에 붙는
    일이 흔한데 그때 정규근사는 폭이 0인 구간을 내놓는다. 표본 5건에서
    "편집률 0%, 오차 없음" 이 나오면 그 숫자를 믿게 된다.
    """
    if total <= 0:
        return (0.0, 1.0)
    p = successes / total
    denom = 1 + z * z / total
    center = (p + z * z / (2 * total)) / denom
    margin = z * ((p * (1 - p) / total + z * z / (4 * total * total)) ** 0.5) / denom
    return (max(0.0, center - margin), min(1.0, center + margin))


def similarity(generated: str, final: str) -> float:
    """생성본과 게시본이 얼마나 같은가. 1.0 이면 한 글자도 안 고쳤다.

    편집률은 고쳤는지 여부만 알려 준다. 조사 하나 바꾼 것과 통째로 다시 쓴
    것이 같은 1건으로 세어지면, 말투가 가까워지는 과정이 보이지 않는다.
    """
    a, b = (generated or "").strip(), (final or "").strip()
    if not a or not b:
        return 0.0
    return SequenceMatcher(None, a, b).ratio()


def _is_positive(rating: int) -> bool:
    return rating >= config.POSITIVE_RATING_THRESHOLD


@dataclass(frozen=True)
class EditStats:
    """편집률 한 덩어리.

    total 이 `MIN_SAMPLES_TO_CITE` 미만이면 `citable` 이 False 다. 그때
    `rate` 를 단독으로 인용하지 않고 구간과 같이 적는다.
    """

    total: int = 0
    edited: int = 0
    rate: float | None = None
    ci_low: float = 0.0
    ci_high: float = 1.0
    # 고쳐 쓴 답글에서 생성본이 얼마나 살아남았는지의 중앙값.
    # 고친 게 없으면 None — 0.0 이 아니다. 0.0 은 "통째로 다시 썼다" 는 뜻이다.
    median_similarity_when_edited: float | None = None

    @property
    def citable(self) -> bool:
        return self.total >= MIN_SAMPLES_TO_CITE


def _median(values: list[float]) -> float:
    ordered = sorted(values)
    mid = len(ordered) // 2
    if len(ordered) % 2:
        return ordered[mid]
    return (ordered[mid - 1] + ordered[mid]) / 2


def edit_stats(samples: list[dict]) -> EditStats:
    """생성본이 있고 게시된 답글만 세어 편집률을 낸다.

    세지 않는 것이 두 가지다.

    `origin == "onboarding"` — 생성본이 없다. 사장님이 처음부터 직접 쓴
    답글이라 "고쳤는가" 가 정의되지 않는다. 이걸 편집 0건으로 세면 온보딩을
    많이 시킨 매장일수록 편집률이 좋아 보인다.

    `final_reply` 가 빈 행 — 만들기만 하고 게시하지 않았다. 사장님이 채택
    했다는 근거가 없으므로 맞았는지 틀렸는지 알 수 없다. 이걸 "안 고쳤다"
    로 세면 화면을 닫아버린 경우가 전부 성공이 된다.
    """
    usable = [
        s for s in samples
        if (s.get("generated_reply") or "").strip()
        and (s.get("final_reply") or "").strip()
    ]
    if not usable:
        return EditStats()

    pairs = [
        (s["generated_reply"].strip(), s["final_reply"].strip()) for s in usable
    ]
    edited = [(g, f) for g, f in pairs if g != f]

    low, high = wilson_interval(len(edited), len(pairs))
    return EditStats(
        total=len(pairs),
        edited=len(edited),
        rate=len(edited) / len(pairs),
        ci_low=low,
        ci_high=high,
        median_similarity_when_edited=(
            _median([similarity(g, f) for g, f in edited]) if edited else None
        ),
    )


@dataclass(frozen=True)
class RepetitionStats:
    """같은 말로 시작하거나 끝나는 답글이 얼마나 되는가.

    `top_opening_share` 는 가장 큰 인사말 군집의 비율이다. README 에 적힌
    사장님 기존 답변의 31% 가 이 값의 기준선이다 — 우리가 만든 답글이 그보다
    높으면 매크로를 더 심하게 만든 것이다.
    """

    total: int = 0
    top_opening_share: float | None = None
    distinct_openings: int = 0
    top_closing_share: float | None = None
    distinct_closings: int = 0


def _cluster(sentences: list[str]) -> list[int]:
    """사실상 같은 문장끼리 묶고 각 군집의 크기를 돌려준다.

    `openings_collide` 는 이행적이지 않다 (A~B, B~C 여도 A~C 는 아닐 수 있다).
    그래서 완전한 군집화가 아니라 **먼저 만들어진 군집의 대표와 비교하는**
    탐욕적 방식이다. 군집 개수를 조금 많게 잡는 쪽으로 치우치므로,
    `top_opening_share` 는 실제 반복 정도를 과소평가할 수는 있어도
    과대평가하지는 않는다. 안전한 방향이다.
    """
    reps: list[str] = []
    sizes: list[int] = []
    for sentence in sentences:
        for i, rep in enumerate(reps):
            if openings_collide(sentence, rep):
                sizes[i] += 1
                break
        else:
            reps.append(sentence)
            sizes.append(1)
    return sizes


def repetition(replies: list[str]) -> RepetitionStats:
    """답글 묶음의 첫 문장·끝 문장 반복 정도.

    끝 문장도 같이 본다. 첫 문장만 흩어 놓고 끝을 매번 "감사합니다" 로
    닫으면 손님이 받는 인상은 그대로다.
    """
    usable = [r.strip() for r in replies if (r or "").strip()]
    if not usable:
        return RepetitionStats()

    openings = _cluster([first_sentence(r) for r in usable])
    closings = _cluster([last_sentence(r) for r in usable])

    return RepetitionStats(
        total=len(usable),
        top_opening_share=max(openings) / len(usable),
        distinct_openings=len(openings),
        top_closing_share=max(closings) / len(usable),
        distinct_closings=len(closings),
    )


@dataclass(frozen=True)
class CurvePoint:
    """표본이 N건 쌓였을 때 만든 답글들의 편집률."""

    low: int
    high: int | None
    stats: EditStats

    @property
    def label(self) -> str:
        return f"{self.low}+" if self.high is None else f"{self.low}-{self.high}"


def learning_curve(samples: list[dict], *, positive: bool | None = None) -> list[CurvePoint]:
    """"표본이 쌓일수록 덜 고치는가" 를 구간별로 본다.

    각 답글을 만든 시점에 **같은 성향의 확정 표본이 몇 건 있었는지**를 세어
    구간에 넣는다. 그 값이 곧 `reply_style.build_profile` 이 그때 받았을
    표본 수다. 성향을 나누는 이유는 생성 경로가 긍정·부정으로 갈리고 표본
    풀도 따로 쓰이기 때문이다 — 섞으면 한쪽이 많은 매장에서 다른 쪽의
    학습 상태를 잘못 읽는다.

    이건 관측이다. 표본이 쌓이는 동안 프롬프트나 모델이 같이 바뀌었으면
    편집률 변화의 원인을 가를 수 없다. 리포트에 그 기간을 같이 적는다.
    """
    dated = [s for s in samples if s.get("finalized_at") is not None]
    if positive is not None:
        dated = [s for s in dated if _is_positive(s["rating"]) == positive]
    dated.sort(key=lambda s: s["finalized_at"])

    # 성향별로 따로 센다. 긍정 답글을 만들 때 부정 표본 20건은 도움이 안 된다.
    seen: dict[bool, int] = {True: 0, False: 0}
    tagged: list[tuple[int, dict]] = []
    for sample in dated:
        polarity = _is_positive(sample["rating"])
        tagged.append((seen[polarity], sample))
        # 게시된 답글만 다음 표본 풀에 들어간다 (`style_examples` 와 같은 기준).
        if (sample.get("final_reply") or "").strip():
            seen[polarity] += 1

    points = []
    for low, high in CURVE_BUCKETS:
        bucket = [
            s for prior, s in tagged
            if prior >= low and (high is None or prior <= high)
        ]
        points.append(CurvePoint(low=low, high=high, stats=edit_stats(bucket)))
    return points
