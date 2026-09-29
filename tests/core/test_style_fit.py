"""말투 적합도 지표 테스트.

리뷰·답글 문장은 전부 지어낸 것이다. 실제 손님 리뷰는 테스트 픽스처에도
쓰지 않는다 (CLAUDE.md).
"""

from datetime import datetime, timedelta, timezone

import pytest

from core import style_fit

BASE = datetime(2026, 1, 1, tzinfo=timezone.utc)


def _sample(prefix, **kw):
    """기본값이 채워진 표본 하나. 필요한 필드만 덮어쓴다."""
    base = {
        "origin": "generated",
        "rating": 5,
        "generated_reply": f"{prefix} 생성본입니다",
        "final_reply": f"{prefix} 생성본입니다",
        "created_at": BASE,
        "finalized_at": BASE,
    }
    base.update(kw)
    return base


# ── Wilson 구간 ────────────────────────────────────────────

def test_wilson_keeps_width_at_zero_percent():
    """정규근사를 썼다면 여기서 (0.0, 0.0) 이 나온다."""
    low, high = style_fit.wilson_interval(0, 5)
    assert low == 0.0
    assert high > 0.4, "표본 5건으로 '편집률 0%, 오차 없음' 이라고 말하면 안 된다"


def test_wilson_keeps_width_at_full_percent():
    low, high = style_fit.wilson_interval(5, 5)
    assert high == 1.0
    assert low < 0.6


def test_wilson_knows_nothing_without_samples():
    assert style_fit.wilson_interval(0, 0) == (0.0, 1.0)


def test_wilson_narrows_as_samples_grow():
    _, wide = style_fit.wilson_interval(5, 10)
    _, narrow = style_fit.wilson_interval(50, 100)
    assert narrow < wide


# ── 편집률 ─────────────────────────────────────────────────

def test_edit_rate_counts_only_changed_replies():
    samples = [
        _sample("가", final_reply="가 생성본입니다"),      # 그대로
        _sample("나", final_reply="나 고쳐 썼습니다"),      # 고침
        _sample("다", final_reply="다 생성본입니다"),      # 그대로
        _sample("라", final_reply="라 완전히 다시 씀"),    # 고침
    ]
    stats = style_fit.edit_stats(samples)
    assert stats.total == 4
    assert stats.edited == 2
    assert stats.rate == 0.5


def test_onboarding_rows_are_not_counted():
    """생성본이 없어 '고쳤는가' 가 정의되지 않는다.

    이걸 편집 0건으로 세면 온보딩을 많이 시킨 매장일수록 편집률이 좋아 보인다.
    """
    samples = [
        _sample("가", origin="onboarding", generated_reply=None,
                final_reply="사장님이 직접 쓴 답글입니다"),
        _sample("나", final_reply="나 고쳐 썼습니다"),
    ]
    stats = style_fit.edit_stats(samples)
    assert stats.total == 1
    assert stats.rate == 1.0


def test_onboarding_rows_are_excluded_even_with_a_generated_reply():
    """생성본이 비어 있다는 우연에 기대지 않는다 — `origin` 으로 거른다."""
    samples = [
        _sample("가", origin="onboarding",
                generated_reply="가 생성본입니다",
                final_reply="가 생성본입니다"),
        _sample("나", final_reply="나 고쳐 썼습니다"),
    ]
    stats = style_fit.edit_stats(samples)
    assert stats.total == 1
    assert stats.edited == 1


def test_unposted_drafts_are_not_counted():
    """채택 근거가 없다. '안 고쳤다' 로 세면 화면을 닫은 경우가 전부 성공이 된다."""
    samples = [
        _sample("가", final_reply=None),
        _sample("나", final_reply=""),
        _sample("다", final_reply="다 고쳐 썼습니다"),
    ]
    stats = style_fit.edit_stats(samples)
    assert stats.total == 1
    assert stats.edited == 1


def test_rate_is_none_without_samples():
    """0.0 이 아니다. 0% 는 '한 번도 안 고쳤다' 는 뜻이고 전혀 다른 말이다."""
    stats = style_fit.edit_stats([])
    assert stats.rate is None
    assert stats.total == 0


def test_small_samples_are_not_citable():
    stats = style_fit.edit_stats([_sample(str(i)) for i in range(9)])
    assert stats.citable is False
    stats = style_fit.edit_stats([_sample(str(i)) for i in range(10)])
    assert stats.citable is True


