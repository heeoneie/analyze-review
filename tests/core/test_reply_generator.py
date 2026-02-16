"""reply_generator 테스트 (LLM 호출 mock)"""

import json
from unittest.mock import MagicMock, patch

from core.reply_generator import (
    SYSTEM_PROMPT,
    ReplyGenerator,
    _build_batch_prompt,
    _build_single_prompt,
)

# ── 프롬프트 빌드 테스트 ─────────────────────────────────────


class TestBuildSinglePrompt:
    def test_includes_review_text(self):
        prompt = _build_single_prompt("배송이 늦었어요", 2)
        assert "배송이 늦었어요" in prompt

    def test_includes_rating(self):
        prompt = _build_single_prompt("별로", 1)
        assert "평점: 1점" in prompt

    def test_includes_category_when_given(self):
        prompt = _build_single_prompt("늦음", 2, category="배송 지연")
        assert "배송 지연" in prompt

    def test_no_category_when_none(self):
        prompt = _build_single_prompt("별로", 3, category=None)
        assert "카테고리" not in prompt

    def test_contains_anti_macro_rules(self):
        prompt = _build_single_prompt("테스트", 1)
        assert "불편을 드려 죄송합니다" in prompt
        assert "금지" in prompt

    def test_contains_json_format(self):
        prompt = _build_single_prompt("테스트", 1)
        assert '"reply"' in prompt


class TestBuildBatchPrompt:
    def test_includes_all_reviews(self):
        reviews = [
            {"review_text": "배송 늦음", "rating": 2},
            {"review_text": "품질 불량", "rating": 1},
        ]
        prompt = _build_batch_prompt(reviews)
        assert "배송 늦음" in prompt
        assert "품질 불량" in prompt
        assert "2개" in prompt

    def test_includes_category_if_present(self):
        reviews = [
            {"review_text": "늦음", "rating": 2, "category": "배송 지연"},
        ]
        prompt = _build_batch_prompt(reviews)
        assert "배송 지연" in prompt


# ── ReplyGenerator 테스트 (LLM mock) ────────────────────────


MOCK_SINGLE_RESPONSE = json.dumps({
    "reply": "고객님, 배송 지연으로 불편을 겪으셨군요.",
    "tone": "공감+사과+안내",
    "key_points_addressed": ["배송 지연"],
    "suggested_action": "1:1 문의 유도",
})

MOCK_BATCH_RESPONSE = json.dumps({
    "replies": [
        {
            "review_index": 1,
            "reply": "배송 지연 답변",
            "tone": "공감",
            "key_points_addressed": ["지연"],
            "suggested_action": "교환",
        },
        {
            "review_index": 2,
            "reply": "품질 불량 답변",
            "tone": "사과",
            "key_points_addressed": ["불량"],
            "suggested_action": "환불",
        },
    ]
})


@patch("core.reply_generator.get_client")
@patch("core.reply_generator.call_openai_json")
class TestGenerateSingle:
    def test_returns_parsed_reply(self, mock_call, mock_client):
        mock_call.return_value = MOCK_SINGLE_RESPONSE
        mock_client.return_value = MagicMock()

        gen = ReplyGenerator()
        result = gen.generate_single("배송이 늦었어요", 2)

        assert result["reply"] == "고객님, 배송 지연으로 불편을 겪으셨군요."
        assert result["tone"] == "공감+사과+안내"
        assert "배송 지연" in result["key_points_addressed"]

    def test_passes_system_prompt(self, mock_call, mock_client):
        mock_call.return_value = MOCK_SINGLE_RESPONSE
        mock_client.return_value = MagicMock()

        gen = ReplyGenerator()
        gen.generate_single("테스트", 1)

        _, kwargs = mock_call.call_args
        assert kwargs["system_prompt"] == SYSTEM_PROMPT

    def test_handles_parse_failure(self, mock_call, mock_client):
        mock_call.return_value = "not json at all"
        mock_client.return_value = MagicMock()

        gen = ReplyGenerator()
        result = gen.generate_single("테스트", 1)

        # fallback: raw 텍스트가 reply에 들어감
        assert result["reply"] == "not json at all"


@patch("core.reply_generator.get_client")
@patch("core.reply_generator.call_openai_json")
class TestGenerateBatch:
    def test_returns_all_replies(self, mock_call, mock_client):
        mock_call.return_value = MOCK_BATCH_RESPONSE
        mock_client.return_value = MagicMock()

        gen = ReplyGenerator()
        reviews = [
            {"review_text": "배송 늦음", "rating": 2},
            {"review_text": "품질 불량", "rating": 1},
        ]
        results = gen.generate_batch(reviews)

        assert len(results) == 2
        assert results[0]["reply"] == "배송 지연 답변"
        assert results[1]["reply"] == "품질 불량 답변"

    def test_empty_input(self, mock_call, mock_client):
        mock_client.return_value = MagicMock()

        gen = ReplyGenerator()
        results = gen.generate_batch([])

        assert not results
        mock_call.assert_not_called()
