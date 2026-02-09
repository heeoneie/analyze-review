import json
import os
import re
import tempfile
import time
from urllib.parse import urlparse

import pandas as pd
from curl_cffi import requests as cffi_requests
from dotenv import load_dotenv

load_dotenv()

FIRECRAWL_API_KEY = os.getenv("FIRECRAWL_API_KEY")


def _extract_product_id(url: str) -> str | None:
    """쿠팡 상품 URL에서 productId 추출"""
    match = re.search(r'/products/(\d+)', url)
    return match.group(1) if match else None


_IMPERSONATE_OPTIONS = ["safari", "safari15_5", "chrome120", "chrome"]


def _crawl_coupang(product_id: str, max_pages: int) -> list[dict]:
    """curl_cffi로 쿠팡 리뷰 API 직접 호출 (브라우저 TLS 핑거프린트로 Akamai 우회)"""
    # 여러 브라우저 핑거프린트를 순서대로 시도
    for impersonate in _IMPERSONATE_OPTIONS:
        session = cffi_requests.Session(impersonate=impersonate)
        session.get(
            f"https://www.coupang.com/vp/products/{product_id}",
            headers={"Accept": "text/html", "Accept-Language": "ko-KR,ko;q=0.9"},
        )
        test_resp = session.get(
            f"https://www.coupang.com/next-api/review?productId={product_id}&page=1&size=1&sortBy=DATE_DESC&ratingSummary=true",
            headers={
                "Accept": "application/json, text/plain, */*",
                "Referer": f"https://www.coupang.com/vp/products/{product_id}",
            },
        )
        if test_resp.status_code == 200:
            break
    else:
        return []

    all_reviews = []
    size = 20
    consecutive_failures = 0

    for page_num in range(1, max_pages + 1):
        api_url = (
            f"https://www.coupang.com/next-api/review"
            f"?productId={product_id}&page={page_num}&size={size}"
            f"&sortBy=DATE_DESC&ratingSummary=true"
        )

        try:
            resp = session.get(
                api_url,
                headers={
                    "Accept": "application/json, text/plain, */*",
                    "Accept-Language": "ko-KR,ko;q=0.9",
                    "Referer": f"https://www.coupang.com/vp/products/{product_id}",
                },
            )
            resp.raise_for_status()
            data = json.loads(resp.text)
        except Exception:
            consecutive_failures += 1
            if consecutive_failures >= 3:
                break
            time.sleep(0.5)
            continue

        paging = data.get("rData", {}).get("paging", {})
        contents = paging.get("contents", [])

        if not contents:
            break

        for item in contents:
            rating = item.get("rating", 5)
            title = item.get("title", "")
            content = item.get("content", "")
            text = f"{title}\n{content}".strip() if title else content.strip()
            if text:
                all_reviews.append({"Ratings": rating, "Reviews": text})

        consecutive_failures = 0

        if not paging.get("isNext", False):
            break

        if page_num < max_pages:
            time.sleep(0.2)

    return all_reviews


# ──────────────────────────────────────────────
# 네이버용 Firecrawl 폴백
# ──────────────────────────────────────────────

def extract_reviews_from_markdown(markdown: str, platform: str) -> list[dict]:
    """마크다운에서 리뷰 데이터 추출 (네이버용)"""
    reviews = []
    if platform == "naver":
        lines = markdown.split('\n')
        current_rating = 5

        for line in lines:
            line = line.strip()
            if not line:
                continue

            rating_match = re.search(r'별점\s*(\d)', line) or re.search(r'(\d)점', line)
            if rating_match:
                current_rating = int(rating_match.group(1))
                continue

            if len(line) >= 15 and re.search(r'[가-힣]', line):
                if not any(skip in line for skip in ['작성', '구매', '옵션', '판매자', '신고']):
                    reviews.append({
                        "Ratings": current_rating,
                        "Reviews": line
                    })

    return reviews


async def crawl_with_firecrawl(url: str, max_pages: int = 5) -> tuple[str, list[dict]]:
    """Firecrawl을 사용한 리뷰 크롤링 (네이버 등)"""
    if not FIRECRAWL_API_KEY:
        raise ValueError("FIRECRAWL_API_KEY가 설정되지 않았습니다. .env 파일을 확인해주세요.")

    from firecrawl import FirecrawlApp

    platform = detect_platform(url)
    app = FirecrawlApp(api_key=FIRECRAWL_API_KEY)

    result = app.scrape(url, formats=['markdown'], wait_for=3000)
    markdown = result.markdown or ''
    if not markdown:
        raise ValueError("페이지 내용을 가져올 수 없습니다.")
    reviews = extract_reviews_from_markdown(markdown, platform)

    return platform, reviews


# ──────────────────────────────────────────────
# 공통
# ──────────────────────────────────────────────

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


async def crawl_reviews(url: str, max_pages: int = 50) -> tuple[str, list[dict]]:
    """리뷰 크롤링 (쿠팡: curl_cffi, 네이버: Firecrawl)"""
    platform = detect_platform(url)

    if platform == "unknown":
        raise ValueError(f"지원하지 않는 플랫폼입니다: {url}")

    if platform == "coupang":
        product_id = _extract_product_id(url)
        if not product_id:
            raise ValueError("쿠팡 상품 URL에서 productId를 추출할 수 없습니다.")
        reviews = _crawl_coupang(product_id, max_pages)
    else:
        _, reviews = await crawl_with_firecrawl(url, max_pages)

    return platform, reviews


def save_reviews_to_csv(reviews: list[dict]) -> str:
    """리뷰를 CSV 파일로 저장"""
    df = pd.DataFrame(reviews)
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".csv")
    df.to_csv(tmp.name, index=False)
    tmp.close()
    return tmp.name