def test_similarity_separates_a_tweak_from_a_rewrite():
    tweaked = style_fit.edit_stats([
        _sample("가", generated_reply="맛있게 드셨다니 기쁩니다",
                final_reply="맛있게 드셨다니 기뻐요"),
    ])
    rewritten = style_fit.edit_stats([
        _sample("나", generated_reply="맛있게 드셨다니 기쁩니다",
                final_reply="다음에 또 들러 주세요 사장 올림"),
    ])
    assert tweaked.rate == rewritten.rate == 1.0, "편집률만으로는 둘이 구분되지 않는다"
    assert tweaked.median_similarity_when_edited > rewritten.median_similarity_when_edited


def test_similarity_is_none_when_nothing_was_edited():
    """0.0 은 '통째로 다시 썼다' 는 뜻이라 여기에 쓰면 정반대로 읽힌다."""
    stats = style_fit.edit_stats([_sample("가"), _sample("나")])
    assert stats.edited == 0
    assert stats.median_similarity_when_edited is None


# ── 반복률 ─────────────────────────────────────────────────

def test_same_greeting_forms_one_cluster():
    replies = [
        "감사합니다 고객님. 다음에도 잘 부탁드립니다.",
        "감사합니다 고객님. 또 방문해 주세요.",
        "감사합니다 고객님. 좋은 하루 보내세요.",
    ]
    stats = style_fit.repetition(replies)
    assert stats.distinct_openings == 1
    assert stats.top_opening_share == 1.0


def test_greeting_on_its_own_line_still_clusters():
    """사장님은 인사말을 따로 한 줄로 올리는 일이 흔하다."""
    replies = [
        "감사합니다 고객님\n다음에도 잘 부탁드립니다",
        "감사합니다 고객님\n또 방문해 주세요",
    ]
    stats = style_fit.repetition(replies)
    assert stats.distinct_openings == 1


def test_varied_openings_split_into_clusters():
    replies = [
        "감사합니다 고객님. 다음에도 잘 부탁드립니다.",
        "짜장면이 입에 맞으셨다니 다행입니다. 또 들러 주세요.",
        "비 오는 날 찾아 주셔서 고맙습니다. 따뜻하게 보내세요.",
    ]
    stats = style_fit.repetition(replies)
    assert stats.distinct_openings == 3
    assert stats.top_opening_share == pytest.approx(1 / 3)


def test_closings_are_measured_too():
    """첫 문장만 흩어 놓고 끝을 매번 같게 닫으면 손님이 받는 인상은 그대로다."""
    replies = [
        "짜장면 맛있게 드셨군요. 감사합니다.",
        "비 오는 날 주문 고맙습니다. 감사합니다.",
        "짬뽕이 입에 맞으셨다니 좋습니다. 감사합니다.",
    ]
    stats = style_fit.repetition(replies)
    assert stats.distinct_openings == 3
    assert stats.top_closing_share == 1.0


def test_run_on_replies_still_cluster_by_their_first_words():
    """구두점 없이 이어 쓴 답글도 앞 두 어절이 같으면 같은 인사말 계열이다.

    `first_sentence` 는 구두점이나 줄바꿈이 있어야 문장을 끊어서 한 줄로 쭉
    이어 쓴 답글은 통째로 한 문장이 된다. 열쇠가 앞 두 어절이라 그래도 묶인다.
    """
    replies = [
        "감사합니다 고객님 다음에도 잘 부탁드립니다",
        "감사합니다 고객님 또 방문해 주세요",
    ]
    assert style_fit.repetition(replies).distinct_openings == 1


def test_same_words_in_a_different_order_are_a_different_family():
    """알고 있는 한계다. 과소평가 방향이라 그대로 둔다.

    앞 두 어절이 열쇠라 "감사합니다 고객님" 과 "고객님 감사합니다" 는 다른
    계열로 센다. 이 지표는 반복을 **덜** 잡을 수는 있어도 없는 반복을
    지어내지는 않는다. "매크로가 아니다" 를 이 숫자만으로 주장하지 않는다.
    """
    replies = ["감사합니다 고객님. 또 오세요.", "고객님 감사합니다. 또 오세요."]
    assert style_fit.repetition(replies).distinct_openings == 2


def test_blank_replies_are_not_counted():
    stats = style_fit.repetition(["", "   ", "감사합니다 고객님"])
    assert stats.total == 1


def test_repetition_is_none_without_replies():
    stats = style_fit.repetition([])
    assert stats.top_opening_share is None
    assert stats.total == 0


# ── 학습 곡선 ──────────────────────────────────────────────

