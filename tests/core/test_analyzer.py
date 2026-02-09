import json
from unittest.mock import MagicMock, patch

import pytest

from core.analyzer import ReviewAnalyzer


@pytest.fixture
def analyzer():
    with patch("core.analyzer.get_client", return_value=MagicMock()):
        return ReviewAnalyzer()


# ── get_top_issues (pure logic) ──


class TestGetTopIssues:
    def test_returns_top_3_by_default(self, analyzer, sample_categorization):
        result = analyzer.get_top_issues(sample_categorization)
        assert len(result) == 3
        # delivery_delay(4) > poor_quality(3) > wrong_item(1) or others
        assert result[0]["category"] == "delivery_delay"
        assert result[0]["count"] == 4

    def test_percentage_calculation(self, analyzer, sample_categorization):
        result = analyzer.get_top_issues(sample_categorization)
        # delivery_delay: 4/10 = 40.0%
        assert result[0]["percentage"] == 40.0
        # poor_quality: 3/10 = 30.0%
        assert result[1]["percentage"] == 30.0

    def test_examples_capped_at_3(self, analyzer, sample_categorization):
        result = analyzer.get_top_issues(sample_categorization)
        for issue in result:
            assert len(issue["examples"]) <= 3

    def test_custom_top_n(self, analyzer, sample_categorization):
        result = analyzer.get_top_issues(sample_categorization, top_n=1)
        assert len(result) == 1
        assert result[0]["category"] == "delivery_delay"

    def test_empty_categories(self, analyzer, empty_categorization):
        result = analyzer.get_top_issues(empty_categorization)
        assert result == []

    def test_single_category(self, analyzer):
        data = {
            "categories": [
                {"review_number": i, "category": "poor_quality", "brief_issue": f"Issue {i}"}
                for i in range(1, 6)
            ]
        }
        result = analyzer.get_top_issues(data)
        assert len(result) == 1
        assert result[0]["count"] == 5
        assert result[0]["percentage"] == 100.0


# ── detect_emerging_issues (pure logic) ──


class TestDetectEmergingIssues:
    def test_detects_increase(self, analyzer, sample_categorization, comparison_categorization):
        result = analyzer.detect_emerging_issues(sample_categorization, comparison_categorization)
        # missing_parts: recent=1, comparison=0 → but recent_count < 5 → skipped
        # damaged_packaging: recent=1, comparison=0 → skipped (< 5)
        # delivery_delay: recent=4, comparison=3 → (4-3)/3 = 33.3% → included
        categories = [r["category"] for r in result]
        assert "delivery_delay" in categories

    def test_returns_max_3(self, analyzer):
        # 5개 카테고리 모두 > 20% 증가
        recent = {"categories": [
            {"review_number": i, "category": f"cat_{i % 5}", "brief_issue": f"Issue {i}"}
            for i in range(50)
        ]}
        comparison = {"categories": [
            {"review_number": i, "category": f"cat_{i % 5}", "brief_issue": f"Issue {i}"}
            for i in range(5)
        ]}
        result = analyzer.detect_emerging_issues(recent, comparison)
        assert len(result) <= 3

    def test_sorted_by_increase_rate_desc(self, analyzer):
        recent = {"categories": [
            {"review_number": 1, "category": "a", "brief_issue": "x"},
            {"review_number": 2, "category": "a", "brief_issue": "x"},
            {"review_number": 3, "category": "a", "brief_issue": "x"},
            {"review_number": 4, "category": "b", "brief_issue": "x"},
            {"review_number": 5, "category": "b", "brief_issue": "x"},
            {"review_number": 6, "category": "b", "brief_issue": "x"},
            {"review_number": 7, "category": "b", "brief_issue": "x"},
            {"review_number": 8, "category": "b", "brief_issue": "x"},
        ]}
        comparison = {"categories": [
            {"review_number": 1, "category": "a", "brief_issue": "x"},
            {"review_number": 2, "category": "a", "brief_issue": "x"},
            {"review_number": 3, "category": "b", "brief_issue": "x"},
        ]}
        result = analyzer.detect_emerging_issues(recent, comparison)
        if len(result) >= 2:
            assert result[0]["increase_rate"] >= result[1]["increase_rate"]

    def test_no_emerging_when_decrease(self, analyzer):
        recent = {"categories": [
            {"review_number": 1, "category": "a", "brief_issue": "x"},
        ]}
        comparison = {"categories": [
            {"review_number": i, "category": "a", "brief_issue": "x"}
            for i in range(1, 6)
        ]}
        result = analyzer.detect_emerging_issues(recent, comparison)
        assert result == []

    def test_zero_comparison_with_significant_volume(self, analyzer):
        recent = {"categories": [
            {"review_number": i, "category": "new_issue", "brief_issue": f"Issue {i}"}
            for i in range(1, 7)  # 6건 (>= 5)
        ]}
        comparison = {"categories": []}
        result = analyzer.detect_emerging_issues(recent, comparison)
        assert len(result) == 1
        assert result[0]["category"] == "new_issue"
        assert result[0]["increase_rate"] == float("inf")

    def test_zero_comparison_low_volume_excluded(self, analyzer):
        recent = {"categories": [
            {"review_number": i, "category": "rare", "brief_issue": f"Issue {i}"}
            for i in range(1, 4)  # 3건 (< 5)
        ]}
        comparison = {"categories": []}
        result = analyzer.detect_emerging_issues(recent, comparison)
        assert result == []

    def test_both_empty(self, analyzer, empty_categorization):
        result = analyzer.detect_emerging_issues(empty_categorization, empty_categorization)
        assert result == []


