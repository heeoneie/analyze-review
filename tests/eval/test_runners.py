"""실행기 테스트 — API 를 부르지 않고 검증할 수 있는 부분만.

여기서 잡는 것은 "숫자를 좋아 보이게 만드는 구조적 실수" 다:
RAG 가 자기 자신을 예시로 보는 것(정확도 100% 수렴), 배치 응답 누락을 조용히
정답 후보로 채우는 것, 열린 어휘를 임의로 접는 것.
"""

import pytest

from core.eval.runners import (
    OPEN_LABEL_RULES,
    UNMAPPED,
    _Retriever,
    _closed_prompt_batch,
    _closed_prompt_single,
    _parse_batch,
    normalize_open_label,
)
from core.eval.taxonomy import LABEL_KEYS


# ── 배치 응답 파싱 ──────────────────────────────────────────

def test_parse_batch_orders_by_review_number():
    content = ('{"categories":[{"review_number":3,"category":"price"},'
               '{"review_number":1,"category":"taste"},'
               '{"review_number":2,"category":"rider"}]}')
    assert _parse_batch(content, 3) == ["taste", "rider", "price"]


def test_missing_entries_stay_empty_not_other():
    """빠진 리뷰를 'other' 로 채우면 프롬프트 준수 실패가 정확도로 위장된다.
    (기존 core/experiments/evaluate.py 의 결함이다.)"""
    content = '{"categories":[{"review_number":1,"category":"taste"}]}'
    assert _parse_batch(content, 3) == ["taste", "", ""]


def test_out_of_range_review_numbers_are_dropped():
    content = ('{"categories":[{"review_number":99,"category":"taste"},'
               '{"review_number":0,"category":"price"},'
               '{"review_number":1,"category":"rider"}]}')
    assert _parse_batch(content, 2) == ["rider", ""]


def test_unparseable_response_yields_all_empty():
    assert _parse_batch("완전히 깨진 응답", 3) == ["", "", ""]


def test_malformed_entries_are_skipped():
    content = ('{"categories":["문자열", {"review_number":"1","category":"taste"},'
               '{"review_number":2,"category":"price"}]}')
    assert _parse_batch(content, 2) == ["", "price"]


# ── 프롬프트 ───────────────────────────────────────────────

@pytest.mark.parametrize("builder", [
    lambda: _closed_prompt_batch(["맛없어요", "잘 먹었습니다"]),
    lambda: _closed_prompt_single("맛없어요"),
])
def test_prompt_lists_every_allowed_label(builder):
    """모델이 라벨 목록 일부만 받으면 못 받은 카테고리는 영영 예측되지 않는다."""
    prompt = builder()
    for key in LABEL_KEYS:
        assert key in prompt, key


def test_prompt_gives_model_the_same_boundaries_as_the_labeler():
    """사람은 상세 기준을 보고 모델은 라벨 이름만 보면, 그 격차는 모델의
    실력이 아니라 정보량 차이다."""
    prompt = _closed_prompt_single("테스트")
    assert "식어서" in prompt or "미지근" in prompt   # temperature 포함 기준
    assert "머리카락" in prompt                        # hygiene 포함 기준
    assert "temperature" in prompt and "delivery_delay" in prompt  # R4


# ── 열린 어휘 정규화 ────────────────────────────────────────

@pytest.mark.parametrize("raw,expected", [
    ("배송 지연", "delivery_delay"),
    ("음식 온도", "temperature"),
    ("위생 불량", "hygiene"),
    ("포장 파손", "packaging"),
    ("메뉴 누락", "missing_item"),
    ("오배송", "wrong_item"),
    ("양 부족", "portion"),
    ("가격 불만", "price"),
    ("라이더 불친절", "rider"),
    ("맛 불량", "taste"),
])
def test_open_labels_map_to_closed_set(raw, expected):
    assert normalize_open_label(raw) == expected


def test_exact_closed_label_passes_through():
    for key in LABEL_KEYS:
        assert normalize_open_label(key) == key


def test_unmappable_label_is_surfaced_not_folded_into_other():
    """조용히 other 로 접으면 '프롬프트가 만들어낸 미지의 라벨' 비율이 숨는다."""
    assert normalize_open_label("배터리 성능") == UNMAPPED
    assert normalize_open_label("") == UNMAPPED
    assert normalize_open_label("zzzz") == UNMAPPED


