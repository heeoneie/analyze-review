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


def test_run_on_replies_under_report_repetition():
    """알고 있는 한계다. 과소평가 방향이라 그대로 둔다.

    `first_sentence` 는 구두점이나 줄바꿈이 있어야 문장을 끊는다. 한 줄로
    쭉 이어 쓴 답글은 통째로 한 문장이 되고, 뒷부분이 다르면 다른 인사말로
    세어진다. 즉 이 지표는 반복을 **덜** 잡을 수는 있어도 없는 반복을
    지어내지는 않는다. "매크로가 아니다" 를 이 숫자만으로 주장하지 않는다.
    """
    replies = [
        "감사합니다 고객님 다음에도 잘 부탁드립니다",
        "감사합니다 고객님 또 방문해 주세요",
    ]
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
            finalized_at=BASE + timedelta(days=i),
        ))
    return out


def test_curve_buckets_by_samples_available_at_the_time():
    points = style_fit.learning_curve(_series(12, rating=5, edited_upto=12))
    labels = [p.label for p in points]
    assert labels == ["0-1", "2-4", "5-9", "10+"]
    assert [p.stats.total for p in points] == [2, 3, 5, 2]


def test_curve_falls_when_the_style_starts_landing():
    # 앞 2건은 고쳤고(학습 꺼진 구간) 나머지는 그대로 게시했다.
    points = style_fit.learning_curve(_series(12, rating=5, edited_upto=2))
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
                               finalized_at=BASE + timedelta(days=i)))
    samples.append(_sample("긍1", rating=5, finalized_at=BASE + timedelta(days=20)))

    points = style_fit.learning_curve(samples, positive=True)
    # 긍정은 한 건뿐이고 그 앞에 쌓인 긍정 표본은 0건이다.
    assert points[0].stats.total == 1
    assert sum(p.stats.total for p in points[1:]) == 0


def test_unposted_drafts_do_not_grow_the_pool():
    """`style_examples` 가 final_reply 있는 행만 쓰므로 여기도 같아야 한다.

    다르면 곡선의 x축이 실제로 프롬프트에 들어간 표본 수와 어긋난다.
    """
    samples = [
        _sample("가", final_reply=None, finalized_at=BASE),
        _sample("나", final_reply=None, finalized_at=BASE + timedelta(days=1)),
        _sample("다", finalized_at=BASE + timedelta(days=2)),
    ]
    points = style_fit.learning_curve(samples)
    # 앞 두 건이 풀에 안 쌓이므로 '다' 는 여전히 표본 0건 구간이다.
    assert points[0].stats.total == 1
    assert points[0].stats.edited == 0


def test_rows_without_a_finalized_time_are_skipped():
    samples = [_sample("가", finalized_at=None), _sample("나")]
    points = style_fit.learning_curve(samples)
    assert sum(p.stats.total for p in points) == 1
