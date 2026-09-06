"""수집한 리뷰의 저장·조회 테스트.

여기서 제일 중요한 것은 **매장 격리**다. 리뷰는 손님 개인정보를 담을 수
있고 매장 사이에 섞이면 개인정보보호법 제26조 ⑤ 위반이다 (형사처벌).
조건을 만드는 곳이 `_mine` 한 군데뿐이라도, 엔드포인트가 그걸 실제로
쓰는지는 따로 고정해 둬야 한다.
"""

import pytest

from backend.database.models import Review, Store, User
from backend.routers import reviews as reviews_router
from backend.services import auth_service
from core import config


@pytest.fixture(name="kakao_on")
def fixture_kakao_on(monkeypatch):
    """카카오 로그인이 켜진 구성. 매장 단위로 갈리는 경로다."""
    monkeypatch.setattr(config, "SESSION_SECRET", "test-secret-key-do-not-use")
    monkeypatch.setattr(config, "KAKAO_LOGIN_ENABLED", True)


def _make_store(db_session, kakao_id: str, name: str) -> Store:
    user = User(kakao_id=kakao_id)
    db_session.add(user)
    db_session.commit()
    store = Store(owner_user_id=user.id, name=name)
    db_session.add(store)
    db_session.commit()
    return store


def _login(client, store, db_session):
    owner = db_session.get(User, store.owner_user_id)
    client.cookies.set(auth_service.SESSION_COOKIE, auth_service.issue_session(owner.id))


def _add_review(db_session, store_id, rating, body, source="coupang"):
    db_session.add(Review(store_id=store_id, source=source, rating=rating, body=body))
    db_session.commit()


class TestStoreIsolation:
    """다른 사장님의 리뷰가 절대 보이면 안 된다."""

    @pytest.fixture(name="two_stores")
    def fixture_two_stores(self, db_session, kakao_on):  # pylint: disable=unused-argument
        a = _make_store(db_session, "1111", "가게A")
        b = _make_store(db_session, "2222", "가게B")
        _add_review(db_session, a.id, 5, "가게A 의 리뷰")
        _add_review(db_session, b.id, 5, "가게B 의 리뷰")
        _add_review(db_session, None, 5, "접속코드 시절 리뷰")
        return a, b

    def test_list_shows_only_own_reviews(self, client, db_session, two_stores):
        a, _ = two_stores
        _login(client, a, db_session)

        body = client.get("/api/reviews").json()

        assert body["total"] == 1
        assert [r["Reviews"] for r in body["reviews"]] == ["가게A 의 리뷰"]

    def test_prioritized_shows_only_own_reviews(self, client, db_session, two_stores):
        a, b = two_stores
        _add_review(db_session, a.id, 1, "가게A 의 불만")
        _add_review(db_session, b.id, 1, "가게B 의 불만")
        _login(client, a, db_session)

        body = client.get("/api/reviews/prioritized").json()

        assert [r["Reviews"] for r in body["reviews"]] == ["가게A 의 불만"]

    def test_summary_counts_only_own_reviews(self, client, db_session, two_stores):
        a, _ = two_stores
        _login(client, a, db_session)

        assert client.get("/api/reviews/summary").json()["total"] == 1

    def test_legacy_null_bucket_is_separate(self, client, db_session, two_stores):
        """store_id 가 NULL 인 이행기 행이 매장 조회에 섞이면 안 된다."""
        a, _ = two_stores
        _login(client, a, db_session)

        bodies = [r["Reviews"] for r in client.get("/api/reviews").json()["reviews"]]

        assert "접속코드 시절 리뷰" not in bodies

    def test_login_required_when_kakao_enabled(self, client, two_stores):  # pylint: disable=unused-argument
        assert client.get("/api/reviews").status_code == 401


class TestAccessCodePath:
    """카카오 로그인을 켜기 전 경로. 매장이 없고 NULL 버킷을 쓴다."""

    @pytest.fixture(name="access_code_only")
    def fixture_access_code_only(self, monkeypatch):
        monkeypatch.setattr(config, "KAKAO_LOGIN_ENABLED", False)
        monkeypatch.setattr(config, "ACCESS_CODE", "")

    def test_list_reads_null_bucket(self, client, db_session, access_code_only):  # pylint: disable=unused-argument
        _add_review(db_session, None, 4, "이행기 리뷰")
        store = _make_store(db_session, "3333", "가게C")
        _add_review(db_session, store.id, 4, "매장 리뷰")

        body = client.get("/api/reviews").json()

        assert [r["Reviews"] for r in body["reviews"]] == ["이행기 리뷰"]


