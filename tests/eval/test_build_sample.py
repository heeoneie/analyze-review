"""표본 추출기 테스트 — 설계의 방어 가능성이 걸린 성질들만 검증한다."""

import importlib.util
import sys
from pathlib import Path

import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[2]
_spec = importlib.util.spec_from_file_location(
    "build_sample", ROOT / "scripts/eval/build_sample.py"
)
build_sample = importlib.util.module_from_spec(_spec)
sys.modules["build_sample"] = build_sample
_spec.loader.exec_module(build_sample)


def _write_csv(tmp_path, rows):
    path = tmp_path / "reviews.csv"
    pd.DataFrame(rows).to_csv(path, index=False, encoding="utf-8-sig")
    return str(path)


def _corpus(  # pylint: disable=too-many-arguments
    tmp_path, *, n_five_clean=300, n_five_complaint=30, n_four=10,
    n_low=12, n_empty=100,
):
    rows = []
    for i in range(n_five_clean):
        rows.append({"별점": 5, "리뷰내용": f"맛있어요 {i}", "작성일시": f"t{i}",
                     "주문메뉴": "도야짬뽕", "주문유형": "배달"})
    for i in range(n_five_complaint):
        rows.append({"별점": 5, "리뷰내용": f"맛있는데 양이 적어요 {i}",
                     "작성일시": f"c{i}", "주문메뉴": "도야짬뽕", "주문유형": "배달"})
    for i in range(n_four):
        rows.append({"별점": 4, "리뷰내용": f"괜찮아요 {i}", "작성일시": f"f{i}",
                     "주문메뉴": "탕수육", "주문유형": "배달"})
    for i in range(n_low):
        rows.append({"별점": 2, "리뷰내용": f"머리카락 나왔어요 {i}",
                     "작성일시": f"n{i}", "주문메뉴": "짜장면", "주문유형": "배달"})
    for i in range(n_empty):
        rows.append({"별점": 5, "리뷰내용": "", "작성일시": f"e{i}",
                     "주문메뉴": "군만두", "주문유형": "배달"})
    return _write_csv(tmp_path, rows)


def test_stratify_assigns_expected_strata(tmp_path):
    pop, _, _ = build_sample.load_and_stratify(_corpus(tmp_path))
    counts = pop["stratum"].value_counts().to_dict()
    assert counts["S1"] == 12     # 별점 ≤3, 본문 있음
    assert counts["S2"] == 10     # 별점 4
    assert counts["S3"] == 30     # 5점 + 불만어휘 검출
    assert counts["S4"] == 300    # 5점 + 미검출
    assert counts["EMPTY"] == 100


def test_empty_body_reviews_are_never_sampled(tmp_path):
    """본문 없는 리뷰는 분류 대상이 아니다. 분모에 넣으면 커버리지를 부풀리는 것이다."""
    pop, _, _ = build_sample.load_and_stratify(_corpus(tmp_path))
    take = build_sample.allocate(pop, target=250, min_s4=60)
    sample = build_sample.draw(pop, take, seed=1)
    assert "EMPTY" not in set(sample["stratum"])
    assert (sample["review_text"].str.strip() != "").all()


def test_s1_and_s2_are_censused(tmp_path):
    """불만이 실릴 가능성이 가장 높은 층은 전수 조사한다."""
    pop, _, _ = build_sample.load_and_stratify(_corpus(tmp_path))
    take = build_sample.allocate(pop, target=250, min_s4=60)
    assert take["S1"] == 12
    assert take["S2"] == 10


def test_s4_is_always_included(tmp_path):
    """어휘 사전이 놓친 불만을 재려면 S4 가 반드시 있어야 한다.
    목표 표본이 아무리 작아도 S4 를 0 으로 만들지 않는다."""
    pop, _, _ = build_sample.load_and_stratify(_corpus(tmp_path))
    take = build_sample.allocate(pop, target=60, min_s4=60)
    assert take["S4"] >= 1, "S4 가 비면 재현율 추정이 구조적으로 불가능해진다"


