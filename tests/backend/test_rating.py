"""별점 파싱 단일 창구 테스트 (이슈 #34)"""

from backend.services.rating import DEFAULT_RATING, parse_rating


class TestParseRating:
    def test_int(self):
        assert parse_rating(4) == 4

    def test_float_string(self):
        """pandas 가 object 로 읽은 '3.0' 이 터지지 않는다"""
        assert parse_rating("3.0") == 3

    def test_int_string(self):
        assert parse_rating("2") == 2

    def test_whitespace_padded(self):
        assert parse_rating(" 1 ") == 1

    def test_float_truncates(self):
        assert parse_rating(2.7) == 2

    def test_empty_string_returns_default(self):
        assert parse_rating("") is None
        assert parse_rating("", DEFAULT_RATING) == DEFAULT_RATING

    def test_non_numeric_returns_default(self):
        assert parse_rating("5 out of 5") is None
        assert parse_rating("5 out of 5", DEFAULT_RATING) == DEFAULT_RATING

    def test_none_returns_default(self):
        assert parse_rating(None) is None
        assert parse_rating(None, DEFAULT_RATING) == DEFAULT_RATING

    def test_nan_returns_default(self):
        assert parse_rating(float("nan")) is None