class TestListing:
    @pytest.fixture(name="store")
    def fixture_store(self, client, db_session, kakao_on):  # pylint: disable=unused-argument
        store = _make_store(db_session, "9999", "가게")
        _login(client, store, db_session)
        return store

    def test_newest_first(self, client, db_session, store):
        for i in range(3):
            _add_review(db_session, store.id, 5, f"리뷰{i}")

        bodies = [r["Reviews"] for r in client.get("/api/reviews").json()["reviews"]]

        assert bodies == ["리뷰2", "리뷰1", "리뷰0"]

    def test_pagination(self, client, db_session, store):
        for i in range(5):
            _add_review(db_session, store.id, 5, f"리뷰{i}")

        body = client.get("/api/reviews", params={"page": 2, "page_size": 2}).json()

        assert body["total"] == 5
        assert body["total_pages"] == 3
        assert len(body["reviews"]) == 2

    def test_empty_store_returns_empty_page(self, client, store):  # pylint: disable=unused-argument
        body = client.get("/api/reviews").json()

        assert body == {
            "reviews": [], "total": 0, "page": 1, "page_size": 20, "total_pages": 0,
        }

    def test_prioritized_excludes_positive_reviews(self, client, db_session, store):
        _add_review(db_session, store.id, 5, "맛있어요")
        _add_review(db_session, store.id, 2, "너무 짜요")

        bodies = [
            r["Reviews"]
            for r in client.get("/api/reviews/prioritized").json()["reviews"]
        ]

        assert bodies == ["너무 짜요"]

    def test_prioritized_level_filter(self, client, db_session, store):
        _add_review(db_session, store.id, 1, "환불해주세요 음식에서 이물질이 나왔습니다")
        _add_review(db_session, store.id, 3, "그냥 그래요")

        body = client.get(
            "/api/reviews/prioritized", params={"level": "low"},
        ).json()

        assert all(r["priority"]["level"] == "low" for r in body["reviews"])

    def test_summary_numbers(self, client, db_session, store):
        _add_review(db_session, store.id, 5, "좋아요")
        _add_review(db_session, store.id, 5, "맛있어요")
        _add_review(db_session, store.id, 1, "별로")

        body = client.get("/api/reviews/summary").json()

        assert body["total"] == 3
        assert body["negative"] == 1
        assert body["rating_average"] == pytest.approx(3.67, abs=0.01)
        assert body["last_collected_at"] is not None

    def test_timestamps_carry_a_utc_offset(self, client, db_session, store):
        """오프셋이 없으면 브라우저가 현지 시각으로 읽어 9시간 어긋난다.

        SQLite 가 tz 를 보존하지 않아 읽을 때 naive 로 돌아오는 탓이다.
        """
        _add_review(db_session, store.id, 5, "좋아요")

        listed = client.get("/api/reviews").json()["reviews"][0]
        summary = client.get("/api/reviews/summary").json()

        assert listed["created_at"].endswith("+00:00")
        assert summary["last_collected_at"].endswith("+00:00")

    def test_summary_on_empty_store_does_not_divide_by_zero(self, client, store):  # pylint: disable=unused-argument
        body = client.get("/api/reviews/summary").json()

        assert body["negative_rate"] == 0.0
        assert body["rating_average"] == 0.0
        assert body["last_collected_at"] is None


