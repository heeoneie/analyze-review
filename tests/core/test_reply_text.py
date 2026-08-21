"""reply_text 테스트 — 매크로 답변을 기계적으로 걸러내는 층"""

from core.reply_text import (
    find_violations,
    first_sentence,
    last_sentence,
    opening_shape,
    openings_collide,
)

STORE = "도야짬뽕 부천시청점"


class TestSentenceSplit:
    def test_first_sentence(self):
        assert first_sentence("짬뽕 국물이 좋았죠. 다음에 또 뵙겠습니다.") == "짬뽕 국물이 좋았죠."

    def test_last_sentence(self):
        assert last_sentence("첫 문장입니다. 끝 문장입니다.") == "끝 문장입니다."

    def test_ignores_trailing_emoji_fragment(self):
        # 이모지만 남은 조각은 문장으로 세지 않는다
        assert last_sentence("잘 챙기겠습니다. 😊") == "잘 챙기겠습니다."

    def test_empty(self):
        assert first_sentence("") == ""


class TestBannedPhrases:
    def test_catches_thanks_for_ordering(self):
        found = find_violations("주문해 주셔서 진심으로 감사드립니다.", STORE)
        assert any("주문" in v for v in found)

    def test_catches_spacing_variant(self):
        # "주문해주셔서" 처럼 붙여 쓴 경우도 잡아야 한다
        assert find_violations("주문해주셔서 정말 감사합니다.", STORE)

    def test_catches_selected_variant(self):
        assert find_violations("선택해 주셔서 정말 기쁩니다.", STORE)

    def test_catches_emotion_report(self):
        found = find_violations("맛있게 드셨다니 기쁩니다.", STORE)
        assert any("기쁩니다" in v or "감정" in v for v in found)

    def test_catches_effort_cliche(self):
        assert find_violations("앞으로도 정성껏 노력하겠습니다.", STORE)

    def test_negative_only_phrase_not_flagged_in_positive(self):
        # "불편을 드려 죄송합니다" 는 부정 답변에서만 막는다
        text = "불편을 드려 죄송합니다. " + "가" * 120
        assert not any("불편" in v for v in find_violations(text, STORE))
        assert any("불편" in v for v in find_violations(text, STORE, negative=True))


class TestStoreNameOpening:
    def test_flags_store_name_in_first_sentence(self):
        found = find_violations(f"{STORE}입니다. 안녕하세요.", STORE)
        assert any("매장 이름" in v for v in found)

    def test_store_name_later_is_fine(self):
        found = find_violations(f"짬뽕 국물이 진했죠. {STORE}에서 계속 지키겠습니다.", STORE)
        assert not any("매장 이름" in v for v in found)


class TestLengthAndEmoji:
    def test_too_short(self):
        found = find_violations("짧다.", STORE, min_chars=100)
        assert any("이상" in v for v in found)

    def test_too_long(self):
        found = find_violations("가" * 300, STORE, max_chars=200)
        assert any("이하" in v for v in found)

    def test_emoji_limit(self):
        found = find_violations("좋아요 😊🍜🔥", STORE, max_emoji=1)
        assert any("이모지" in v for v in found)


class TestOpeningCollision:
    def test_same_greeting_with_different_wording_collides(self):
        assert openings_collide(
            "도야짬뽕 부천시청점에서 주문해 주셔서 진심으로 감사드립니다.",
            "도야짬뽕 부천시청점에서 주문해주셔서 정말 감사합니다.",
        )

    def test_different_openings_do_not_collide(self):
        assert not openings_collide(
            "해물짬뽕 국물, 오늘따라 잘 나왔습니다.",
            "탕수육은 튀김옷 상태가 관건이죠.",
        )

    def test_flagged_via_find_violations(self):
        found = find_violations(
            "짬뽕 국물이 진했죠. " + "가" * 120, STORE,
            avoid_openings=["짬뽕 국물이 진했죠."],
        )
        assert any("첫 문장" in v for v in found)


class TestOpeningShape:
    def test_detects_guest_action_frame(self):
        # 내용어만 바꾼 같은 골격을 잡아내는 것이 목적이다
        a = opening_shape("새우고추짬뽕을 선택하셨네요.")
        b = opening_shape("아침에 짬뽕을 드셨군요.")
        assert a and a == b

    def test_plain_statement_has_no_shape(self):
        assert opening_shape("짜장은 매일 볶아냅니다.") == ""

    def test_flagged_when_shape_repeats(self):
        found = find_violations(
            "탕수육을 시키셨네요. " + "가" * 120, STORE,
            avoid_shapes=[opening_shape("짬뽕을 드셨군요.")],
        )
        assert any("골격" in v for v in found)
