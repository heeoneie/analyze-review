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

from bisect import bisect_left
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

    `openings_collide` 는 이행적이지 않다 — A~B 이고 B~C 여도 A~C 는 아닐 수
    있다. 그래서 군집을 만들 때 **이미 들어 있는 모든 문장과 충돌해야** 넣는다
    (대표 하나와만 비교하지 않는다). 두 가지가 여기에 걸려 있다.

    첫째, 군집이 전부 서로 충돌하는 무리가 되므로 `top_opening_share` 가
    실제보다 큰 값이 되지 않는다. 대표와만 비교하면 A~C 가 아닌데도 B 를
    거쳐 한 군집에 들어간다. 실제로 그렇게 됐었다:

        A="감사합니다 고객님 진심으로 감사드립니다"
        B="감사합니다 고객님"
        C="고객님 안녕하세요 반갑습니다 감사합니다 고객님"
        (A~B 참, B~C 참, A~C 거짓)

        입력 [A,B,C] → 최다 군집 66.7%
        입력 [B,A,C] → 최다 군집 100.0%    ← 같은 데이터, 다른 숫자

    둘째, 그래서 입력 순서에 따라 결과가 흔들렸다. 이 값은 매크로 기준선
    31% 와 나란히 놓고 읽는 숫자라 행 순서로 바뀌면 안 된다. 들어온 순서를
    먼저 정렬해 결과를 고정한다.
    """
    clusters: list[list[str]] = []
    for sentence in sorted(sentences):
        for members in clusters:
            if all(openings_collide(sentence, m) for m in members):
                members.append(sentence)
                break
        else:
            clusters.append([sentence])
    return [len(c) for c in clusters]


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

    각 답글을 **만든 시점**에 같은 성향의 게시된 표본이 몇 건 있었는지를 세어
    구간에 넣는다. 그 값이 곧 `reply_style.build_profile` 이 그때 받은 표본
    수다.

    ## 만든 시각으로 센다 — 게시한 시각이 아니다

    `created_at` 은 `record_generated` 가 찍고 `finalized_at` 은 `finalize`
    가 찍는다. 둘은 다른 순간이고, 프롬프트를 만든 것은 앞쪽이다.

    게시 시각으로 줄을 세우면 x축을 지어낼 수 있다. 사장님이 월요일에 리뷰
    다섯 건의 답글을 한꺼번에 만들면 다섯 건 모두 표본 0건으로 생성된다.
    그걸 화요일에 하나씩 올리면, 게시 순서만 보고 0·1·2·3·4 건으로 세어
    뒤쪽 세 건이 "표본 2-4건으로 만든 답글" 이 된다. 그것들이 수정 없이
    올라갔다면, 학습이 전혀 걸리지 않은 데이터에서 이 리포트가 찾으려는
    바로 그 하향 곡선이 그려진다.

    ## 성향을 나누는 이유

    생성 경로가 긍정·부정으로 갈리고 표본 풀도 따로 쓰인다. 섞으면 한쪽이
    많은 매장에서 다른 쪽의 학습 상태를 잘못 읽는다.

    ## 무엇을 풀로 세는가

    `final_reply` 가 빈 문자열이 아닌 행만 센다. `style_examples` 는 NULL 만
    거르지만 그 뒤 `build_profile` 이 빈 답글을 다시 걸러내므로, 프롬프트에
    실제로 들어간 수는 이쪽이다.

    이건 관측이지 실험이 아니다. 표본이 쌓이는 동안 프롬프트나 모델이 같이
    바뀌었으면 편집률 변화의 원인을 가를 수 없다.
    """
    drafts = [
        s for s in samples
        if s.get("created_at") is not None
        and (s.get("generated_reply") or "").strip()
    ]
    if positive is not None:
        drafts = [s for s in drafts if _is_positive(s["rating"]) == positive]

    # 성향별 게시 시각을 정렬해 두고, 답글을 만든 시각보다 앞선 것을 센다.
    posted: dict[bool, list] = {True: [], False: []}
    for sample in samples:
        if (sample.get("final_reply") or "").strip() and sample.get("finalized_at"):
            posted[_is_positive(sample["rating"])].append(sample["finalized_at"])
    for times in posted.values():
        times.sort()

    tagged = [
        (bisect_left(posted[_is_positive(d["rating"])], d["created_at"]), d)
        for d in drafts
    ]

    points = []
    for low, high in CURVE_BUCKETS:
        bucket = [
            s for prior, s in tagged
            if prior >= low and (high is None or prior <= high)
        ]
        points.append(CurvePoint(low=low, high=high, stats=edit_stats(bucket)))
    return points