# ── categorize_issues (mocked LLM) ──


class TestCategorizeIssues:
    def test_calls_openai_and_parses_response(self, analyzer):
        mock_response = json.dumps({"categories": [{"review_number": 1, "category": "poor_quality", "brief_issue": "Bad"}]})
        with patch("core.analyzer.call_openai_json", return_value=mock_response):
            result = analyzer.categorize_issues(["Bad product"])
        assert "categories" in result

    def test_samples_at_200(self, analyzer):
        reviews = [f"Review {i}" for i in range(300)]
        with patch("core.analyzer.call_openai_json", return_value='{"categories": []}') as mock_call:
            with patch("core.analyzer.format_reviews") as mock_format:
                mock_format.return_value = "formatted"
                analyzer.categorize_issues(reviews)
                # format_reviews는 200개로 잘린 리스트로 호출돼야 함
                called_reviews = mock_format.call_args[0][0]
                assert len(called_reviews) == 200

    def test_raises_on_parse_failure(self, analyzer):
        with patch("core.analyzer.call_openai_json", return_value="not json at all"):
            with patch("core.analyzer.extract_json_from_text", return_value=None):
                with pytest.raises(ValueError, match="Failed to parse categorization"):
                    analyzer.categorize_issues(["Review"])


# ── generate_action_plan (mocked LLM) ──


class TestGenerateActionPlan:
    def test_returns_recommendations_list(self, analyzer, sample_top_issues, sample_emerging_issues):
        mock_response = json.dumps({"recommendations": ["액션 1", "액션 2", "액션 3"]})
        with patch("core.analyzer.call_openai_json", return_value=mock_response):
            result = analyzer.generate_action_plan(sample_top_issues, sample_emerging_issues)
        assert len(result) == 3

    def test_raises_on_parse_failure(self, analyzer, sample_top_issues, sample_emerging_issues):
        with patch("core.analyzer.call_openai_json", return_value="bad"):
            with patch("core.analyzer.extract_json_from_text", return_value=None):
                with pytest.raises(ValueError, match="Failed to parse recommendations"):
                    analyzer.generate_action_plan(sample_top_issues, sample_emerging_issues)

    def test_handles_empty_emerging_issues(self, analyzer, sample_top_issues):
        mock_response = json.dumps({"recommendations": ["액션 1"]})
        with patch("core.analyzer.call_openai_json", return_value=mock_response) as mock_call:
            analyzer.generate_action_plan(sample_top_issues, [])
            prompt_arg = mock_call.call_args[0][1]
            assert "No significant emerging issues detected." in prompt_arg
