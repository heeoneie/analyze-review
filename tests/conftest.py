from datetime import datetime, timedelta

import pandas as pd
import pytest


@pytest.fixture
def sample_reviews_df():
    """10개 리뷰, 60일 범위, 다양한 평점."""
    base_date = datetime(2024, 6, 1)
    data = {
        "review_id": list(range(1, 11)),
        "rating": [1, 2, 3, 4, 5, 1, 2, 3, 4, 5],
        "review_text": [
            "Terrible product, broke after one day",
            "Delivery was super late, very disappointed",
            "Okay quality but not great, packaging damaged",
            "Pretty good overall, fast shipping",
            "Excellent! Best purchase ever",
            "Wrong item received, not what I ordered",
            "Missing parts in the box, very frustrating",
            "Average quality, price too high",
            "Nice product, would recommend",
            "Perfect, five stars!",
        ],
        "created_at": [
            base_date - timedelta(days=i * 6) for i in range(10)
        ],
    }
    df = pd.DataFrame(data)
    df["created_at"] = pd.to_datetime(df["created_at"])
    return df


@pytest.fixture
def negative_reviews_df(sample_reviews_df):
    """평점 <= 3 리뷰만."""
    return sample_reviews_df[
        sample_reviews_df["rating"] <= 3
    ].copy()


@pytest.fixture
def sample_categorization():
    """LLM 분류 결과 샘플."""
    return {"categories": [
        {"review_number": 1, "category": "poor_quality",
         "brief_issue": "Product broke after one day"},
        {"review_number": 2, "category": "delivery_delay",
         "brief_issue": "Super late delivery"},
        {"review_number": 3, "category": "damaged_packaging",
         "brief_issue": "Packaging was damaged"},
        {"review_number": 4, "category": "poor_quality",
         "brief_issue": "Quality below expectations"},
        {"review_number": 5, "category": "delivery_delay",
         "brief_issue": "Waited 3 weeks"},
        {"review_number": 6, "category": "wrong_item",
         "brief_issue": "Received wrong product"},
        {"review_number": 7, "category": "missing_parts",
         "brief_issue": "Parts missing from box"},
        {"review_number": 8, "category": "poor_quality",
         "brief_issue": "Cheap materials"},
        {"review_number": 9, "category": "delivery_delay",
         "brief_issue": "Delayed by 10 days"},
        {"review_number": 10, "category": "delivery_delay",
         "brief_issue": "Extremely slow shipping"},
    ]}


@pytest.fixture
def comparison_categorization():
    """비교 기간 분류 결과."""
    return {"categories": [
        {"review_number": 1, "category": "delivery_delay",
         "brief_issue": "Late delivery"},
        {"review_number": 2, "category": "delivery_delay",
         "brief_issue": "Slow shipping"},
        {"review_number": 3, "category": "delivery_delay",
         "brief_issue": "Package delayed"},
        {"review_number": 4, "category": "poor_quality",
         "brief_issue": "Bad quality"},
        {"review_number": 5, "category": "poor_quality",
         "brief_issue": "Broke quickly"},
        {"review_number": 6, "category": "poor_quality",
         "brief_issue": "Cheap"},
        {"review_number": 7, "category": "wrong_item",
         "brief_issue": "Wrong product"},
        {"review_number": 8, "category": "wrong_item",
         "brief_issue": "Wrong item sent"},
    ]}


@pytest.fixture
def empty_categorization():
    """빈 분류 결과."""
    return {"categories": []}


@pytest.fixture
def sample_top_issues():
    """미리 계산된 top issues."""
    return [
        {"category": "delivery_delay", "count": 4,
         "percentage": 40.0,
         "examples": ["Late", "Slow", "Delayed"]},
        {"category": "poor_quality", "count": 3,
         "percentage": 30.0,
         "examples": ["Broke", "Cheap", "Bad"]},
        {"category": "wrong_item", "count": 1,
         "percentage": 10.0,
         "examples": ["Wrong product"]},
    ]


@pytest.fixture
def sample_emerging_issues():
    """미리 계산된 emerging issues."""
    return [
        {"category": "missing_parts", "recent_count": 5,
         "comparison_count": 1, "increase_rate": 400.0},
    ]
