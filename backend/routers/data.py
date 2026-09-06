import logging
import os
import tempfile
from pathlib import Path

import pandas as pd
from fastapi import APIRouter, File, HTTPException, Query, UploadFile
from pydantic import BaseModel, Field

from backend.services.crawler_service import (
    crawl_reviews,
    save_reviews_to_csv,
)
from backend.services.priority_service import PriorityLevel, score_and_sort
from backend.services.rating import parse_rating

logger = logging.getLogger(__name__)
router = APIRouter()

# NOTE: 모듈 레벨 상태는 단일 워커에서만 공유됩니다.
# 다중 워커 배포 시 Redis 등 외부 저장소로 교체 필요.
uploaded_files = {}
analysis_settings = {"rating_threshold": 3}

PROJECT_ROOT = str(Path(__file__).resolve().parents[2])


def _validate_ratings_column(df: pd.DataFrame) -> None:
    """Ratings 컬럼이 숫자 별점으로 읽히는지 업로드 시점에 확인한다.

    한 행도 숫자로 읽히지 않으면(예: ``Ratings = "5 out of 5"``) 업로드를
    거부한다. 그러지 않으면 업로드는 성공하고 조회 시점에야 빈 결과나
    엉뚱한 기본 별점으로 드러난다.
    """
    values = df["Ratings"].tolist()
    if not values:
        return
    if any(parse_rating(v) is not None for v in values):
        return

    sample = next(
        (repr(v) for v in values if str(v).strip()),
        "(빈 값)",
    )
    raise HTTPException(
        400,
        "'Ratings' 컬럼에서 숫자 별점을 읽을 수 없습니다. "
        f"1~5 사이의 숫자여야 합니다. (예시 값: {sample})",
    )


class CrawlRequest(BaseModel):
    url: str
    max_pages: int = 50


class SettingsRequest(BaseModel):
    rating_threshold: int = Field(3, ge=1, le=5)


@router.post("/upload")
async def upload_csv(file: UploadFile = File(...)):
    if not file.filename or not file.filename.endswith(".csv"):
        raise HTTPException(
            400, "CSV 파일만 업로드 가능합니다."
        )

    content = await file.read()
    with tempfile.NamedTemporaryFile(
        delete=False, suffix=".csv"
    ) as tmp:
        tmp.write(content)
        tmp_path = tmp.name

    try:
        df = pd.read_csv(tmp_path)
    except Exception as exc:
        os.unlink(tmp_path)
        raise HTTPException(
            400, "CSV 파일을 파싱할 수 없습니다."
        ) from exc

    # Ratings/Reviews 또는 rating/review_text 컬럼 확인
    has_custom = (
        "Ratings" in df.columns and "Reviews" in df.columns
    )
    has_eval = (
        "review_text" in df.columns and "rating" in df.columns
    )

    if not has_custom and not has_eval:
        os.unlink(tmp_path)
        raise HTTPException(
            400,
            "CSV에 'Ratings'/'Reviews' 또는 "
            "'rating'/'review_text' 컬럼이 필요합니다.",
        )

    # evaluation_dataset 형식이면 Ratings/Reviews로 변환
    if has_eval and not has_custom:
        df = df.rename(
            columns={"review_text": "Reviews", "rating": "Ratings"}
        )
        df[["Ratings", "Reviews"]].to_csv(tmp_path, index=False)

    try:
        _validate_ratings_column(df)
    except HTTPException:
        os.unlink(tmp_path)
        raise

    uploaded_files["current"] = tmp_path

    preview = df.head(5).fillna("").to_dict(orient="records")
    return {
        "filename": file.filename,
        "total_rows": len(df),
        "preview": preview,
    }


@router.post("/crawl")
async def crawl_product_reviews(request: CrawlRequest):
    """상품 URL에서 리뷰 크롤링"""
    try:
        platform, result = await crawl_reviews(
            request.url, request.max_pages
        )

        reviews = result["reviews"]
        total_count = result["total_count"]

        if total_count == 0:
            raise HTTPException(
                400,
                "리뷰를 찾을 수 없습니다. URL을 확인해주세요.",
            )

        # 텍스트 리뷰를 CSV로 저장 (분석용)
        if reviews:
            csv_path = save_reviews_to_csv(reviews)
            uploaded_files["current"] = csv_path
        else:
            uploaded_files.pop("current", None)

        return {
            "platform": platform,
            "total_reviews": total_count,
            "text_reviews": len(reviews),
            "rating_average": result["rating_average"],
            "rating_distribution": {
                str(k): v
                for k, v in result[
                    "rating_distribution"
                ].items()
            },
            "preview": reviews[:5],
        }
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
    except HTTPException:
        raise
    except Exception:
        logger.exception("크롤링 중 오류 발생")
        raise HTTPException(
            500, "크롤링 중 오류가 발생했습니다."
        ) from None


@router.post("/settings")
def update_settings(request: SettingsRequest):
    """분석 설정 업데이트 (별점 기준 등)"""
    analysis_settings["rating_threshold"] = (
        request.rating_threshold
    )
    return {
        "rating_threshold": analysis_settings["rating_threshold"]
    }


@router.get("/settings")
def get_settings():
    """현재 분석 설정 조회"""
    return analysis_settings


@router.get("/reviews")
def get_reviews(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
):
    """수집된 리뷰 목록 조회 (페이지네이션)"""
    csv_path = uploaded_files.get("current")
    if not csv_path or not os.path.exists(csv_path):
        raise HTTPException(
            400,
            "먼저 CSV 파일을 업로드하거나 크롤링해주세요.",
        )

    df = pd.read_csv(csv_path).fillna("")
    total = len(df)

    # 페이지네이션
    start = (page - 1) * page_size
    end = start + page_size
    reviews = df.iloc[start:end].to_dict(orient="records")

    return {
        "reviews": reviews,
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": (total + page_size - 1) // page_size,
    }


@router.get("/reviews/prioritized")
def get_prioritized_reviews(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    level: PriorityLevel = Query(None, description="critical/high/medium/low"),
):
    """우선순위 정렬된 부정 리뷰 목록"""
    csv_path = uploaded_files.get("current")
    if not csv_path or not os.path.exists(csv_path):
        raise HTTPException(
            400,
            "먼저 CSV 파일을 업로드하거나 크롤링해주세요.",
        )

    df = pd.read_csv(csv_path).fillna("")
    threshold = analysis_settings["rating_threshold"]

    # 부정 리뷰만 필터링 (별점 파싱은 parse_rating 한 곳으로)
    def _is_negative(x):
        rating = parse_rating(x)
        return rating is not None and rating <= threshold

    negative_df = df[df["Ratings"].apply(_is_negative)]
    reviews = negative_df.to_dict(orient="records")

    # 우선순위 스코어링 및 정렬
    scored = score_and_sort(reviews)

    # 레벨 필터링
    if level:
        scored = [r for r in scored if r["priority"]["level"] == level.value]

    total = len(scored)
    start = (page - 1) * page_size
    end = start + page_size

    return {
        "reviews": scored[start:end],
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": (total + page_size - 1) // page_size,
    }
