"""라벨 체계가 문서와 어긋나지 않게 잡는 테스트.

체계가 코드와 문서 양쪽에 있으면 반드시 어긋난다. 어긋난 채로 라벨링하면
라벨러는 문서를 보고 모델은 코드를 보게 되어, 그 격차가 정확도로 둔갑한다.
"""

import re
from pathlib import Path

import pytest

from core.eval.taxonomy import (
    COMPLAINT_KEYS,
    EXCLUDE,
    HOTKEYS,
    LABEL_KEYS,
    LABELS,
    LEGACY_ECOMMERCE_MAP,
    TAXONOMY_VERSION,
    build_category_block,
    has_complaint_signal,
    is_valid_label,
)

GUIDE = Path(__file__).resolve().parents[2] / "docs/evaluation/labeling-guide-v1.md"


def test_label_set_is_closed_and_complete():
    assert len(LABELS) == 13
    assert "no_issue" in LABEL_KEYS
    assert len(COMPLAINT_KEYS) == 12
    assert "no_issue" not in COMPLAINT_KEYS
    assert EXCLUDE not in LABEL_KEYS, "EXCLUDE 는 라벨이 아니라 제외 사유다"


def test_every_label_has_boundaries():
    for key, spec in LABELS.items():
        assert spec["ko"], key
        assert spec["includes"].strip(), f"{key}: 포함 기준이 비었다"
        assert spec["excludes"].strip(), f"{key}: 제외 기준이 비었다"


def test_hotkeys_unique_and_single_char():
    assert len(HOTKEYS) == len(LABELS)
    for hotkey in HOTKEYS:
        assert len(hotkey) == 1, hotkey
    # 라벨링 도구가 'e' 를 EXCLUDE 에 쓴다. 카테고리가 가로채면 안 된다.
    assert "e" not in HOTKEYS
    # 도구의 다른 조작 키와도 겹치면 안 된다.
    for reserved in ("m", "r", "g", "d"):
        assert reserved not in HOTKEYS, f"'{reserved}' 는 도구 조작 키다"


def test_guide_document_lists_every_label():
    """문서에 빠진 카테고리가 있으면 라벨러가 그 카테고리를 영영 못 쓴다."""
    text = GUIDE.read_text(encoding="utf-8")
    for key, spec in LABELS.items():
        assert f"`{key}`" in text, f"가이드에 {key} 가 없다"
        assert spec["ko"] in text, f"가이드에 '{spec['ko']}' 가 없다"
    assert f"`{EXCLUDE}`" in text
    assert TAXONOMY_VERSION in text


def test_guide_hotkeys_match_code():
    """가이드 표의 단축키와 코드의 단축키가 같아야 한다."""
    text = GUIDE.read_text(encoding="utf-8")
    for key, spec in LABELS.items():
        row = next(
            (line for line in text.splitlines() if line.startswith(f"| `{key}` |")),
            None,
        )
        assert row is not None, f"가이드에 {key} 행이 없다"
        assert f"`{spec['hotkey']}`" in row, (
            f"{key}: 가이드 단축키와 코드 단축키가 다르다 (코드={spec['hotkey']})"
        )


def test_guide_documents_all_ten_rules():
    text = GUIDE.read_text(encoding="utf-8")
    for n in range(1, 11):
        assert re.search(rf"### R{n} — ", text), f"판정 규칙 R{n} 이 문서에 없다"


def test_legacy_map_covers_every_label():
    assert set(LEGACY_ECOMMERCE_MAP) == set(LABEL_KEYS)


def test_legacy_map_is_lossy_as_documented():
    """맛·온도·위생이 poor_quality 하나로 뭉개지는 것이 v1 을 새로 만든 이유다."""
    collapsed = {LEGACY_ECOMMERCE_MAP[k] for k in ("taste", "temperature", "hygiene")}
    assert collapsed == {"poor_quality"}


def test_category_block_feeds_same_boundaries_to_model():
    block = build_category_block()
    for key, spec in LABELS.items():
        assert key in block
        assert spec["includes"][:20] in block, f"{key}: 모델에 포함 기준이 안 간다"


def test_is_valid_label():
    assert is_valid_label("taste")
    assert not is_valid_label(EXCLUDE)
    assert not is_valid_label("battery_issue")  # 예전 체계의 라벨
    assert not is_valid_label("")


@pytest.mark.parametrize("text", [
    "늦게 와서 다 식었어요",
    "머리카락 나왔어요",
    "양이 너무 적어요",
    "국물이 다 샜어요",
    "단무지가 안 왔어요",
    "너무 비싸요",
    "불친절하네요",
])
def test_lexicon_catches_obvious_complaints(text):
    assert has_complaint_signal(text)


@pytest.mark.parametrize("text", [
    "맛있어요",
    "잘 먹었습니다",
    "또 시킬게요",
    "",
])
def test_lexicon_ignores_plain_praise(text):
    assert not has_complaint_signal(text)


def test_lexicon_is_only_a_stratifier_not_a_labeler():
    """사전은 층을 가르는 데만 쓴다. 놓치는 불만이 있는 것이 정상이고,
    그래서 S4(사전 미검출) 층을 표본에 반드시 넣는다."""
    missed = "면이 좀 그렇네요"  # 완곡한 불만 — 사전에 안 걸린다
    assert not has_complaint_signal(missed)
