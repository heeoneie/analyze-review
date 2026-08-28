"""계정(카카오 로그인)과 답글 이력 기록 테스트."""

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from starlette.testclient import TestClient

from backend.database.database import get_db
from backend.database.models import Base, ReplySample, Store, User
from backend.main import app
from backend.services import auth_service, reply_history
from core import config


@pytest.fixture(name="db_session")
def fixture_db_session():
    """테스트마다 새 인메모리 DB. StaticPool 이라야 커넥션이 공유된다."""
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    session = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)()
    yield session
    session.close()


@pytest.fixture(name="client")
def fixture_client(db_session):
    app.dependency_overrides[get_db] = lambda: db_session
    yield TestClient(app)
    app.dependency_overrides.clear()


@pytest.fixture(name="secret")
def fixture_secret(monkeypatch):
    monkeypatch.setattr(config, "SESSION_SECRET", "test-secret-key-do-not-use")


@pytest.fixture(name="logged_in")
def fixture_logged_in(client, db_session, secret):  # pylint: disable=unused-argument
    """세션 쿠키가 꽂힌 클라이언트와 그 사용자."""
    user = User(kakao_id="12345", nickname="사장님")
    db_session.add(user)
    db_session.commit()
    client.cookies.set(auth_service.SESSION_COOKIE, auth_service.issue_session(user.id))
    return client, user


class TestSessionCookie:
    def test_roundtrip(self, secret):  # pylint: disable=unused-argument
        assert auth_service.read_session(auth_service.issue_session(7)) == 7

    def test_tampered_cookie_rejected(self, secret):  # pylint: disable=unused-argument
        raw = auth_service.issue_session(7)
        # 서명 앞의 페이로드만 바꿔치기해도 통과하면 안 된다.
        tampered = raw[:-3] + ("aaa" if not raw.endswith("aaa") else "bbb")
        assert auth_service.read_session(tampered) is None

    def test_cookie_from_other_secret_rejected(self, monkeypatch):
        monkeypatch.setattr(config, "SESSION_SECRET", "secret-a")
        raw = auth_service.issue_session(7)
        monkeypatch.setattr(config, "SESSION_SECRET", "secret-b")
        assert auth_service.read_session(raw) is None

    def test_empty_cookie(self, secret):  # pylint: disable=unused-argument
        assert auth_service.read_session("") is None


class TestOAuthState:
    def test_matching_state_passes(self, secret):  # pylint: disable=unused-argument
        state = auth_service.issue_state()
        assert auth_service.verify_state(state, state) is True

    def test_mismatched_state_fails(self, secret):  # pylint: disable=unused-argument
        assert auth_service.verify_state(
            auth_service.issue_state(), auth_service.issue_state()
        ) is False

    def test_missing_state_fails(self, secret):  # pylint: disable=unused-argument
        state = auth_service.issue_state()
        assert auth_service.verify_state("", state) is False
        assert auth_service.verify_state(state, "") is False

    def test_forged_state_fails(self, secret):  # pylint: disable=unused-argument
        # 쿠키와 쿼리를 같은 값으로 맞춰도 우리 서명이 아니면 안 된다.
        assert auth_service.verify_state("not-signed", "not-signed") is False


class TestMe:
    def test_anonymous(self, client):
        body = client.get("/api/auth/me").json()
        assert body == {"authenticated": False, "user": None, "store": None}

    def test_logged_in_without_store(self, logged_in):
        client, _ = logged_in
        body = client.get("/api/auth/me").json()
        assert body["authenticated"] is True
        assert body["store"] is None


