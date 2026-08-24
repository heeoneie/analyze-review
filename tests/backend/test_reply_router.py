"""답글 라우터의 접속 코드 잠금 테스트.

공개 URL 에 올라가는 서비스라 LLM 을 부르는 엔드포인트가 열려 있으면
링크를 아는 사람이 OpenAI 요금을 그대로 쓴다. 리뷰에서 실제로 뚫려 있었다.
"""

import importlib
from unittest.mock import patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from backend.routers import reply

# LLM 을 부르는 엔드포인트. 전부 잠겨 있어야 한다.
LLM_ENDPOINTS = [
    ("/api/reply/generate", {"review_text": "테스트", "rating": 2}),
    ("/api/reply/generate-batch", {"reviews": [{"review_text": "테스트", "rating": 2}]}),
    ("/api/reply/store/generate", {"review_text": "테스트", "rating": 5, "menu": "도야짬뽕"}),
]


def build_client():
    app = FastAPI()
    app.include_router(reply.router, prefix="/api/reply")
    return TestClient(app)


@pytest.fixture
def locked():
    with patch.object(reply.config, "ACCESS_CODE", "test-code"):
        yield build_client()


@pytest.fixture
def unlocked():
    with patch.object(reply.config, "ACCESS_CODE", ""):
        yield build_client()


class TestAccessGate:
    @pytest.mark.parametrize("path,payload", LLM_ENDPOINTS)
    def test_rejects_without_code(self, locked, path, payload):
        assert locked.post(path, json=payload).status_code == 401

    @pytest.mark.parametrize("path,payload", LLM_ENDPOINTS)
    def test_rejects_wrong_code(self, locked, path, payload):
        res = locked.post(path, json=payload, headers={"X-Access-Code": "nope"})
        assert res.status_code == 401

    def test_verify_accepts_right_code(self, locked):
        res = locked.post("/api/reply/verify", headers={"X-Access-Code": "test-code"})
        assert res.status_code == 200

    def test_ascii_symbols_work(self):
        # 기호가 섞여도 정상 동작해야 한다
        with patch.object(reply.config, "ACCESS_CODE", "doya-1877!#"):
            client = build_client()
            assert client.post(
                "/api/reply/verify", headers={"X-Access-Code": "doya-1877!#"}
            ).status_code == 200

    def test_wrong_code_is_401_not_500(self, locked):
        # compare_digest 가 str 을 그대로 받으면 비ASCII 헤더에서 TypeError 를 낸다.
        # bytes 로 비교하므로 500 이 아니라 401 이어야 한다.
        res = locked.post("/api/reply/verify", headers={"X-Access-Code": "wrong"})
        assert res.status_code == 401

    @pytest.mark.parametrize("path,payload", LLM_ENDPOINTS)
    def test_open_when_no_code_configured(self, unlocked, path, payload):
        # 코드를 비워 두면 잠그지 않는다 (로컬 개발)
        assert unlocked.post(path, json=payload).status_code != 401


class TestConfigEndpoint:
    def test_readable_without_code(self, locked):
        # 화면이 잠금 여부를 알아야 코드 입력 화면을 띄운다
        res = locked.get("/api/reply/config")
        assert res.status_code == 200
        assert res.json()["requires_code"] is True

    def test_reports_unlocked(self, unlocked):
        assert unlocked.get("/api/reply/config").json()["requires_code"] is False


class TestStoreRequestValidation:
    def test_rejects_empty_input(self, unlocked):
        res = unlocked.post(
            "/api/reply/store/generate", json={"review_text": "", "rating": 5, "menu": ""}
        )
        assert res.status_code == 400

    def test_rejects_out_of_range_rating(self, unlocked):
        res = unlocked.post(
            "/api/reply/store/generate", json={"review_text": "좋아요", "rating": 9}
        )
        assert res.status_code == 422


class TestAccessCodeValidation:
    """비ASCII 코드는 헤더로 전송조차 안 되므로 시작 시점에 막는다."""

    def test_rejects_non_ascii_at_startup(self, monkeypatch):
        monkeypatch.setenv("ACCESS_CODE", "도야2026")
        with pytest.raises(ValueError, match="ASCII"):
            importlib.reload(reply.config)

    def test_accepts_ascii(self, monkeypatch):
        monkeypatch.setenv("ACCESS_CODE", "doya-1877")
        importlib.reload(reply.config)
        assert reply.config.ACCESS_CODE == "doya-1877"
        monkeypatch.delenv("ACCESS_CODE")
        importlib.reload(reply.config)