def _series(count, *, rating, edited_upto):
    """시간순 표본 count 건. 앞 edited_upto 건은 사장님이 고쳤다."""
    out = []
    for i in range(count):
        gen = f"{i}번 생성본입니다"
        out.append(_sample(
            str(i),
            rating=rating,
            generated_reply=gen,
            final_reply=f"{i}번 고쳐 썼습니다" if i < edited_upto else gen,
            created_at=BASE + timedelta(days=i),
            finalized_at=BASE + timedelta(days=i, hours=1),
        ))
    return out


def test_curve_buckets_by_samples_available_at_the_time():
    points = style_fit.learning_curve(_series(12, rating=5, edited_upto=12))
    labels = [p.label for p in points]
    assert labels == ["0", "1-4", "5-9", "10+"]
    assert [p.stats.total for p in points] == [1, 4, 5, 2]


def test_the_baseline_bucket_is_zero_samples_only():
    """표본 1건이면 이미 예시와 인사말이 프롬프트에 들어간다.

    `reply_style` 은 1/1 도 인사말 습관으로 인정한다(OPENING_HABIT_RATIO 0.5
    초과). 0 과 1 을 한 구간으로 묶으면 학습이 걸린 답글이 "학습 꺼진 기준선"
    에 섞인다.
    """
    points = style_fit.learning_curve(_series(2, rating=5, edited_upto=1))
    assert points[0].label == "0"
    assert points[0].stats.total == 1
    assert points[0].stats.edited == 1
    assert points[1].stats.total == 1
    assert points[1].stats.edited == 0


def test_curve_falls_when_the_style_starts_landing():
    # 첫 건은 고쳤고(학습 꺼진 구간) 나머지는 그대로 게시했다.
    points = style_fit.learning_curve(_series(12, rating=5, edited_upto=1))
    first_bucket = points[0].stats
    last_bucket = points[-1].stats
    assert first_bucket.rate == 1.0
    assert last_bucket.rate == 0.0


def test_curve_keeps_polarities_apart():
    """긍정 답글을 만들 때 부정 표본 20건은 도움이 되지 않는다.

    섞어서 세면 긍정 1건짜리 매장이 '표본 21건' 구간에 들어가 버린다.
    """
    samples = []
    for i in range(10):
        samples.append(_sample(f"부{i}", rating=2,
                               created_at=BASE + timedelta(days=i),
                               finalized_at=BASE + timedelta(days=i, hours=1)))
    samples.append(_sample("긍1", rating=5,
                           created_at=BASE + timedelta(days=20),
                           finalized_at=BASE + timedelta(days=20, hours=1)))

    points = style_fit.learning_curve(samples, positive=True)
    # 긍정은 한 건뿐이고 그 앞에 쌓인 긍정 표본은 0건이다.
    assert points[0].stats.total == 1
    assert sum(p.stats.total for p in points[1:]) == 0


def test_unposted_drafts_do_not_grow_the_pool():
    """`style_examples` 가 final_reply 있는 행만 쓰므로 여기도 같아야 한다.

    다르면 곡선의 x축이 실제로 프롬프트에 들어간 표본 수와 어긋난다.
    """
    samples = [
        _sample("가", final_reply=None, created_at=BASE, finalized_at=None),
        _sample("나", final_reply=None,
                created_at=BASE + timedelta(days=1), finalized_at=None),
        _sample("다", created_at=BASE + timedelta(days=2),
                finalized_at=BASE + timedelta(days=2, hours=1)),
    ]
    points = style_fit.learning_curve(samples)
    # 앞 두 건이 풀에 안 쌓이므로 '다' 는 여전히 표본 0건 구간이다.
    assert points[0].stats.total == 1
    assert points[0].stats.edited == 0


def test_rows_without_a_created_time_are_skipped():
    """언제 만들었는지 모르면 그 시점의 표본 수도 알 수 없다."""
    samples = [_sample("가", created_at=None), _sample("나")]
    points = style_fit.learning_curve(samples)
    assert sum(p.stats.total for p in points) == 1


def test_batch_generation_does_not_fabricate_a_curve():
    """한꺼번에 만들고 하나씩 게시해도 학습 곡선이 생기면 안 된다.

    게시 시각으로 줄을 세우면 여기서 0·1·2·3·4 건 구간이 만들어지고,
    뒤쪽이 수정 없이 올라갔으므로 이 리포트가 찾으려는 하향 곡선이 그대로
    그려진다. 학습이 전혀 걸리지 않은 데이터인데도.
    """
    made = BASE
    samples = [
        _sample(
            str(i),
            generated_reply=f"{i}번 생성본입니다",
            final_reply=f"{i}번 생성본입니다",
            created_at=made,                                   # 전부 같은 순간에 생성
            finalized_at=BASE + timedelta(days=1, hours=i),     # 게시는 하루 뒤 순차
        )
        for i in range(5)
    ]
    points = style_fit.learning_curve(samples)
    # 만든 시점에는 게시된 표본이 0건이었다. 전부 첫 구간에 들어가야 한다.
    assert points[0].stats.total == 5
    assert sum(p.stats.total for p in points[1:]) == 0


