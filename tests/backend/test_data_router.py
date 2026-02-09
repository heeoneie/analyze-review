import io
import os

import pytest
from starlette.testclient import TestClient

from backend.main import app
from backend.routers.data import uploaded_files, analysis_settings


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
