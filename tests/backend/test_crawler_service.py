from backend.services.crawler_service import (
    detect_platform,
    _extract_product_id,
    extract_reviews_from_markdown,
)


class TestDetectPlatform:
    def test_coupang_url(self):
        assert detect_platform("https://www.coupang.com/vp/products/123456") == "coupang"

    def test_naver_smartstore_url(self):
        assert detect_platform("https://smartstore.naver.com/shop/products/123") == "naver"

    def test_naver_shopping_url(self):
        assert detect_platform("https://shopping.naver.com/product/123") == "naver"

    def test_unknown_url(self):
        assert detect_platform("https://www.amazon.com/product/123") == "unknown"

    def test_coupang_mobile_url(self):
        assert detect_platform("https://m.coupang.com/vm/products/789") == "coupang"


class TestExtractProductId:
    def test_valid_coupang_url(self):
        assert _extract_product_id("https://www.coupang.com/vp/products/7893106168") == "7893106168"

    def test_no_product_id(self):
        assert _extract_product_id("https://www.coupang.com/categories/food") is None

    def test_url_with_query_params(self):
        url = "https://www.coupang.com/vp/products/12345?itemId=67890"
        assert _extract_product_id(url) == "12345"


class TestExtractReviewsFromMarkdown:
    def test_naver_reviews_with_star_rating(self):
        # 스킵 워드('구매' 등) 없는 리뷰 텍스트 사용
        md = "별점 5\n이 제품은 정말 좋습니다. 배송도 빠르고 품질도 훌륭해요.\n별점 1\n별로예요 품질이 너무 안좋네요 다시는 주문하지 않겠습니다."
        result = extract_reviews_from_markdown(md, "naver")
        assert len(result) == 2
        assert result[0]["Ratings"] == 5
        assert result[1]["Ratings"] == 1

    def test_naver_skips_short_lines(self):
        md = "별점 3\n짧은텍스트\n이 제품은 가격 대비 괜찮은 것 같습니다. 배송은 보통이었어요."
        result = extract_reviews_from_markdown(md, "naver")
        assert len(result) == 1  # 15자 미만은 제외

    def test_naver_skips_keyword_lines(self):
        md = "별점 4\n작성일자 2024년 1월 15일 구매확인 리뷰\n이 제품 정말 좋네요. 가격 대비 성능이 매우 뛰어나다고 생각합니다."
        result = extract_reviews_from_markdown(md, "naver")
        assert len(result) == 1  # '작성' 포함 라인 제외

    def test_non_naver_platform_returns_empty(self):
        md = "별점 5\n이 제품은 정말 좋습니다. 배송도 빠르고 품질도 훌륭해요."
        result = extract_reviews_from_markdown(md, "coupang")
        assert result == []

    def test_empty_markdown(self):
        result = extract_reviews_from_markdown("", "naver")
        assert result == []

    def test_naver_점_rating_format(self):
        md = "4점\n이 제품은 전체적으로 괜찮았습니다. 가성비가 좋다고 생각해요."
        result = extract_reviews_from_markdown(md, "naver")
        assert len(result) == 1
        assert result[0]["Ratings"] == 4