class TestClaimStore:
    def test_correct_code_claims_store(self, logged_in, db_session, monkeypatch):
        monkeypatch.setattr(config, "ACCESS_CODE", "doya-1877")
        monkeypatch.setattr(config, "STORE_NAME", "도야짬뽕 부천시청점")
        client, user = logged_in

        resp = client.post("/api/auth/claim-store", json={"access_code": "doya-1877"})
        assert resp.status_code == 200
        assert resp.json()["store"]["name"] == "도야짬뽕 부천시청점"

        store = db_session.query(Store).one()
        assert store.owner_user_id == user.id

    def test_wrong_code_rejected(self, logged_in, db_session, monkeypatch):
        monkeypatch.setattr(config, "ACCESS_CODE", "doya-1877")
        client, _ = logged_in
        resp = client.post("/api/auth/claim-store", json={"access_code": "guess"})
        assert resp.status_code == 401
        assert db_session.query(Store).count() == 0

    def test_already_claimed_by_someone_else(self, logged_in, db_session, monkeypatch):
        """먼저 이관한 사람이 있으면 코드를 알아도 가로챌 수 없다."""
        monkeypatch.setattr(config, "ACCESS_CODE", "doya-1877")
        monkeypatch.setattr(config, "STORE_NAME", "도야짬뽕 부천시청점")
        other = User(kakao_id="99999")
        db_session.add(other)
        db_session.commit()
        db_session.add(Store(owner_user_id=other.id, name="도야짬뽕 부천시청점"))
        db_session.commit()

        client, _ = logged_in
        resp = client.post("/api/auth/claim-store", json={"access_code": "doya-1877"})
        assert resp.status_code == 409

    def test_requires_login(self, client, monkeypatch):
        monkeypatch.setattr(config, "ACCESS_CODE", "doya-1877")
        assert client.post(
            "/api/auth/claim-store", json={"access_code": "doya-1877"}
        ).status_code == 401


class TestSanitizeReviewBody:
    @pytest.mark.parametrize("raw,gone", [
        ("연락 주세요 hong@example.com", "hong@example.com"),
        ("010-1234-5678 로 전화 주세요", "010-1234-5678"),
        ("01012345678 입니다", "01012345678"),
        ("주문번호 20260828123456 확인", "20260828123456"),
    ])
    def test_contact_info_removed(self, raw, gone):
        assert gone not in reply_history.sanitize_review_body(raw)

    def test_ordinary_text_survives(self):
        text = "짬뽕이 너무 맛있었어요. 다음에 또 시킬게요"
        assert reply_history.sanitize_review_body(text) == text

    def test_rating_like_numbers_survive(self):
        # 별점·금액이 [번호] 로 바뀌면 안 된다.
        assert "12000" in reply_history.sanitize_review_body("12000원인데 만족합니다")


class TestReplyHistory:
    @pytest.fixture(name="store")
    def fixture_store(self, db_session):
        user = User(kakao_id="1")
        db_session.add(user)
        db_session.commit()
        store = Store(owner_user_id=user.id, name="테스트 매장")
        db_session.add(store)
        db_session.commit()
        return store

    def test_generated_is_not_final_until_posted(self, db_session, store):
        sample = reply_history.record_generated(
            db_session, store_id=store.id, review_body="맛있어요", rating=5,
            menu="짬뽕", generated_reply="감사합니다",
        )
        assert sample.final_reply is None
        # 게시 전 답글은 학습에 쓰지 않는다.
        assert reply_history.style_examples(db_session, store.id) == []

    def test_unedited_finalize(self, db_session, store):
        sample = reply_history.record_generated(
            db_session, store_id=store.id, review_body="맛있어요", rating=5,
            menu="짬뽕", generated_reply="감사합니다",
        )
        reply_history.finalize(db_session, sample, "감사합니다")
        assert sample.was_edited is False
        assert sample.origin == "generated"

    def test_edited_finalize_is_flagged(self, db_session, store):
        sample = reply_history.record_generated(
            db_session, store_id=store.id, review_body="맛있어요", rating=5,
            menu="짬뽕", generated_reply="감사합니다",
        )
        reply_history.finalize(db_session, sample, "감사합니다! 또 오세요")
        assert sample.was_edited is True
        assert sample.origin == "edited"

    def test_whitespace_only_change_is_not_an_edit(self, db_session, store):
        sample = reply_history.record_generated(
            db_session, store_id=store.id, review_body="맛있어요", rating=5,
            menu="짬뽕", generated_reply="감사합니다",
        )
        reply_history.finalize(db_session, sample, "  감사합니다  ")
        assert sample.was_edited is False

    def test_style_examples_prefers_edited(self, db_session, store):
        reply_history.record_onboarding(
            db_session, store_id=store.id, review_body="a", rating=5,
            owner_reply="온보딩 답글",
        )
        edited = reply_history.record_generated(
            db_session, store_id=store.id, review_body="b", rating=5,
            menu="", generated_reply="생성본",
        )
        reply_history.finalize(db_session, edited, "사장님이 고친 답글")

        examples = reply_history.style_examples(db_session, store.id)
        assert [e.origin for e in examples] == ["edited", "onboarding"]

    def test_other_stores_are_not_mixed_in(self, db_session, store):
        other_user = User(kakao_id="2")
        db_session.add(other_user)
        db_session.commit()
        other = Store(owner_user_id=other_user.id, name="남의 매장")
        db_session.add(other)
        db_session.commit()
        reply_history.record_onboarding(
            db_session, store_id=other.id, review_body="x", rating=5,
            owner_reply="남의 말투",
        )
        assert reply_history.style_examples(db_session, store.id) == []


