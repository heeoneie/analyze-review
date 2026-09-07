"""말투 프로필 — 사장님 표본에서 예시와 길이 기준을 뽑는 부분.

여기 나오는 리뷰·답글은 전부 지어낸 것이다. 실제 손님 리뷰는 저장소에
넣지 않는다 (CLAUDE.md).
"""

from core import reply_style
from core.reply_style import build_profile, prompt_block


def _sample(reply: str, review: str = "리뷰 본문", rating: int = 5) -> dict:
    return {"review": review, "rating": rating, "reply": reply}


class TestBuildProfile:
    def test_no_samples_gives_an_empty_profile(self):
        profile = build_profile([])

        assert not profile
        assert not profile.examples
        assert profile.min_chars is None

    def test_blank_replies_are_ignored(self):
        profile = build_profile([_sample("   "), _sample("")])

        assert not profile

    def test_length_window_comes_from_the_samples(self):
        profile = build_profile([_sample("가" * 40), _sample("가" * 60)])

        # 40*0.7 = 28, 60*1.4 = 84
        assert profile.min_chars == 28
        assert profile.max_chars == 84

    def test_one_sample_gives_examples_but_no_length_window(self):
        """한 건으로 폭을 정하면 우연히 길었던 답글 하나가 기준이 된다."""
        profile = build_profile([_sample("가" * 40)])

        assert profile.examples
        assert profile.min_chars is None
        assert profile.max_chars is None

    def test_window_never_goes_below_the_floor(self):
        """아주 짧은 답글만 있어도 답글 구실은 해야 한다."""
        profile = build_profile([_sample("네"), _sample("감사")])

        assert profile.min_chars == reply_style.FLOOR_CHARS

    def test_identical_lengths_still_leave_a_range(self):
        profile = build_profile([_sample("가" * 30), _sample("나" * 30)])

        assert profile.max_chars > profile.min_chars

    def test_examples_are_capped(self):
        profile = build_profile([_sample(f"답글 {i}") for i in range(20)])

        assert len(profile.examples) == reply_style.MAX_EXAMPLES_IN_PROMPT

    def test_order_is_preserved(self):
        """호출하는 쪽이 고쳐 쓴 답글을 앞에 놓는다. 그 순서를 흐트러뜨리면 안 된다."""
        profile = build_profile([_sample("첫째"), _sample("둘째"), _sample("셋째")])

        assert [e["reply"] for e in profile.examples] == ["첫째", "둘째", "셋째"]


class TestPromptBlock:
    def test_empty_profile_adds_nothing(self):
        assert prompt_block(build_profile([])) == ""

    def test_block_carries_the_replies(self):
        block = prompt_block(build_profile([
            _sample("감사합니다 또 오세요", review="맛있어요"),
            _sample("고맙습니다 다음에 또 뵈어요", review="좋아요"),
        ]))

        assert "감사합니다 또 오세요" in block
        assert "맛있어요" in block

    def test_block_tells_the_model_not_to_tidy_the_spelling(self):
        """사장님보다 반듯하게 고치면 사장님 말투가 아니게 된다."""
        block = prompt_block(build_profile([_sample("답글1"), _sample("답글2")]))

        assert "반듯하게 고치지 마라" in block

    def test_missing_review_body_does_not_break_the_block(self):
        """별점만 남긴 리뷰에 단 답글도 표본이 된다."""
        block = prompt_block(build_profile([
            _sample("감사합니다", review=""), _sample("고맙습니다", review=""),
        ]))

        assert "(리뷰 본문 없음)" in block


class TestCommonOpening:
    """인사말 습관. 예시만 보여 주면 모델이 자주 흘린다."""

    def test_majority_opening_is_picked_up(self):
        profile = build_profile([
            _sample("죄송합니다 고객님 다시 챙기겠습니다"),
            _sample("죄송합니다 고객님 바로 고치겠습니다"),
            _sample("소중한 시간을 뺏어 죄송해요"),
        ])

        assert profile.common_opening == "죄송합니다 고객님"

    def test_no_habit_when_openings_differ(self):
        profile = build_profile([
            _sample("감사합니다 또 오세요"),
            _sample("맛있게 드셨다니 다행이에요"),
            _sample("좋게 봐주셔서 고맙습니다"),
        ])

        assert profile.common_opening is None

    def test_habit_shows_up_in_the_prompt(self):
        block = prompt_block(build_profile([
            _sample("감사합니다 고객님 또 오세요"),
            _sample("감사합니다 고객님 좋은 하루 되세요"),
        ]))

        assert '"감사합니다 고객님" 로 시작한다' in block

    def test_one_word_habit_is_picked_up(self):
        """한 어절로 끝내는 사장님도 있다."""
        profile = build_profile([_sample("감사합니다"), _sample("감사합니다")])

        assert profile.common_opening == "감사합니다"

    def test_longer_prefix_wins_when_both_are_habits(self):
        """'감사합니다' 도 습관이지만 '감사합니다 고객님' 이 더 많은 것을 알려 준다."""
        profile = build_profile([
            _sample("감사합니다 고객님 또 오세요"),
            _sample("감사합니다 고객님 좋은 하루 되세요"),
        ])

        assert profile.common_opening == "감사합니다 고객님"

    def test_different_one_word_openings_are_not_a_habit(self):
        profile = build_profile([_sample("감사합니다"), _sample("고맙습니다")])

        assert profile.common_opening is None
