from core.utils.json_utils import extract_json_from_text


class TestExtractJsonFromText:
    def test_valid_json_string(self):
        text = '{"categories": [{"category": "delivery_delay"}]}'
        result = extract_json_from_text(text)
        assert result is not None
        assert "categories" in result
        assert result["categories"][0]["category"] == "delivery_delay"

    def test_json_in_code_block(self):
        text = '```json\n{"key": "value"}\n```'
        result = extract_json_from_text(text)
        assert result == {"key": "value"}

    def test_json_in_code_block_no_lang(self):
        text = '```\n{"key": "value"}\n```'
        result = extract_json_from_text(text)
        assert result == {"key": "value"}

    def test_json_embedded_in_text(self):
        text = 'Here is the result: {"key": "value"} done.'
        result = extract_json_from_text(text)
        assert result == {"key": "value"}

    def test_double_braces_repair(self):
        text = '{{"key": "value"}}'
        result = extract_json_from_text(text)
        assert result == {"key": "value"}

    def test_trailing_comma_in_object_repair(self):
        text = '{"a": 1, "b": 2,}'
        result = extract_json_from_text(text)
        assert result == {"a": 1, "b": 2}

    def test_trailing_comma_in_array_repair(self):
        text = '{"items": [1, 2, 3,]}'
        result = extract_json_from_text(text)
        assert result == {"items": [1, 2, 3]}

    def test_no_json_returns_none(self):
        text = "This is just plain text with no braces"
        result = extract_json_from_text(text)
        assert result is None

    def test_empty_string_returns_none(self):
        result = extract_json_from_text("")
        assert result is None

    def test_nested_json_objects(self):
        text = '{"outer": {"inner": "value"}}'
        result = extract_json_from_text(text)
        assert result == {"outer": {"inner": "value"}}

    def test_complex_categories_response(self):
        text = (
            '```json\n{"categories": ['
            '{"review_number": 1, "category": "poor_quality",'
            ' "brief_issue": "Broke fast"}, '
            '{"review_number": 2, "category": "delivery_delay",'
            ' "brief_issue": "Late"}]}\n```'
        )
        result = extract_json_from_text(text)
        assert len(result["categories"]) == 2

    def test_malformed_json_returns_none(self):
        text = "{key: value}"
        result = extract_json_from_text(text)
        assert result is None