def test_prior_count_uses_replies_posted_before_generation():
    """생성 전에 이미 게시돼 있던 답글만 그 시점의 표본으로 센다.

    하루에 한 건씩 만들고 곧바로 게시하면 n번째 답글의 표본은 n-1 건이다.
    0번은 0 구간, 1번과 그 뒤는 1-4 구간에 들어간다.
    """
    daily = [
        _sample(f"이전{i}",
                created_at=BASE + timedelta(days=i),
                finalized_at=BASE + timedelta(days=i, hours=1))
        for i in range(3)
    ]
    later = _sample("나중", created_at=BASE + timedelta(days=10),
                    finalized_at=BASE + timedelta(days=10, hours=1))
    points = style_fit.learning_curve(daily + [later])
    assert {p.label: p.stats.total for p in points} == {
        "0": 1, "1-4": 3, "5-9": 0, "10+": 0,
    }


# 유사도로 묶던 때 군집이 순서에 휘둘리던 세 문장. 열쇠(앞 두 어절)로 세면
# A 와 B 가 한 계열이고 C 는 따로다 — 어느 순서로 넣어도 같다.
_A = "감사합니다 고객님 진심으로 감사드립니다"
_B = "감사합니다 고객님"
_C = "고객님 안녕하세요 반갑습니다 감사합니다 고객님"


def test_repetition_does_not_depend_on_input_order():
    """같은 데이터에서 같은 숫자가 나와야 한다. 기준선과 나란히 읽는 값이다."""
    assert style_fit.repetition([_A, _B, _C]) == style_fit.repetition([_B, _A, _C])
    assert style_fit.repetition([_C, _B, _A]) == style_fit.repetition([_A, _B, _C])
    assert style_fit.repetition([_A, _B, _C]).top_opening_share == pytest.approx(2 / 3)


def test_adding_an_unrelated_reply_does_not_regroup_the_others():
    """행 하나가 늘어도 기존 문장들의 군집은 그대로여야 한다.

    유사도로 탐욕 군집화할 때는 새 문장이 먼저 대표가 되면서 기존 짝을
    갈라놓았다. 달마다 뽑는 숫자가 사장님 습관과 무관하게 흔들리는 원인이었다.
    """
    pair = ["리뷰 감사드립니다. 또 오세요.", "리뷰 감사드립니다. 좋은 하루 되세요."]
    before = style_fit.repetition(pair)
    after = style_fit.repetition(pair + ["감사드립니다 리뷰 항상. 또 오세요."])
    assert before.distinct_openings == 1
    assert after.distinct_openings == 2
    assert max(before.top_opening_share * 2, 0) == after.top_opening_share * 3


def test_emoji_only_replies_count_as_repetition():
    """'👍' 만으로 답한 답글 세 건은 같은 인사말 세 번이다. 세 종류가 아니다."""
    stats = style_fit.repetition(["👍", "👍", "👍"])
    assert stats.distinct_openings == 1
    assert stats.top_opening_share == 1.0


def test_leading_emoji_does_not_split_the_family():
    replies = ["😊 감사합니다 고객님. 또 오세요.", "감사합니다 고객님! 또 오세요."]
    assert style_fit.repetition(replies).distinct_openings == 1


def test_similarity_survives_long_repetitive_replies():
    """200자를 넘는 되풀이 문장에서 어절 순서만 바꿔도 크게 고친 것으로 읽히면 안 된다.

    `SequenceMatcher` 의 autojunk 는 200자부터 "1% 넘게 나오는 글자" 를 잡동사니로
    취급한다. 같은 인사말이 되풀이되는 답글은 모든 글자가 그 기준에 걸려서,
    사장님이 마지막 인사말의 어절 순서만 바꿔도 유사도가 0.88 로 떨어졌다.
    """
    phrase = "감사합니다 고객님 오늘도 주문해 주셔서 정말 고맙습니다 "
    generated = (phrase * 8).strip()
    final = (phrase * 7 + "고객님 감사합니다 오늘도 주문해 주셔서 정말 고맙습니다").strip()
    assert len(generated) > 200
    assert style_fit.similarity(generated, final) > 0.95
