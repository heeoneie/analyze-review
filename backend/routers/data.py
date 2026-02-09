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

logger = logging.getLogger(__name__)
router = APIRouter()

# NOTE: 모듈 레벨 상태는 단일 워커에서만 공유됩니다.
# 다중 워커 배포 시 Redis 등 외부 저장소로 교체 필요.
uploaded_files = {}
analysis_settings = {"rating_threshold": 3}

AI_DIR = str(Path(__file__).resolve().parents[2] / "ai")


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

    uploaded_files["current"] = tmp_path

    preview = df.head(5).fillna("").to_dict(orient="records")
    return {
        "filename": file.filename,
        "total_rows": len(df),
        "preview": preview,
    }


@router.get("/sample")
def use_sample_data():
    sample_path = os.path.join(
        AI_DIR, "evaluation", "evaluation_dataset.csv"
    )

    if not os.path.exists(sample_path):
        raise HTTPException(404, "샘플 데이터를 찾을 수 없습니다.")

    # 컬럼명 변환하여 임시 파일로 저장
    try:
        df = pd.read_csv(sample_path)
    except Exception as exc:
        logger.exception("샘플 데이터 파싱 실패")
        raise HTTPException(
            500, "샘플 데이터를 파싱할 수 없습니다."
        ) from exc

    df = df.rename(
        columns={"review_text": "Reviews", "rating": "Ratings"}
    )

    with tempfile.NamedTemporaryFile(
        delete=False, suffix=".csv", mode="w"
    ) as tmp:
        tmp_path = tmp.name

    df[["Ratings", "Reviews"]].to_csv(tmp_path, index=False)

    uploaded_files["current"] = tmp_path

    return {
        "filename": "evaluation_dataset.csv (sample)",
        "total_rows": len(df),
    }


@router.post("/crawl")
async def crawl_product_reviews(request: CrawlRequest):
    """상품 URL에서 리뷰 크롤링"""
    try:
        platform, reviews = await crawl_reviews(
            request.url, request.max_pages
        )

        if not reviews:
            raise HTTPException(
                400,
                "리뷰를 찾을 수 없습니다. URL을 확인해주세요.",
            )

        # CSV로 저장
        csv_path = save_reviews_to_csv(reviews)
        uploaded_files["current"] = csv_path

        # 별점 분포 계산
        df = pd.DataFrame(reviews)
        rating_dist = (
            df["Ratings"].value_counts().sort_index().to_dict()
        )

        return {
            "platform": platform,
            "total_reviews": len(reviews),
            "rating_distribution": {
                str(k): v for k, v in rating_dist.items()
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