class TestTransitionalAuth:
    """카카오 설정 전에는 기존 접속코드가 계속 동작해야 한다.

    이 브랜치를 배포해도 지금 쓰고 계신 사장님의 화면이 끊기면 안 된다.
    """

    def test_access_code_path_still_works(self, client, monkeypatch):
        monkeypatch.setattr(config, "KAKAO_LOGIN_ENABLED", False)
        monkeypatch.setattr(config, "ACCESS_CODE", "doya-1877")
        resp = client.post(
            "/api/reply/store/finalize",
            json={"sample_id": 1, "final_reply": "감사합니다"},
            headers={"X-Access-Code": "doya-1877"},
        )
        # 매장이 없으니 기록은 안 되지만 401 로 막히지는 않는다.
        assert resp.status_code == 200
        assert resp.json() == {"recorded": False}

    def test_wrong_access_code_still_rejected(self, client, monkeypatch):
        monkeypatch.setattr(config, "KAKAO_LOGIN_ENABLED", False)
        monkeypatch.setattr(config, "ACCESS_CODE", "doya-1877")
        resp = client.post(
            "/api/reply/store/finalize",
            json={"sample_id": 1, "final_reply": "x"},
            headers={"X-Access-Code": "wrong"},
        )
        assert resp.status_code == 401

    def test_login_required_once_kakao_is_configured(self, client, monkeypatch):
        monkeypatch.setattr(config, "KAKAO_LOGIN_ENABLED", True)
        monkeypatch.setattr(config, "ACCESS_CODE", "doya-1877")
        resp = client.post(
            "/api/reply/store/finalize",
            json={"sample_id": 1, "final_reply": "x"},
            headers={"X-Access-Code": "doya-1877"},
        )
        # 접속코드를 들고 와도 계정 체계가 켜지면 로그인해야 한다.
        assert resp.status_code == 401


class TestFinalizeOwnership:
    def test_cannot_finalize_another_stores_sample(
        self, logged_in, db_session, monkeypatch,
    ):
        monkeypatch.setattr(config, "KAKAO_LOGIN_ENABLED", True)
        client, user = logged_in
        mine = Store(owner_user_id=user.id, name="내 매장")
        other_user = User(kakao_id="777")
        db_session.add_all([mine, other_user])
        db_session.commit()
        other = Store(owner_user_id=other_user.id, name="남의 매장")
        db_session.add(other)
        db_session.commit()
        victim = reply_history.record_generated(
            db_session, store_id=other.id, review_body="x", rating=5,
            menu="", generated_reply="남의 답글",
        )

        resp = client.post(
            "/api/reply/store/finalize",
            json={"sample_id": victim.id, "final_reply": "가로채기"},
        )
        assert resp.status_code == 404
        db_session.refresh(victim)
        assert victim.final_reply is None

    def test_missing_sample_is_404(self, logged_in, db_session, monkeypatch):
        monkeypatch.setattr(config, "KAKAO_LOGIN_ENABLED", True)
        client, user = logged_in
        db_session.add(Store(owner_user_id=user.id, name="내 매장"))
        db_session.commit()
        resp = client.post(
            "/api/reply/store/finalize",
            json={"sample_id": 999, "final_reply": "x"},
        )
        assert resp.status_code == 404


class TestNoAuthorColumn:
    """닉네임은 컬럼 자체가 없어야 한다. 저장할 자리가 없으면 실수도 없다."""

    def test_reply_sample_has_no_author_field(self):
        columns = set(ReplySample.__table__.columns.keys())
        for forbidden in ("author", "nickname", "customer_name", "user_name"):
            assert forbidden not in columns
