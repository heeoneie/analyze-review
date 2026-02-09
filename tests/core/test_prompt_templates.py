from core.utils.prompt_templates import format_reviews, build_zero_shot_prompt


class TestFormatReviews:
    def test_basic_formatting(self):
        result = format_reviews(["Review one", "Review two"])
        assert "1. Review one" in result
        assert "2. Review two" in result
        assert "---" in result

    def test_truncation_at_500_chars(self):
        long_text = "A" * 600
        result = format_reviews([long_text])
        # format_reviews는 text[:500]으로 잘라냄
        assert len(result.split(". ", 1)[1]) == 500

    def test_empty_list(self):
        result = format_reviews([])
        assert result == ""

    def test_single_review_no_separator(self):
        result = format_reviews(["Only one review"])
        assert result == "1. Only one review"
        assert "---" not in result

    def test_multiple_reviews_separator(self):
        result = format_reviews(["First", "Second", "Third"])
        parts = result.split("\n---\n")
        assert len(parts) == 3


class TestBuildZeroShotPrompt:
    def test_contains_review_count(self):
        result = build_zero_shot_prompt("reviews text", 42)
        assert "42 negative customer reviews" in result

    def test_contains_reviews_text(self):
        result = build_zero_shot_prompt("MY_REVIEW_TEXT", 1)
        assert "MY_REVIEW_TEXT" in result
