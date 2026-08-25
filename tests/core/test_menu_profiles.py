"""menu_profiles 테스트 (LLM 호출 없음)"""

from core.menu_profiles import (
    format_menu_block,
    main_items,
    parse_menu,
    unordered_mentions,
)


class TestParseMenu:
    def test_splits_on_pipe(self):
        items = parse_menu("해물짬뽕 | 도야짜장면")
        assert [i["name"] for i in items] == ["해물짬뽕", "도야짜장면"]

    def test_strips_review_event_suffix(self):
        # 리뷰 이벤트 서비스 품목에는 안내 문구가 그대로 따라온다
        items = parse_menu("군만두3P 찜과ZI뷰항상감사드립니다")
        assert items[0]["name"] == "군만두3P"
        assert items[0]["is_service"] is True

    def test_normal_item_is_not_service(self):
        assert parse_menu("탕수육")[0]["is_service"] is False

    def test_set_menu_collects_every_axis(self):
        # "짜장+짬뽕+미니탕수육" 은 한 품목이지만 구성 음식의 축을 모두 모은다
        axis = parse_menu("짜장+짬뽕+미니탕수육")[0]["axis"]
        assert "춘장향" in axis
        assert "매콤" in axis
        assert "바삭" in axis

    def test_specific_name_wins_over_generic(self):
        # "해물짬뽕" 이 "짬뽕" 보다 먼저 매칭돼야 한다
        assert "해물" in parse_menu("해물짬뽕")[0]["axis"]

    def test_deduplicates(self):
        assert len(parse_menu("탕수육 | 탕수육")) == 1

    def test_empty_input(self):
        assert parse_menu("") == []
        assert parse_menu(None) == []


class TestMainItems:
    def test_excludes_service_items(self):
        items = parse_menu("해물짬뽕 | 군만두3P 찜과ZI뷰항상감사드립니다")
        assert [i["name"] for i in main_items(items)] == ["해물짬뽕"]

    def test_falls_back_when_everything_is_service(self):
        items = parse_menu("군만두3P 찜과ZI뷰항상감사드립니다")
        assert len(main_items(items)) == 1


class TestFormatMenuBlock:
    def test_marks_service_item(self):
        block = format_menu_block(parse_menu("군만두3P 찜과ZI뷰항상감사드립니다"))
        assert "리뷰 이벤트 서비스 품목" in block

    def test_warns_against_copying_keywords(self):
        # 완성된 문장을 주면 모델이 그대로 베껴 쓴다
        assert "그대로 옮겨 적지 말고" in format_menu_block(parse_menu("탕수육"))

    def test_handles_no_menu(self):
        assert "주문 메뉴 정보 없음" in format_menu_block([])


class TestUnorderedMentions:
    def test_flags_dish_not_ordered(self):
        found = unordered_mentions("바삭한 군만두도 함께하셨네요.", "짬뽕+미니탕수육")
        assert "군만두" in found

    def test_allows_suggestion_context(self):
        found = unordered_mentions("다음에는 군만두도 드셔 보세요.", "짬뽕+미니탕수육")
        assert found == []

    def test_ordered_dish_is_fine(self):
        assert unordered_mentions("탕수육 튀김옷이 바삭했습니다.", "탕수육") == []

    def test_service_item_counts_as_ordered(self):
        # 리뷰 이벤트로 받은 군만두도 손님이 실제로 받은 것이다
        found = unordered_mentions(
            "군만두 바삭했지요.", "탕수육 | 군만두3P 찜과ZI뷰항상감사드립니다"
        )
        assert found == []

    def test_no_menu_means_no_check(self):
        assert unordered_mentions("군만두 좋았죠.", "") == []
