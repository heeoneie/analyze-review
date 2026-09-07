"""말투 학습이 실제로 생성에 연결됐는지.

`style_examples()` 는 오래전부터 있었지만 부르는 곳이 없어서, 답글을 모으기만
하고 쓰지는 않았다. 여기서 고정하는 것은 "라우터가 그걸 꺼내 생성기로 넘긴다"
는 사실이다.

리뷰·답글은 전부 지어낸 것이다 (CLAUDE.md).
"""

import pytest

from backend.database.models import ReplySample
from backend.dependencies import store_or_access_code
from backend.routers import reply as reply_router
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
        assert reply_router._style_for(db_session, None, 5) is None  # pylint: disable=protected-access

    def test_store_without_samples_gets_no_style(self, db_session, make_store):
        store = make_store()

        assert reply_router._style_for(db_session, store, 5) is None  # pylint: disable=protected-access

    def test_positive_request_only_sees_positive_samples(self, db_session, make_store):
        """칭찬 답글과 사과 답글을 섞으면 어느 쪽도 닮지 않은 평균이 나온다."""
        store = make_store()
        _posted(db_session, store, 5, "감사합니다 또 오세요")
        _posted(db_session, store, 5, "고맙습니다 다음에 또 뵈어요")
        _posted(db_session, store, 1, "죄송합니다 다시는 이런 일 없게 하겠습니다")

        style = reply_router._style_for(db_session, store, 5)  # pylint: disable=protected-access

        replies = [e["reply"] for e in style.examples]
        assert replies == ["감사합니다 또 오세요", "고맙습니다 다음에 또 뵈어요"]

    def test_negative_request_only_sees_negative_samples(self, db_session, make_store):
        store = make_store()
        _posted(db_session, store, 5, "감사합니다 또 오세요")
        _posted(db_session, store, 2, "죄송합니다 다음엔 꼭 챙기겠습니다")
        _posted(db_session, store, 1, "불편을 드려 죄송합니다 바로 고치겠습니다")

        style = reply_router._style_for(db_session, store, 2)  # pylint: disable=protected-access

        replies = [e["reply"] for e in style.examples]
        assert "감사합니다 또 오세요" not in replies
        assert len(replies) == 2

    def test_other_stores_samples_never_leak(self, db_session, make_store):
        """매장 간 데이터를 섞으면 안 된다 (개인정보보호법 제26조 ⑤)."""
        mine = make_store("1111", "내 가게")
        other = make_store("2222", "남의 가게")
        _posted(db_session, other, 5, "남의 가게 말투입니다")
        _posted(db_session, other, 5, "남의 가게 인사말입니다")

        assert reply_router._style_for(db_session, mine, 5) is None  # pylint: disable=protected-access

    def test_length_window_follows_the_owner(self, db_session, make_store):
        """사장님이 짧게 쓰면 기준도 짧아져야 한다. 안 그러면 검사기가 되돌려보낸다."""
        store = make_store()
        _posted(db_session, store, 5, "가" * 30)
        _posted(db_session, store, 5, "나" * 30)

        style = reply_router._style_for(db_session, store, 5)  # pylint: disable=protected-access

        assert style.max_chars < config.POSITIVE_REPLY_MIN_CHARS

    def test_unposted_drafts_are_not_learned_from(self, db_session, make_store):
        """게시하지 않은 생성본을 배우면 모델이 자기 문장을 다시 배운다."""
        store = make_store()
        db_session.add(ReplySample(
            store_id=store.id, origin="generated", review_body="리뷰",
            rating=5, generated_reply="우리가 만든 답글", final_reply=None,
        ))
        db_session.commit()

        assert reply_router._style_for(db_session, store, 5) is None  # pylint: disable=protected-access


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
