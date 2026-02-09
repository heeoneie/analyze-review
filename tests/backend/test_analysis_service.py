import pandas as pd

from backend.services.analysis_service import _compute_stats


class TestComputeStats:
    def test_basic_stats(self, sample_reviews_df, negative_reviews_df):
        result = _compute_stats(sample_reviews_df, negative_reviews_df, rating_threshold=3)
        assert result["total_reviews"] == 10
        assert result["negative_reviews"] == 6
        assert result["negative_ratio"] == 60.0
        assert result["rating_threshold"] == 3

    def test_rating_distribution_keys_are_strings(self, sample_reviews_df, negative_reviews_df):
        result = _compute_stats(sample_reviews_df, negative_reviews_df, rating_threshold=3)
        for key in result["rating_distribution"]:
            assert isinstance(key, str)

    def test_no_negative_reviews(self):
        df = pd.DataFrame({"rating": [5, 5, 5], "review_text": ["a", "b", "c"]})
        negative_df = df[df["rating"] <= 3]
        result = _compute_stats(df, negative_df, rating_threshold=3)
        assert result["negative_reviews"] == 0
        assert result["negative_ratio"] == 0.0

    def test_empty_dataframes(self):
        df = pd.DataFrame({"rating": pd.Series(dtype="float64")})
        negative_df = df.copy()
        result = _compute_stats(df, negative_df, rating_threshold=3)
        assert result["total_reviews"] == 0
        assert result["negative_ratio"] == 0.0