def test_inclusion_probability_matches_actual_draw(tmp_path):
    """가중치가 틀리면 모집단 추정치가 통째로 틀린다."""
    pop, _, _ = build_sample.load_and_stratify(_corpus(tmp_path))
    take = build_sample.allocate(pop, target=250, min_s4=60)
    sample = build_sample.draw(pop, take, seed=1)
    for stratum, block in sample.groupby("stratum"):
        pop_size = (pop["stratum"] == stratum).sum()
        assert block["inclusion_prob"].iloc[0] == pytest.approx(
            len(block) / pop_size, abs=1e-5
        )
        assert block["weight"].iloc[0] == pytest.approx(
            1 / block["inclusion_prob"].iloc[0], abs=1e-3
        )


def test_census_strata_have_weight_one(tmp_path):
    pop, _, _ = build_sample.load_and_stratify(_corpus(tmp_path))
    take = build_sample.allocate(pop, target=250, min_s4=60)
    sample = build_sample.draw(pop, take, seed=1)
    for stratum in ("S1", "S2"):
        assert (sample[sample["stratum"] == stratum]["weight"] == 1.0).all()


def test_sample_is_shuffled_so_labeler_cannot_infer_stratum(tmp_path):
    """층 순서대로 두면 라벨러가 '지금은 5점 구간' 을 알아채고 기준이 끌려간다."""
    pop, _, _ = build_sample.load_and_stratify(_corpus(tmp_path))
    take = build_sample.allocate(pop, target=250, min_s4=60)
    sample = build_sample.draw(pop, take, seed=1)
    strata = sample["stratum"].tolist()
    runs = sum(1 for a, b in zip(strata, strata[1:]) if a != b)
    assert runs > 10, "층이 뭉쳐 있다 — 섞이지 않았다"


def test_draw_is_deterministic(tmp_path):
    csv = _corpus(tmp_path)
    pop1, _, _ = build_sample.load_and_stratify(csv)
    pop2, _, _ = build_sample.load_and_stratify(csv)
    take = build_sample.allocate(pop1, target=250, min_s4=60)
    a = build_sample.draw(pop1, take, seed=42)
    b = build_sample.draw(pop2, take, seed=42)
    assert a["review_id"].tolist() == b["review_id"].tolist()


def test_label_columns_start_empty(tmp_path):
    """표본 파일에 라벨이 미리 들어 있으면 안 된다. 라벨은 사람이 단다."""
    pop, _, _ = build_sample.load_and_stratify(_corpus(tmp_path))
    take = build_sample.allocate(pop, target=250, min_s4=60)
    sample = build_sample.draw(pop, take, seed=1)
    for col in ("primary_label", "alt_label", "notes", "labeled_at"):
        assert (sample[col] == "").all(), f"{col} 이 비어 있지 않다"


def test_review_id_is_stable_across_runs(tmp_path):
    pop, _, _ = build_sample.load_and_stratify(_corpus(tmp_path))
    again, _, _ = build_sample.load_and_stratify(_corpus(tmp_path))
    assert pop["review_id"].tolist() == again["review_id"].tolist()


def test_missing_required_column_fails_loudly(tmp_path):
    path = _write_csv(tmp_path, [{"본문": "맛있어요", "점수": 5}])
    with pytest.raises(SystemExit, match="필수 컬럼"):
        build_sample.load_and_stratify(path)


def test_dedup_can_be_disabled(tmp_path):
    rows = [{"별점": 5, "리뷰내용": "맛있어요", "작성일시": "2026-09-01",
             "주문메뉴": "짬뽕", "주문유형": "배달"}] * 5
    path = _write_csv(tmp_path, rows)
    with_dedup, _, removed = build_sample.load_and_stratify(path, dedup=True)
    without, _, kept = build_sample.load_and_stratify(path, dedup=False)
    assert len(with_dedup) == 1 and removed == 4
    assert len(without) == 5 and kept == 0
