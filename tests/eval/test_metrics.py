"""채점 테스트 — 숫자가 조용히 틀리는 것을 막는다.

여기서 잡는 것은 "좋아 보이게 만드는 실수" 들이다: 정의되지 않은 값을 0 으로
적기, 체계 밖 예측을 정답 쪽으로 접기, 관대 채점과 per-class 표가 어긋나기.
"""

import pytest

from core.eval.metrics import (
    Item,
    cohen_kappa,
    score,
    stratified_bootstrap_ci,
    top3_agreement,
    wilson_interval,
)
from core.eval.taxonomy import LABEL_KEYS


def mk(  # pylint: disable=too-many-arguments,too-many-positional-arguments
    gold, pred, alt="", weight=1.0, stratum="S1", rating=5, n=0
):
    return Item(review_id=f"r{n}", gold=gold, pred=pred, alt=alt,
                weight=weight, stratum=stratum, rating=rating)


# ── Wilson 구간 ────────────────────────────────────────────

def test_wilson_never_leaves_zero_one():
    for successes, total in [(0, 5), (5, 5), (1, 3), (0, 1), (100, 100)]:
        lo, hi = wilson_interval(successes, total)
        assert 0.0 <= lo <= hi <= 1.0, (successes, total, lo, hi)


def test_wilson_is_wide_at_tiny_n():
    """support 3건짜리 카테고리의 재현율을 단일 수치로 인용하면 안 되는 이유."""
    lo, hi = wilson_interval(3, 3)
    assert hi - lo > 0.35, "3/3 인데 구간이 좁게 나오면 표본 크기를 숨기는 것이다"


def test_wilson_is_not_degenerate_at_perfect_score():
    lo, _ = wilson_interval(10, 10)
    assert lo < 1.0, "10/10 의 하한이 1.0 이면 불확실성이 사라진 것이다"


def test_wilson_narrows_as_n_grows():
    narrow = wilson_interval(80, 100)
    wide = wilson_interval(8, 10)
    assert (narrow[1] - narrow[0]) < (wide[1] - wide[0])


# ── 기본 채점 ──────────────────────────────────────────────

def test_perfect_predictions():
    items = [mk("taste", "taste"), mk("price", "price")]
    r = score(items, LABEL_KEYS)
    assert r.overall["accuracy"]["point"] == 1.0
    assert r.per_class["taste"]["precision"] == 1.0
    assert r.per_class["taste"]["recall"] == 1.0


def test_micro_equals_accuracy_and_says_so():
    """같은 수를 네 번 적어 놓고 네 가지 증거인 것처럼 보이면 안 된다."""
    items = [mk("taste", "taste"), mk("price", "taste"), mk("rider", "rider")]
    r = score(items, LABEL_KEYS)
    acc = r.overall["accuracy"]["point"]
    micro = r.overall["micro"]
    assert micro["precision"] == micro["recall"] == micro["f1"] == acc
    assert micro["equals_accuracy"] is True


def test_undefined_precision_is_none_not_zero():
    """예측이 한 번도 안 나온 카테고리의 정밀도는 0% 가 아니라 '정의되지 않음' 이다."""
    items = [mk("taste", "taste"), mk("price", "taste")]
    r = score(items, LABEL_KEYS)
    assert r.per_class["price"]["support"] == 1
    assert r.per_class["price"]["n_pred"] == 0
    assert r.per_class["price"]["precision"] is None
    assert r.per_class["price"]["recall"] == 0.0


def test_undefined_precision_is_reported_in_notes():
    items = [mk("taste", "taste"), mk("price", "taste")]
    r = score(items, LABEL_KEYS)
    assert any("정의되지 않" in n for n in r.notes)


def test_out_of_taxonomy_prediction_counts_as_wrong_and_is_surfaced():
    """모델이 지어낸 라벨을 조용히 other 로 접으면 프롬프트 준수 실패가 숨는다."""
    items = [mk("taste", "배터리불량"), mk("price", "price")]
    r = score(items, LABEL_KEYS)
    assert r.overall["accuracy"]["point"] == 0.5
    assert "배터리불량" in r.per_class
    assert any("닫힌 집합 밖" in n for n in r.notes)


def test_empty_prediction_counts_as_wrong():
    """배치 응답에서 빠진 리뷰. 조용히 other 로 채우면 정확도가 위장된다."""
    items = [mk("taste", ""), mk("price", "price")]
    r = score(items, LABEL_KEYS)
    assert r.overall["accuracy"]["point"] == 0.5


def test_macro_excludes_classes_with_no_support():
    """데이터에 없는 카테고리를 0 점으로 끼우면 카테고리를 늘리는 것만으로
    점수가 떨어진다."""
    items = [mk("taste", "taste"), mk("price", "price")]
    r = score(items, LABEL_KEYS)
    assert r.overall["macro"]["n_classes"] == 2
    assert r.overall["macro"]["f1"] == 1.0


def test_thin_support_is_flagged():
    items = [mk("taste", "taste") for _ in range(3)]
    r = score(items, LABEL_KEYS)
    assert any("support 5건 미만" in n for n in r.notes)


def test_confusion_matrix_records_direction():
    items = [mk("temperature", "delivery_delay")] * 3
    r = score(items, LABEL_KEYS)
    assert r.confusion["temperature"]["delivery_delay"] == 3
    assert "delivery_delay" not in r.confusion


# ── strict / lenient ───────────────────────────────────────

def test_lenient_accepts_alt_label():
    items = [mk("temperature", "delivery_delay", alt="delivery_delay")]
    assert score(items, LABEL_KEYS, lenient=False).overall["accuracy"]["point"] == 0.0
    assert score(items, LABEL_KEYS, lenient=True).overall["accuracy"]["point"] == 1.0


