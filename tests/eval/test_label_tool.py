"""라벨링 도구 저장소 테스트 — 라벨을 잃지 않는 것과, 재검사가 눈가림인 것."""

import csv
import importlib.util
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
_spec = importlib.util.spec_from_file_location(
    "label_tool", ROOT / "scripts/eval/label_tool.py"
)
label_tool = importlib.util.module_from_spec(_spec)
sys.modules["label_tool"] = label_tool
_spec.loader.exec_module(label_tool)

COLUMNS = [
    "sample_id", "review_id", "review_text", "rating", "ordered_at", "menu",
    "stratum", "inclusion_prob", "weight",
    "primary_label", "alt_label", "notes", "labeled_at",
]


def _sample(tmp_path, n=100, labeled=False):
    path = tmp_path / "sample.csv"
    with open(path, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=COLUMNS)
        w.writeheader()
        for i in range(1, n + 1):
            w.writerow({
                "sample_id": i, "review_id": f"id{i:04d}",
                "review_text": f"리뷰 본문 {i}", "rating": 5 if i % 3 else 2,
                "ordered_at": f"2026-09-{i % 28 + 1:02d}", "menu": "도야짬뽕",
                "stratum": "S4" if i % 3 else "S1",
                "inclusion_prob": 0.5, "weight": 2.0,
                "primary_label": "taste" if labeled else "",
                "alt_label": "", "notes": "", "labeled_at": "",
            })
    return str(path)


def test_label_is_written_through_to_disk(tmp_path):
    path = _sample(tmp_path)
    store = label_tool.Store(path, retest=False)
    store.set_label(0, "temperature", "delivery_delay", "R4 적용")

    with open(path, encoding="utf-8-sig", newline="") as f:
        rows = list(csv.DictReader(f))
    assert rows[0]["primary_label"] == "temperature"
    assert rows[0]["alt_label"] == "delivery_delay"
    assert rows[0]["notes"] == "R4 적용"
    assert rows[0]["labeled_at"], "라벨링 시각이 안 찍혔다"


