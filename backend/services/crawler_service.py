import re
import tempfile
import asyncio
from urllib.parse import urlparse

import pandas as pd
from playwright.async_api import async_playwright


async def crawl_coupang(url: str, max_pages: int = 5) -> list[dict]:
    """쿠팡 상품 리뷰 크롤링"""
    reviews = []

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()

        # 상품 페이지 접속
        await page.goto(url, wait_until="networkidle", timeout=30000)
        await page.wait_for_timeout(2000)

        # 리뷰 탭 클릭 (있으면)
        try:
            review_tab = page.locator("a:has-text('상품평')")
            if await review_tab.count() > 0:
                await review_tab.first.click()
                await page.wait_for_timeout(2000)
        except Exception:
            pass

        for page_num in range(max_pages):
            # 리뷰 요소 수집
            review_items = page.locator("article.sdp-review__article__list")
            count = await review_items.count()

            for i in range(count):
                try:
                    item = review_items.nth(i)

                    # 별점
                    rating_el = item.locator("div.sdp-review__article__list__info__product-info__star-orange")
                    rating_style = await rating_el.get_attribute("style") if await rating_el.count() > 0 else ""
                    rating_match = re.search(r"width:\s*(\d+)%", rating_style or "")
                    rating = int(int(rating_match.group(1)) / 20) if rating_match else 5

                    # 리뷰 텍스트
                    text_el = item.locator("div.sdp-review__article__list__review__content")
                    review_text = await text_el.inner_text() if await text_el.count() > 0 else ""

                    if review_text.strip():
                        reviews.append({"Ratings": rating, "Reviews": review_text.strip()})

                except Exception:
                    continue

            # 다음 페이지
            try:
                next_btn = page.locator("button.sdp-review__article__page__next")
                if await next_btn.count() > 0 and await next_btn.is_enabled():
                    await next_btn.click()
                    await page.wait_for_timeout(2000)
                else:
                    break
            except Exception:
                break

        await browser.close()

    return reviews


async def crawl_naver(url: str, max_pages: int = 5) -> list[dict]:
    """네이버 스마트스토어 리뷰 크롤링"""
    reviews = []

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()

        await page.goto(url, wait_until="networkidle", timeout=30000)
        await page.wait_for_timeout(2000)

        # 리뷰 탭 클릭
        try:
            review_tab = page.locator("a:has-text('리뷰')")
            if await review_tab.count() > 0:
                await review_tab.first.click()
                await page.wait_for_timeout(2000)
        except Exception:
            pass

        for page_num in range(max_pages):
            # 리뷰 요소 수집
            review_items = page.locator("li.BnwL_cs1av")
            count = await review_items.count()

            for i in range(count):
                try:
                    item = review_items.nth(i)

                    # 별점
                    rating_el = item.locator("em.K23LVofo0z")
                    rating_text = await rating_el.inner_text() if await rating_el.count() > 0 else "5"
                    rating = int(rating_text) if rating_text.isdigit() else 5

                    # 리뷰 텍스트
                    text_el = item.locator("span._1LIgGDVTt_")
                    review_text = await text_el.inner_text() if await text_el.count() > 0 else ""

                    if review_text.strip():
                        reviews.append({"Ratings": rating, "Reviews": review_text.strip()})

                except Exception:
                    continue

            # 다음 페이지
            try:
                next_btn = page.locator("a.fAUKm1ewwo._2Ar8-aEUTq:has-text('다음')")
                if await next_btn.count() > 0:
                    await next_btn.click()
                    await page.wait_for_timeout(2000)
                else:
                    break
            except Exception:
                break

        await browser.close()

    return reviews


def detect_platform(url: str) -> str:
    """URL로 플랫폼 감지"""
    parsed = urlparse(url)
    domain = parsed.netloc.lower()

    if "coupang" in domain:
        return "coupang"
    elif "naver" in domain or "smartstore" in domain:
        return "naver"
    else:
        return "unknown"


async def crawl_reviews(url: str, max_pages: int = 5) -> tuple[str, list[dict]]:
    """URL에 맞는 크롤러 실행"""
    platform = detect_platform(url)

    if platform == "coupang":
        reviews = await crawl_coupang(url, max_pages)
    elif platform == "naver":
        reviews = await crawl_naver(url, max_pages)
    else:
        raise ValueError(f"지원하지 않는 플랫폼입니다: {url}")

    return platform, reviews


def save_reviews_to_csv(reviews: list[dict]) -> str:
    """리뷰를 CSV 파일로 저장"""
    df = pd.DataFrame(reviews)
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".csv")
    df.to_csv(tmp.name, index=False)
    tmp.close()
    return tmp.name