def test_lenient_never_scores_below_strict():
    items = [
        mk("temperature", "delivery_delay", alt="delivery_delay"),
        mk("taste", "hygiene", alt="portion"),
        mk("price", "price"),
    ]
    strict = score(items, LABEL_KEYS).overall["accuracy"]["point"]
    lenient = score(items, LABEL_KEYS, lenient=True).overall["accuracy"]["point"]
    assert lenient >= strict


def test_lenient_per_class_matches_lenient_accuracy():
    """대체라벨을 맞힌 건을 주라벨의 오답으로 세면 표와 총계가 어긋난다."""
    items = [
        mk("temperature", "delivery_delay", alt="delivery_delay"),
        mk("taste", "taste"),
    ]
    r = score(items, LABEL_KEYS, lenient=True)
    total_tp = sum(c["tp"] for c in r.per_class.values())
    assert total_tp == 2
    assert r.overall["accuracy"]["point"] == 1.0


def test_alt_label_ignored_when_it_equals_primary():
    items = [mk("taste", "price", alt="taste")]
    assert score(items, LABEL_KEYS, lenient=True).overall["accuracy"]["point"] == 0.0


def test_empty_alt_does_not_make_empty_pred_correct():
    items = [mk("taste", "", alt="")]
    assert score(items, LABEL_KEYS, lenient=True).overall["accuracy"]["point"] == 0.0


# ── 모집단 추정 ────────────────────────────────────────────

def test_population_estimate_uses_weights():
    """가중치가 큰 층에서 틀리면 모집단 정확도가 표본 정확도보다 낮아야 한다."""
    items = [
        mk("no_issue", "no_issue", weight=1.0, stratum="S1"),
        mk("taste", "price", weight=10.0, stratum="S4"),
    ]
    r = score(items, LABEL_KEYS)
    assert r.overall["accuracy"]["point"] == 0.5
    assert r.overall["population_estimate"]["accuracy"] == pytest.approx(1 / 11, abs=1e-3)


def test_bootstrap_interval_brackets_point_estimate():
    items = [mk("taste", "taste" if i % 4 else "price", weight=2.0, stratum="S4", n=i)
             for i in range(60)]
    ci = stratified_bootstrap_ci(items, rounds=300)
    assert ci["ci95_low"] <= ci["point"] <= ci["ci95_high"]


def test_bootstrap_is_deterministic():
    items = [mk("taste", "taste" if i % 3 else "price", n=i) for i in range(40)]
    a = stratified_bootstrap_ci(items, rounds=200)
    b = stratified_bootstrap_ci(items, rounds=200)
    assert a == b


# ── 재검사 일치도 ──────────────────────────────────────────

def test_kappa_is_one_on_perfect_agreement():
    first = ["taste", "price", "rider", "taste"]
    r = cohen_kappa(first, list(first))
    assert r["kappa"] == 1.0
    assert r["agreement"] == 1.0


def test_kappa_corrects_for_chance():
    """단순 일치율이 높아도 한 카테고리에 쏠려 있으면 κ 는 낮아야 한다."""
    first = ["no_issue"] * 9 + ["taste"]
    second = ["no_issue"] * 9 + ["price"]
    r = cohen_kappa(first, second)
    assert r["agreement"] == 0.9
    assert r["kappa"] < 0.9


def test_kappa_flags_low_reliability():
    first = ["taste", "price", "rider", "portion", "hygiene"]
    second = ["price", "taste", "portion", "rider", "taste"]
    r = cohen_kappa(first, second)
    assert r["kappa"] is not None and r["kappa"] < 0.40
    assert "신뢰하기 어렵" in r["interpretation"]


def test_kappa_undefined_when_everything_is_one_class():
    r = cohen_kappa(["no_issue"] * 5, ["no_issue"] * 5)
    assert r["kappa"] is None
    assert r["agreement"] == 1.0


def test_kappa_lists_disagreements():
    r = cohen_kappa(["taste", "price"], ["taste", "portion"])
    assert r["disagreements"] == [{"first": "price", "second": "portion"}]


def test_kappa_rejects_mismatched_lengths():
    with pytest.raises(ValueError):
        cohen_kappa(["taste"], ["taste", "price"])


# ── TOP 3 ──────────────────────────────────────────────────

def test_top3_excludes_no_issue():
    """불만 랭킹이다. '문제 없음' 이 1위로 올라오면 TOP 3 가 무의미해진다."""
    items = ([mk("no_issue", "no_issue")] * 50 + [mk("taste", "taste")] * 5
             + [mk("price", "price")] * 4 + [mk("rider", "rider")] * 3)
    t3 = top3_agreement(items)
    assert "no_issue" not in t3["gold_top3"]
    assert t3["gold_top3"] == ["taste", "price", "rider"]


def test_top3_detects_ranking_match_despite_item_errors():
    """리뷰 단위로 좀 틀려도 집계 랭킹은 맞을 수 있다. 그래서 둘 다 낸다."""
    items = ([mk("taste", "taste")] * 9 + [mk("taste", "price")]
             + [mk("price", "price")] * 5 + [mk("rider", "rider")] * 3
             + [mk("portion", "portion")])
    t3 = top3_agreement(items)
    assert t3["overlap_count"] == 3
    assert t3["gold_top3"] == ["taste", "price", "rider"]


def test_top3_uses_weights_when_asked():
    items = [mk("taste", "taste", weight=1.0)] * 3 + [mk("price", "price", weight=20.0)]
    assert top3_agreement(items, use_weights=True)["gold_top3"][0] == "price"
    assert top3_agreement(items, use_weights=False)["gold_top3"][0] == "taste"


def test_empty_input_does_not_crash():
    r = score([], LABEL_KEYS)
    assert r.n == 0
    assert r.overall["accuracy"]["point"] is None