def test_normalization_is_deterministic():
    """같은 문자열은 언제 넣어도 같은 결과. 점수를 보고 바꿀 여지가 없어야 한다."""
    for raw in ["배송 지연", "양 부족", "알 수 없음"]:
        assert normalize_open_label(raw) == normalize_open_label(raw)


def test_every_rule_target_is_a_real_label():
    for target, _ in OPEN_LABEL_RULES:
        assert target in LABEL_KEYS, target


def test_rule_order_resolves_temperature_before_delivery():
    """'식었다' 는 온도다. 규칙 순서가 바뀌면 R4 와 어긋난다."""
    assert normalize_open_label("식음") == "temperature"


# ── RAG 검색기 ─────────────────────────────────────────────

@pytest.fixture(name="retriever")
def _retriever():
    texts = [
        "국물이 다 식어서 왔어요",
        "양이 너무 적어요",
        "머리카락이 나왔습니다",
        "배달이 한 시간 넘게 걸렸어요",
        "맛있게 잘 먹었습니다",
        "단무지가 안 왔어요",
    ]
    # 임베딩 모델 다운로드를 피하려고 일부러 없는 이름을 줘서
    # 문자 n-gram 폴백으로 돌린다.
    return _Retriever(texts, "__no_such_model__")


def test_retriever_falls_back_without_embedding_model(retriever):
    assert retriever.backend == "char_ngram_tfidf"
    assert retriever.model_name is None


def test_retriever_never_returns_itself(retriever):
    """자기 자신을 예시로 돌려주면 정답이 프롬프트에 그대로 들어가
    정확도가 100% 에 수렴한다. 그건 측정이 아니다."""
    for i in range(len(retriever.texts)):
        assert i not in retriever.neighbours(i, k=3)


def test_retriever_returns_requested_count(retriever):
    assert len(retriever.neighbours(0, k=3)) == 3
    assert len(retriever.neighbours(0, k=5)) == 5


def test_retriever_caps_k_below_pool_size(retriever):
    """k 가 풀 크기 이상이어도 자기 자신이 끝에 딸려 나오면 안 된다."""
    n = len(retriever.texts)
    for k in (n, n + 3):
        got = retriever.neighbours(0, k=k)
        assert len(got) == n - 1
        assert 0 not in got


def test_retriever_finds_lexically_similar_first(retriever):
    """'국물이 다 식어서 왔어요' 와 가장 가까운 것이 '맛있게 잘 먹었습니다' 면
    검색이 무의미하다."""
    top = retriever.neighbours(0, k=2)
    assert 4 not in top[:1]


# ── 정규화 규칙의 충돌 지점 (실제로 버그가 났던 곳) ──────────────

@pytest.mark.parametrize("raw,expected", [
    # "오배송" 은 delivery_delay 의 "배송" 을 부분 포함한다.
    ("오배송", "wrong_item"),
    ("주문 오배송", "wrong_item"),
    # "불만 없음" 은 missing_item 쪽으로 새기 쉬웠다.
    ("불만 없음", "no_issue"),
    ("문제 없음", "no_issue"),
    ("이상 없음", "no_issue"),
    # 라이더는 delivery_delay 의 "배달" 계열과 겹친다.
    ("배달원 불친절", "rider"),
    ("라이더 태도", "rider"),
    # 시간 계열은 지연이고, 상태 계열은 온도다 (R4).
    ("배달 시간 지연", "delivery_delay"),
    ("음식이 식음", "temperature"),
    # "양호" 는 portion 의 "양" 을 부분 포함한다.
    ("양호", "no_issue"),
    ("전반 양호", "no_issue"),
])
def test_normalization_collision_points(raw, expected):
    assert normalize_open_label(raw) == expected


def test_underscore_label_is_not_mangled():
    """구분자를 먼저 지우면 missing_item 이 missingitem 이 되어 못 알아본다."""
    assert normalize_open_label("missing_item") == "missing_item"
    assert normalize_open_label("delivery_delay") == "delivery_delay"
    assert normalize_open_label("  taste  ") == "taste"
