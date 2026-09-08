"""말투 학습이 실제로 생성에 연결됐는지.

`style_examples()` 는 오래전부터 있었지만 부르는 곳이 없어서, 답글을 모으기만
하고 쓰지는 않았다. 여기서 고정하는 것은 "라우터가 그걸 꺼내 생성기로 넘긴다"
는 사실이다.

리뷰·답글은 전부 지어낸 것이다 (CLAUDE.md).
"""

import pytest

from backend.database.models import ReplySample
from backend.dependencies import store_or_access_code
from backend.services import reply_history
from core import config


def _posted(db_session, store, rating, reply, *, review="리뷰 본문"):
    """사장님이 실제로 게시한 답글 한 건."""
    db_session.add(ReplySample(
        store_id=store.id, origin="edited", review_body=review,
        rating=rating, final_reply=reply,
    ))
    db_session.commit()


class TestStyleForStore:
    def test_no_store_means_no_style(self, db_session):
        """접속코드 경로에는 매장이 없어 표본을 고를 기준이 없다."""
        assert reply_history.style_profile_for(db_session, None, 5) is None

    def test_store_without_samples_gets_no_style(self, db_session, make_store):
        store = make_store()

        assert reply_history.style_profile_for(db_session, store, 5) is None

    def test_positive_request_only_sees_positive_samples(self, db_session, make_store):
        """칭찬 답글과 사과 답글을 섞으면 어느 쪽도 닮지 않은 평균이 나온다."""
        store = make_store()
        _posted(db_session, store, 5, "감사합니다 또 오세요")
        _posted(db_session, store, 5, "고맙습니다 다음에 또 뵈어요")
        _posted(db_session, store, 1, "죄송합니다 다시는 이런 일 없게 하겠습니다")

        style = reply_history.style_profile_for(db_session, store, 5)

        replies = [e["reply"] for e in style.examples]
        assert replies == ["감사합니다 또 오세요", "고맙습니다 다음에 또 뵈어요"]

    def test_negative_request_only_sees_negative_samples(self, db_session, make_store):
        store = make_store()
        _posted(db_session, store, 5, "감사합니다 또 오세요")
        _posted(db_session, store, 2, "죄송합니다 다음엔 꼭 챙기겠습니다")
        _posted(db_session, store, 1, "불편을 드려 죄송합니다 바로 고치겠습니다")

        style = reply_history.style_profile_for(db_session, store, 2)

        replies = [e["reply"] for e in style.examples]
        assert "감사합니다 또 오세요" not in replies
        assert len(replies) == 2

    def test_other_stores_samples_never_leak(self, db_session, make_store):
        """매장 간 데이터를 섞으면 안 된다 (개인정보보호법 제26조 ⑤)."""
        mine = make_store("1111", "내 가게")
        other = make_store("2222", "남의 가게")
        _posted(db_session, other, 5, "남의 가게 말투입니다")
        _posted(db_session, other, 5, "남의 가게 인사말입니다")

        assert reply_history.style_profile_for(db_session, mine, 5) is None

    def test_length_window_follows_the_owner(self, db_session, make_store):
        """사장님이 짧게 쓰면 기준도 짧아져야 한다. 안 그러면 검사기가 되돌려보낸다."""
        store = make_store()
        _posted(db_session, store, 5, "가" * 30)
        _posted(db_session, store, 5, "나" * 30)

        style = reply_history.style_profile_for(db_session, store, 5)

        assert style.max_chars < config.POSITIVE_REPLY_MIN_CHARS

    def test_unposted_drafts_are_not_learned_from(self, db_session, make_store):
        """게시하지 않은 생성본을 배우면 모델이 자기 문장을 다시 배운다."""
        store = make_store()
        db_session.add(ReplySample(
            store_id=store.id, origin="generated", review_body="리뷰",
            rating=5, generated_reply="우리가 만든 답글", final_reply=None,
        ))
        db_session.commit()

        assert reply_history.style_profile_for(db_session, store, 5) is None


class TestSentimentFilterHappensBeforeTheLimit:
    """개수를 먼저 자르고 성향으로 나누면 한쪽이 굶는다."""

    def test_many_positive_samples_do_not_starve_the_negative_path(
        self, db_session, make_store,
    ):
        store = make_store()
        for i in range(40):
            _posted(db_session, store, 5, f"감사합니다 고객님 {i}번째 답글입니다")
        _posted(db_session, store, 1, "죄송합니다 고객님 다시는 이런 일 없게 하겠습니다")
        _posted(db_session, store, 2, "죄송합니다 고객님 바로 확인해보겠습니다")

        style = reply_history.style_profile_for(db_session, store, 2)

        assert style is not None
        assert len(style.examples) == 2


