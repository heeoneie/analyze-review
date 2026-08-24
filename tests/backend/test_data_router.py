import io
import os

import pytest
from starlette.testclient import TestClient

from backend.main import app
from backend.routers.data import analysis_settings, uploaded_files


@pytest.fixture(autouse=True)
def reset_state():
    """각 테스트 전 모듈 레벨 상태 초기화."""
    uploaded_files.clear()
    analysis_settings.clear()
    analysis_settings["rating_threshold"] = 3
    yield
    # 업로드된 임시 파일 정리
    path = uploaded_files.get("current")
    if path and os.path.exists(path):
        os.unlink(path)


@pytest.fixture
def client():
    return TestClient(app)


class TestHealthCheck:
    def test_health_endpoint(self, client):
        resp = client.get("/api/health")
        assert resp.status_code == 200
        assert resp.json() == {"status": "ok"}


class TestSettings:
    def test_get_default_settings(self, client):
        resp = client.get("/api/data/settings")
        assert resp.status_code == 200
        assert resp.json() == {"rating_threshold": 3}

    def test_update_settings(self, client):
        resp = client.post("/api/data/settings", json={"rating_threshold": 2})
        assert resp.status_code == 200
        assert resp.json()["rating_threshold"] == 2

    def test_invalid_rating_threshold_too_high(self, client):
        resp = client.post("/api/data/settings", json={"rating_threshold": 6})
        assert resp.status_code == 422

    def test_invalid_rating_threshold_too_low(self, client):
        resp = client.post("/api/data/settings", json={"rating_threshold": 0})
        assert resp.status_code == 422


class TestUploadCsv:
    def test_upload_valid_csv(self, client):
        csv_content = b"Ratings,Reviews\n5,Great product\n1,Terrible quality\n3,Average\n"
        resp = client.post(
            "/api/data/upload",
            files={"file": ("test.csv", io.BytesIO(csv_content), "text/csv")},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["filename"] == "test.csv"
        assert data["total_rows"] == 3
        assert len(data["preview"]) == 3

    def test_upload_non_csv_rejected(self, client):
        resp = client.post(
            "/api/data/upload",
            files={"file": ("data.txt", io.BytesIO(b"text"), "text/plain")},
        )
        assert resp.status_code == 400


class TestGetReviews:
    def test_no_csv_uploaded(self, client):
        resp = client.get("/api/data/reviews")
        assert resp.status_code == 400

    def test_paginated_reviews(self, client):
        # CSV 먼저 업로드
        csv_content = b"Ratings,Reviews\n5,Good\n4,Nice\n3,Ok\n2,Bad\n1,Terrible\n"
        client.post(
            "/api/data/upload",
            files={"file": ("test.csv", io.BytesIO(csv_content), "text/csv")},
        )
        resp = client.get("/api/data/reviews", params={"page": 1, "page_size": 2})
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["reviews"]) == 2
        assert data["total"] == 5
        assert data["total_pages"] == 3


class TestUploadRatingValidation:
    """이슈 #34: 숫자가 아닌 별점은 업로드 시점에 거부한다"""

    def test_non_numeric_ratings_rejected(self, client):
        csv_content = (
            b"Ratings,Reviews\n"
            b"5 out of 5,Great product\n"
            b"1 out of 5,Terrible quality\n"
        )
        resp = client.post(
            "/api/data/upload",
            files={"file": ("bad.csv", io.BytesIO(csv_content), "text/csv")},
        )
        assert resp.status_code == 400
        assert "Ratings" in resp.json()["detail"]
        assert uploaded_files.get("current") is None

    def test_float_string_ratings_accepted(self, client):
        """'3.0' 처럼 실수 문자열로 온 별점은 통과시킨다"""
        csv_content = b'Ratings,Reviews\n"3.0",Ok\n"1.0",Bad\n'
        resp = client.post(
            "/api/data/upload",
            files={"file": ("floats.csv", io.BytesIO(csv_content), "text/csv")},
        )
        assert resp.status_code == 200

    def test_partially_empty_ratings_accepted(self, client):
        """일부 행만 비어 있으면 업로드는 허용한다"""
        csv_content = b"Ratings,Reviews\n,No rating\n2,Bad\n"
        resp = client.post(
            "/api/data/upload",
            files={"file": ("mixed.csv", io.BytesIO(csv_content), "text/csv")},
        )
        assert resp.status_code == 200


class TestGetPrioritizedReviews:
    def test_no_csv_uploaded(self, client):
        resp = client.get("/api/data/reviews/prioritized")
        assert resp.status_code == 400

    def test_string_ratings_do_not_500(self, client):
        """이슈 #34: 문자열 별점 CSV 에서 500 이 나지 않는다"""
        csv_content = (
            "Ratings,Reviews\n"
            '"3.0",환불해주세요 불량입니다\n'
            '"1.0",배송이 너무 늦었어요\n'
            ",별점 없는 리뷰\n"
            '"5.0",아주 만족합니다\n'
        ).encode()
        client.post(
            "/api/data/upload",
            files={"file": ("floats.csv", io.BytesIO(csv_content), "text/csv")},
        )
        resp = client.get("/api/data/reviews/prioritized")
        assert resp.status_code == 200
        data = resp.json()
        # 기본 threshold 3 → "3.0", "1.0" 만 부정 리뷰. 빈 값·5점은 제외
        assert data["total"] == 2
        assert all("priority" in r for r in data["reviews"])

    def test_level_filter(self, client):
        csv_content = "Ratings,Reviews\n1,환불 요청\n3,그냥\n".encode()
        client.post(
            "/api/data/upload",
            files={"file": ("t.csv", io.BytesIO(csv_content), "text/csv")},
        )
        resp = client.get(
            "/api/data/reviews/prioritized", params={"level": "low"}
        )
        assert resp.status_code == 200
        assert all(
            r["priority"]["level"] == "low" for r in resp.json()["reviews"]
        )