class TestPersist:
    """수집 결과를 행으로 옮기는 부분. 크롤러 없이 직접 부른다."""

    @pytest.fixture(name="store")
    def fixture_store(self, db_session):
        return _make_store(db_session, "5555", "가게")

    def test_saves_valid_reviews(self, db_session, store):
        saved, _ = reviews_router._persist(  # pylint: disable=protected-access
            db_session, store, "coupang", "https://example.com/1",
            [{"Ratings": 5, "Reviews": "맛있어요"}, {"Ratings": 2, "Reviews": "짜요"}],
        )

        assert saved == 2
        assert db_session.query(Review).count() == 2

    def test_skips_rows_that_would_violate_the_check_constraint(self, db_session, store):
        """별점이 범위를 벗어난 한 건 때문에 멀쩡한 리뷰까지 잃으면 안 된다."""
        saved, _ = reviews_router._persist(  # pylint: disable=protected-access
            db_session, store, "coupang", "https://example.com/1",
            [
                {"Ratings": 9, "Reviews": "별점이 이상함"},
                {"Ratings": 0, "Reviews": "별점이 0"},
                {"Ratings": 5, "Reviews": "정상 리뷰"},
            ],
        )

        assert saved == 1
        assert [r.body for r in db_session.query(Review).all()] == ["정상 리뷰"]

    def test_skips_empty_bodies(self, db_session, store):
        """별점만 남긴 리뷰가 많다. 답글을 달 대상이 아니라 저장하지 않는다."""
        saved, _ = reviews_router._persist(  # pylint: disable=protected-access
            db_session, store, "coupang", "https://example.com/1",
            [{"Ratings": 5, "Reviews": "  "}, {"Ratings": 5, "Reviews": None}],
        )

        assert saved == 0

    def test_skips_unparsable_rating(self, db_session, store):
        saved, _ = reviews_router._persist(  # pylint: disable=protected-access
            db_session, store, "coupang", "https://example.com/1",
            [{"Ratings": "다섯개", "Reviews": "본문은 있음"}],
        )

        assert saved == 0

    def test_truncates_overlong_body(self, db_session, store):
        """컬럼이 String(4096) 이다. 넘치면 자르고 넣는다."""
        reviews_router._persist(  # pylint: disable=protected-access
            db_session, store, "coupang", "https://example.com/1",
            [{"Ratings": 5, "Reviews": "가" * 5000}],
        )

        assert len(db_session.query(Review).one().body) == 4096

    def test_tags_rows_with_the_store(self, db_session, store):
        reviews_router._persist(  # pylint: disable=protected-access
            db_session, store, "naver", "https://example.com/1",
            [{"Ratings": 5, "Reviews": "리뷰"}],
        )

        row = db_session.query(Review).one()
        assert row.store_id == store.id
        assert row.source == "naver"