def test_write_preserves_every_row_and_column(tmp_path):
    """한 건 저장할 때마다 전체를 다시 쓴다. 다른 행이 상하면 안 된다."""
    path = _sample(tmp_path, n=250)
    store = label_tool.Store(path, retest=False)
    store.set_label(7, "hygiene", "", "")

    with open(path, encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        assert list(reader.fieldnames) == COLUMNS
        rows = list(reader)
    assert len(rows) == 250
    assert rows[7]["primary_label"] == "hygiene"
    assert rows[7]["review_text"] == "리뷰 본문 8"
    assert all(r["primary_label"] == "" for i, r in enumerate(rows) if i != 7)


def test_clearing_a_label_clears_the_timestamp(tmp_path):
    path = _sample(tmp_path)
    store = label_tool.Store(path, retest=False)
    store.set_label(0, "taste", "", "")
    store.set_label(0, "", "", "")
    with open(path, encoding="utf-8-sig", newline="") as f:
        rows = list(csv.DictReader(f))
    assert rows[0]["primary_label"] == ""
    assert rows[0]["labeled_at"] == ""


def test_progress_counts_only_labeled(tmp_path):
    store = label_tool.Store(_sample(tmp_path, n=10), retest=False)
    assert store.progress() == {"done": 0, "total": 10}
    store.set_label(0, "taste", "", "")
    store.set_label(1, "price", "", "")
    assert store.progress() == {"done": 2, "total": 10}


def test_view_never_exposes_stratum(tmp_path):
    """층을 보여주면 '지금은 불만어휘 검출 구간' 을 알아채고 라벨이 쏠린다."""
    store = label_tool.Store(_sample(tmp_path), retest=False)
    for row in store.view():
        assert "stratum" not in row
        assert "inclusion_prob" not in row
        assert "weight" not in row


def _retest_copy(tmp_path, **kw):
    source = _sample(tmp_path, **kw)
    target = str(tmp_path / "sample.retest.csv")
    label_tool.make_retest_copy(source, target)
    return source, target


def test_retest_copy_hides_previous_labels_of_target_rows(tmp_path):
    """이전 라벨이 보이면 재검사가 아니라 베껴쓰기가 된다."""
    _, target = _retest_copy(tmp_path, labeled=True)
    store = label_tool.Store(target, retest=True)
    view = store.view()
    assert view, "재검사 대상이 하나도 안 뽑혔다"
    assert all(r["primary"] == "" for r in view)
    assert all(r["alt"] == "" for r in view)
    assert all(r["notes"] == "" for r in view)


def test_retest_copy_keeps_baseline_labels_of_other_rows(tmp_path):
    """대상이 아닌 행의 최초 라벨은 사본에도 남는다. 비교 파일 형식이 그대로다."""
    _, target = _retest_copy(tmp_path, n=200, labeled=True)
    store = label_tool.Store(target, retest=True)
    targets = set(store.indices)
    for i, row in enumerate(store.rows):
        assert (row["primary_label"] == "") == (i in targets)


def test_retest_progress_starts_at_zero(tmp_path):
    """최초 라벨을 재검사 완료로 세면 진행률이 처음부터 다 찬 것으로 나온다."""
    _, target = _retest_copy(tmp_path, labeled=True)
    store = label_tool.Store(target, retest=True)
    assert store.progress()["done"] == 0
    assert store.progress()["total"] == len(store.indices) > 0


def test_retest_labels_survive_a_restart(tmp_path):
    """저장한 재검사 라벨은 다시 열어도 보여야 이어서 한다. 가리면 같은 건을 또 단다."""
    _, target = _retest_copy(tmp_path, labeled=True)
    store = label_tool.Store(target, retest=True)
    idx = store.indices[0]
    store.set_label(idx, "portion", "price", "R6")

    reopened = label_tool.Store(target, retest=True)
    assert reopened.progress()["done"] == 1
    shown = next(r for r in reopened.view() if r["idx"] == idx)
    assert (shown["primary"], shown["alt"], shown["notes"]) == ("portion", "price", "R6")


def test_retest_copy_does_not_touch_the_source(tmp_path):
    source, _ = _retest_copy(tmp_path, labeled=True)
    with open(source, encoding="utf-8-sig", newline="") as f:
        rows = list(csv.DictReader(f))
    assert all(r["primary_label"] == "taste" for r in rows)


def test_retest_selects_about_ten_percent(tmp_path):
    store = label_tool.Store(_sample(tmp_path, n=1000), retest=True)
    assert 70 <= len(store.indices) <= 130, len(store.indices)


def test_retest_selection_is_reproducible(tmp_path):
    """시드가 아니라 review_id 해시로 고르므로 언제 돌려도 같은 건이 나온다."""
    path = _sample(tmp_path, n=300)
    a = label_tool.Store(path, retest=True).indices
    b = label_tool.Store(path, retest=True).indices
    assert a == b


def test_retest_mode_still_writes_full_file(tmp_path):
    _, path = _retest_copy(tmp_path, n=50, labeled=True)
    store = label_tool.Store(path, retest=True)
    target = store.indices[0]
    store.set_label(target, "portion", "", "")
    with open(path, encoding="utf-8-sig", newline="") as f:
        rows = list(csv.DictReader(f))
    assert len(rows) == 50
    assert rows[target]["primary_label"] == "portion"


def test_page_waits_for_the_save_to_land():
    """디스크 쓰기가 실패했는데 다음 건으로 넘어가면 라벨러는 그 건을 잃는다.

    JS 는 테스트가 못 돌리므로 계약이 페이지에 남아 있는지만 본다.
    """
    assert "res.ok" in label_tool.PAGE
    assert "await save(r)" in label_tool.PAGE


def test_missing_column_fails_loudly(tmp_path):
    path = tmp_path / "bad.csv"
    path.write_text("sample_id,review_text\n1,안녕\n", encoding="utf-8")
    with pytest.raises(SystemExit, match="primary_label"):
        label_tool.Store(str(path), retest=False)
