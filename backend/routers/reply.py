"""리뷰 답변 생성 API"""

import asyncio
import logging

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from core.reply_generator import ReplyGenerator

logger = logging.getLogger(__name__)
router = APIRouter()


class SingleReplyRequest(BaseModel):
    review_text: str = Field(min_length=1)
    rating: int = Field(ge=1, le=5)
    category: str | None = None


class BatchReplyItem(BaseModel):
    review_text: str = Field(min_length=1)
    rating: int = Field(ge=1, le=5)
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