class TestCollectEndpoint:
    """크롤러와 저장을 잇는 부분. 크롤러는 가짜로 바꿔 외부에 나가지 않는다."""

    @pytest.fixture(name="store")
    def fixture_store(self, client, db_session, kakao_on):  # pylint: disable=unused-argument
        store = _make_store(db_session, "7777", "가게")
        _login(client, store, db_session)
        return store

    @staticmethod
    def _fake_crawler(monkeypatch, result=None, error=None):
        """`collect` 안에서 지연 임포트하므로 원본 모듈에 심어야 한다."""
        async def fake(url, max_pages):  # pylint: disable=unused-argument
            if error:
                raise error
            return "coupang", result

        monkeypatch.setattr(
            "backend.services.crawler_service.crawl_reviews", fake,
        )

    def test_stores_crawled_reviews(self, client, db_session, store, monkeypatch):
        self._fake_crawler(monkeypatch, {
            "reviews": [
                {"Ratings": 5, "Reviews": "맛있어요"},
                {"Ratings": 1, "Reviews": "별로예요"},
            ],
            "total_count": 2,
            "rating_average": 3.0,
        })

        body = client.post(
            "/api/reviews/collect", json={"url": "https://www.coupang.com/vp/products/1"},
        ).json()

        assert body["saved"] == 2
        assert body["platform"] == "coupang"
        rows = db_session.query(Review).all()
        assert {r.body for r in rows} == {"맛있어요", "별로예요"}
        assert {r.store_id for r in rows} == {store.id}

    def test_collected_reviews_show_up_in_the_list(self, client, store, monkeypatch):  # pylint: disable=unused-argument
        """수집한 것이 곧바로 목록에 보여야 한다. 화면이 이 흐름으로 돈다."""
        self._fake_crawler(monkeypatch, {
            "reviews": [{"Ratings": 2, "Reviews": "국물이 짜요"}],
            "total_count": 1, "rating_average": 2.0,
        })
        client.post(
            "/api/reviews/collect", json={"url": "https://www.coupang.com/vp/products/1"},
        )

        listed = client.get("/api/reviews").json()
        prioritized = client.get("/api/reviews/prioritized").json()

        assert [r["Reviews"] for r in listed["reviews"]] == ["국물이 짜요"]
        assert [r["Reviews"] for r in prioritized["reviews"]] == ["국물이 짜요"]

    def test_unsupported_platform_is_a_400(self, client, store, monkeypatch):  # pylint: disable=unused-argument
        self._fake_crawler(monkeypatch, error=ValueError("지원하지 않는 플랫폼입니다"))

        response = client.post(
            "/api/reviews/collect", json={"url": "https://example.com/x"},
        )

        assert response.status_code == 400
        assert "지원하지" in response.json()["detail"]

    def test_crawler_failure_is_a_502_not_a_500(self, client, store, monkeypatch):  # pylint: disable=unused-argument
        """상대 사이트 문제다. 사장님에게는 다시 시도하라고 안내한다."""
        self._fake_crawler(monkeypatch, error=RuntimeError("연결 끊김"))

        response = client.post(
            "/api/reviews/collect", json={"url": "https://www.coupang.com/vp/products/1"},
        )

        assert response.status_code == 502
        # 내부 예외 문구가 그대로 새어 나가면 안 된다.
        assert "연결 끊김" not in response.json()["detail"]

    def test_recollecting_the_same_product_does_not_duplicate(self, db_session, store):
        """사장님은 새 리뷰를 보려고 같은 상품을 다시 수집한다.

        막지 않으면 누를 때마다 목록이 두 배가 된다.
        """
        url = "https://www.coupang.com/vp/products/1"
        payload = [{"Ratings": 5, "Reviews": "맛있어요"}, {"Ratings": 1, "Reviews": "짜요"}]

        first, _ = reviews_router._persist(  # pylint: disable=protected-access
            db_session, store, "coupang", url, payload)
        second, skipped = reviews_router._persist(  # pylint: disable=protected-access
            db_session, store, "coupang", url, payload)

        assert (first, second, skipped) == (2, 0, 2)
        assert db_session.query(Review).count() == 2

    def test_recollecting_picks_up_new_reviews(self, db_session, store):
        """이미 있는 것은 넘어가고 새로 달린 것만 담는다."""
        url = "https://www.coupang.com/vp/products/1"
        reviews_router._persist(  # pylint: disable=protected-access
            db_session, store, "coupang", url, [{"Ratings": 5, "Reviews": "맛있어요"}])

        saved, skipped = reviews_router._persist(  # pylint: disable=protected-access
            db_session, store, "coupang", url,
            [{"Ratings": 5, "Reviews": "맛있어요"}, {"Ratings": 3, "Reviews": "새로 달린 리뷰"}])

        assert (saved, skipped) == (1, 1)
        assert db_session.query(Review).count() == 2

    def test_duplicates_inside_one_batch_are_collapsed(self, db_session, store):
        saved, skipped = reviews_router._persist(  # pylint: disable=protected-access
            db_session, store, "coupang", "https://example.com/1",
            [{"Ratings": 5, "Reviews": "같은 글"}, {"Ratings": 5, "Reviews": "같은 글"}])

        assert (saved, skipped) == (1, 1)

    def test_other_stores_reviews_do_not_block_collection(self, db_session, store):
        """중복 검사도 매장 안에서만 본다. 남의 매장 글 때문에 건너뛰면 안 된다."""
        other = _make_store(db_session, "8888", "다른 가게")
        url = "https://www.coupang.com/vp/products/1"
        reviews_router._persist(  # pylint: disable=protected-access
            db_session, other, "coupang", url, [{"Ratings": 5, "Reviews": "맛있어요"}])

        saved, skipped = reviews_router._persist(  # pylint: disable=protected-access
            db_session, store, "coupang", url, [{"Ratings": 5, "Reviews": "맛있어요"}])

        assert (saved, skipped) == (1, 0)

    def test_different_product_is_collected_separately(self, db_session, store):
        """상품이 다르면 글이 같아도 각각 담는다."""
        reviews_router._persist(  # pylint: disable=protected-access
            db_session, store, "coupang", "https://www.coupang.com/vp/products/1",
            [{"Ratings": 5, "Reviews": "맛있어요"}])

        saved, _ = reviews_router._persist(  # pylint: disable=protected-access
            db_session, store, "coupang", "https://www.coupang.com/vp/products/2",
            [{"Ratings": 5, "Reviews": "맛있어요"}])

        assert saved == 1
        assert db_session.query(Review).count() == 2