class TestGeneratorReceivesStyle:
    """생성기까지 실제로 도달하는지. LLM 은 부르지 않는다."""

    @pytest.fixture(name="captured")
    def fixture_captured(self, monkeypatch):
        seen = {}

        def fake_generate(self, review_text=None, rating=5, menu=None, **kwargs):  # pylint: disable=unused-argument
            seen["style"] = kwargs.get("style")
            return {"reply": "답글", "sentiment": "positive"}

        monkeypatch.setattr(
            "core.reply_generator.ReplyGenerator.generate", fake_generate,
        )
        monkeypatch.setattr(config, "KAKAO_LOGIN_ENABLED", False)
        monkeypatch.setattr(config, "ACCESS_CODE", "")
        return seen

    def test_style_reaches_the_generator(self, client, db_session, captured, make_store):
        store = make_store()
        _posted(db_session, store, 5, "감사합니다 또 오세요")
        _posted(db_session, store, 5, "고맙습니다 또 뵈어요")
        # 접속코드 경로는 매장이 없으므로, 매장이 붙은 경로를 흉내 낸다.
        client.app.dependency_overrides[store_or_access_code] = lambda: store

        client.post("/api/reply/store/generate", json={
            "review_text": "맛있어요", "rating": 5, "menu": "짬뽕",
        })

        assert captured["style"] is not None
        assert len(captured["style"].examples) == 2


class TestOnboarding:
    """말투 학습의 콜드스타트를 메우는 경로."""

    @pytest.fixture(name="logged_in_store")
    def fixture_logged_in_store(self, client, make_store, monkeypatch):
        monkeypatch.setattr(config, "KAKAO_LOGIN_ENABLED", False)
        monkeypatch.setattr(config, "ACCESS_CODE", "")
        store = make_store()
        client.app.dependency_overrides[store_or_access_code] = lambda: store
        yield store
        client.app.dependency_overrides.pop(store_or_access_code, None)

    def test_new_store_is_not_learning_yet(self, client, logged_in_store):  # pylint: disable=unused-argument
        body = client.get("/api/reply/style/status").json()

        assert body == {
            "store": True, "positive": 0, "negative": 0,
            "learning": False, "needed": 2, "positive_from": 4,
        }

    def test_samples_are_saved_and_counted(self, client, logged_in_store):  # pylint: disable=unused-argument
        response = client.post("/api/reply/style/onboarding", json={"samples": [
            {"review_text": "맛있어요", "rating": 5, "reply": "감사합니다 고객님 또 오세요"},
            {"review_text": "좋아요", "rating": 5, "reply": "감사합니다 고객님 좋은 하루 되세요"},
        ]})

        assert response.json() == {"saved": 2}
        status = client.get("/api/reply/style/status").json()
        assert status["positive"] == 2
        assert status["learning"] is True

    def test_one_sample_is_not_enough_to_learn(self, client, logged_in_store):  # pylint: disable=unused-argument
        client.post("/api/reply/style/onboarding", json={"samples": [
            {"review_text": "맛있어요", "rating": 5, "reply": "감사합니다"},
        ]})

        assert client.get("/api/reply/style/status").json()["learning"] is False

    def test_onboarding_samples_feed_generation(self, client, db_session, logged_in_store):
        """담은 표본이 곧바로 말투 프로필이 되어야 한다."""
        client.post("/api/reply/style/onboarding", json={"samples": [
            {"review_text": "맛있어요", "rating": 5, "reply": "감사합니다 고객님 또 오세요"},
            {"review_text": "좋아요", "rating": 5, "reply": "감사합니다 고객님 좋은 하루 되세요"},
        ]})

        style = reply_history.style_profile_for(db_session, logged_in_store, 5)

        assert style is not None
        assert style.common_opening == "감사합니다 고객님"

    def test_contact_details_are_scrubbed(self, client, db_session, logged_in_store):  # pylint: disable=unused-argument
        """사장님이 답글에 연락처를 적는 일이 흔하다. 저장 전에 지운다."""
        client.post("/api/reply/style/onboarding", json={"samples": [
            {"review_text": "연락 주세요", "rating": 3,
             "reply": "010-1234-5678 로 연락 주세요"},
        ]})

        saved = db_session.query(ReplySample).one()
        assert "1234-5678" not in saved.final_reply
        assert "[연락처]" in saved.final_reply

    def test_empty_submission_is_rejected(self, client, logged_in_store):  # pylint: disable=unused-argument
        assert client.post(
            "/api/reply/style/onboarding", json={"samples": []},
        ).status_code == 422

    def test_status_serves_the_rating_threshold(self, client, logged_in_store, monkeypatch):  # pylint: disable=unused-argument
        """화면이 4를 따로 들고 있으면 서버 값이 바뀌는 날 조용히 어긋난다."""
        monkeypatch.setattr(config, "POSITIVE_RATING_THRESHOLD", 3)

        assert client.get("/api/reply/style/status").json()["positive_from"] == 3

    def test_access_code_path_has_nowhere_to_store(self, client, monkeypatch):
        """매장이 없으면 담을 곳이 없다. 화면은 온보딩을 띄우지 않는다."""
        monkeypatch.setattr(config, "KAKAO_LOGIN_ENABLED", False)
        monkeypatch.setattr(config, "ACCESS_CODE", "")

        status = client.get("/api/reply/style/status").json()

        assert status["store"] is False
        assert client.post("/api/reply/style/onboarding", json={"samples": [
            {"review_text": "맛있어요", "rating": 5, "reply": "감사합니다"},
        ]}).status_code == 409
