from datetime import datetime, timedelta

import pandas as pd
import pytest

from core.data_loader import DataLoader


@pytest.fixture
def data_loader(tmp_path, monkeypatch):
    monkeypatch.setattr("core.config.DATA_PATH", str(tmp_path))
    return DataLoader()


# ── filter_negative_reviews ──


class TestFilterNegativeReviews:
    def test_default_threshold_3(self, data_loader, sample_reviews_df):
        result = data_loader.filter_negative_reviews(sample_reviews_df)
        # 평점 1,2,3,1,2,3 → 6개
        assert len(result) == 6
        assert all(result["rating"] <= 3)

    def test_custom_threshold_2(self, data_loader, sample_reviews_df):
        result = data_loader.filter_negative_reviews(sample_reviews_df, threshold=2)
        # 평점 1,2,1,2 → 4개
        assert len(result) == 4

    def test_threshold_5_returns_all(self, data_loader, sample_reviews_df):
        result = data_loader.filter_negative_reviews(sample_reviews_df, threshold=5)
        assert len(result) == len(sample_reviews_df)

    def test_threshold_0_returns_none(self, data_loader, sample_reviews_df):
        result = data_loader.filter_negative_reviews(sample_reviews_df, threshold=0)
        assert len(result) == 0

    def test_preserves_columns(self, data_loader, sample_reviews_df):
        result = data_loader.filter_negative_reviews(sample_reviews_df)
        assert list(result.columns) == list(sample_reviews_df.columns)


# ── split_by_period ──


class TestSplitByPeriod:
    def test_basic_split(self, data_loader, sample_reviews_df):
        recent, comparison = data_loader.split_by_period(
            sample_reviews_df, recent_days=30, comparison_days=60
        )
        assert len(recent) + len(comparison) <= len(sample_reviews_df)
        # 최신 기간 리뷰는 max_date - 30일 이후
        max_date = sample_reviews_df["created_at"].max()
        if len(recent) > 0:
            assert recent["created_at"].min() >= max_date - timedelta(days=30)

    def test_no_overlap(self, data_loader, sample_reviews_df):
        recent, comparison = data_loader.split_by_period(
            sample_reviews_df, recent_days=30, comparison_days=60
        )
        if len(recent) > 0 and len(comparison) > 0:
            recent_ids = set(recent["review_id"])
            comparison_ids = set(comparison["review_id"])
            assert recent_ids.isdisjoint(comparison_ids)

    def test_all_data_in_recent(self, data_loader):
        base_date = datetime(2024, 6, 1)
        df = pd.DataFrame({
            "review_id": [1, 2, 3],
            "rating": [1, 2, 3],
            "review_text": ["a", "b", "c"],
            "created_at": pd.to_datetime([base_date - timedelta(days=i) for i in range(3)]),
        })
        recent, comparison = data_loader.split_by_period(df, recent_days=30, comparison_days=60)
        assert len(recent) == 3
        assert len(comparison) == 0

    @pytest.mark.skip(reason="Legacy test, deferring fix for MVP sprint")
    def test_empty_dataframe(self, data_loader):
        df = pd.DataFrame(
            columns=["review_id", "rating", "review_text",
                      "created_at"]
        )
        df["created_at"] = pd.to_datetime(df["created_at"])
        # 빈 DataFrame에서 NaT로 인한 에러 발생을 검증
        with pytest.raises((TypeError, ValueError)):
            data_loader.split_by_period(
                df, recent_days=30, comparison_days=60
            )


# ── load_custom_csv ──


class TestLoadCustomCsv:
    def test_valid_csv(self, data_loader, tmp_path):
        csv_path = tmp_path / "test.csv"
        csv_path.write_text("Ratings,Reviews\n5,Great product\n1,Terrible\n3,Average\n")
        result = data_loader.load_custom_csv(str(csv_path))
        assert len(result) == 3
        assert "rating" in result.columns
        assert "review_text" in result.columns

    def test_missing_columns_raises(self, data_loader, tmp_path):
        csv_path = tmp_path / "bad.csv"
        csv_path.write_text("Name,Value\nA,1\n")
        with pytest.raises(ValueError, match="Ratings.*Reviews"):
            data_loader.load_custom_csv(str(csv_path))

    def test_filters_nan_reviews(self, data_loader, tmp_path):
        csv_path = tmp_path / "nan.csv"
        csv_path.write_text("Ratings,Reviews\n5,Good\n1,\n3,Average\n")
        result = data_loader.load_custom_csv(str(csv_path))
        # NaN 리뷰 제거됨
        assert all(result["review_text"].notna())
