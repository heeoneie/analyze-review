"""reply_guide 테스트 (정적 가이드 + LLM 폴백 mock)"""

from unittest.mock import MagicMock, patch

from core.reply_guide import (
    _LLM_CACHE,
    GUIDE_DB,
    get_guide,
    list_guides,
)

# ── 정적 가이드 테스트 ──────────────────────────────────────


class TestGuideDB:
    def test_has_common_categories(self):
        assert "배송 지연" in GUIDE_DB
        assert "품질 불량" in GUIDE_DB
        assert "고객 서비스" in GUIDE_DB

    def test_guide_has_required_fields(self):
        for category, guide in GUIDE_DB.items():
            assert "tone" in guide, f"{category}: tone 없음"
            assert "structure" in guide, f"{category}: structure 없음"
            assert "must_address" in guide, f"{category}: must_address 없음"
            assert "good_example" in guide, f"{category}: good_example 없음"
            assert "bad_example" in guide, f"{category}: bad_example 없음"

    def test_structure_is_list(self):
        for category, guide in GUIDE_DB.items():
            assert isinstance(guide["structure"], list), f"{category}: structure가 리스트가 아님"
            assert len(guide["structure"]) >= 2, f"{category}: structure가 너무 짧음"

    def test_bad_example_is_macro_style(self):
        """나쁜 예시에는 매크로성 표현이 포함되어야 함"""
        macro_phrases = ["불편을 드려", "소중한 의견", "최선을 다하겠습니다", "더 나은 서비스", "어쩔 수 없는", "신경 쓰도록"]
        for category, guide in GUIDE_DB.items():
            has_macro = any(phrase in guide["bad_example"] for phrase in macro_phrases)
            assert has_macro, f"{category}: bad_example에 매크로 표현이 없음"


# ── get_guide 테스트 ────────────────────────────────────────


class TestGetGuide:
    def test_static_guide_returns_immediately(self):
        result = get_guide("배송 지연")
        assert result["category"] == "배송 지연"
        assert result["source"] == "static"
        assert "tone" in result
        assert "structure" in result

    def test_static_guide_has_all_fields(self):
        result = get_guide("품질 불량")
        assert result["tone"]
        assert len(result["structure"]) >= 2
        assert len(result["must_address"]) >= 2
        assert result["good_example"]
        assert result["bad_example"]

    @patch("core.reply_guide.get_client")
    @patch("core.reply_guide.call_openai_json")
    def test_unknown_category_calls_llm(self, mock_call, mock_client):
        _LLM_CACHE.clear()
        mock_client.return_value = MagicMock()
        mock_call.return_value = (
            '{"tone": "공감", "structure": ["1", "2"], '
            '"must_address": ["p1"], "good_example": "좋음", "bad_example": "나쁨"}'
        )

        result = get_guide("알 수 없는 카테고리")
        assert result["source"] == "generated"
        assert result["tone"] == "공감"
        mock_call.assert_called_once()

    @patch("core.reply_guide.get_client")
    @patch("core.reply_guide.call_openai_json")
    def test_llm_cache_hit(self, mock_call, _mock_client):
        _LLM_CACHE.clear()
        _LLM_CACHE["캐시됨"] = {
            "tone": "캐시", "structure": [], "must_address": [],
            "good_example": "", "bad_example": "",
        }

        result = get_guide("캐시됨")
        assert result["tone"] == "캐시"
        mock_call.assert_not_called()

    @patch("core.reply_guide.get_client")
    @patch("core.reply_guide.call_openai_json")
    def test_llm_failure_returns_fallback(self, mock_call, mock_client):
        _LLM_CACHE.clear()
        mock_client.return_value = MagicMock()
        mock_call.side_effect = RuntimeError("API 에러")

        result = get_guide("에러 카테고리")
        assert result["source"] == "generated"
        assert result["tone"] == "공감 + 사과 + 해결"


# ── list_guides 테스트 ──────────────────────────────────────


class TestListGuides:
    def test_returns_all_static_guides(self):
        guides = list_guides()
        categories = {g["category"] for g in guides}
        assert "배송 지연" in categories
        assert "품질 불량" in categories
        assert len(guides) == len(GUIDE_DB)

    def test_guide_items_have_required_fields(self):
        guides = list_guides()
        for guide in guides:
            assert "category" in guide
            assert "tone" in guide
            assert "structure" in guide
