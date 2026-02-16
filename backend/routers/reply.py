"""리뷰 답변 생성 및 가이드 API"""

import asyncio
import logging

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from core.reply_generator import ReplyGenerator
from core.reply_guide import get_guide, list_guides

logger = logging.getLogger(__name__)
router = APIRouter()


class GuideRequest(BaseModel):
    category: str


class SingleReplyRequest(BaseModel):
    review_text: str
    rating: int
    category: str | None = None


class BatchReplyItem(BaseModel):
    review_text: str
    rating: int
    category: str | None = None


class BatchReplyRequest(BaseModel):
    reviews: list[BatchReplyItem]


@router.post("/generate")
async def generate_reply(request: SingleReplyRequest):
    """단일 리뷰에 대한 맞춤 답변 생성"""
    try:
        generator = ReplyGenerator()
        result = await asyncio.to_thread(
            generator.generate_single,
            request.review_text,
            request.rating,
            request.category,
        )
        return result
    except Exception:
        logger.exception("답변 생성 실패")
        raise HTTPException(500, "답변 생성 중 오류가 발생했습니다.") from None


@router.post("/generate-batch")
async def generate_batch_replies(request: BatchReplyRequest):
    """다건 리뷰에 대한 답변 일괄 생성"""
    if len(request.reviews) > 50:
        raise HTTPException(400, "최대 50건까지 일괄 생성 가능합니다.")

    try:
        generator = ReplyGenerator()
        reviews_dicts = [r.model_dump() for r in request.reviews]
        results = await asyncio.to_thread(
            generator.generate_batch, reviews_dicts
        )
        return {"replies": results}
    except Exception:
        logger.exception("일괄 답변 생성 실패")
        raise HTTPException(500, "일괄 답변 생성 중 오류가 발생했습니다.") from None


@router.post("/guide")
async def get_reply_guide(request: GuideRequest):
    """카테고리별 답변 품질 가이드 조회"""
    try:
        guide = await asyncio.to_thread(get_guide, request.category)
    except Exception:
        logger.exception("가이드 조회 실패: %s", request.category)
        raise HTTPException(500, "가이드 조회 중 오류가 발생했습니다.") from None
    return guide


@router.get("/guides")
async def get_all_guides():
    """등록된 전체 가이드 목록"""
    return {"guides": list_guides()}
