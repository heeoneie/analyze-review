"""리뷰 답변 생성 및 가이드 API

/generate, /generate-batch 는 대시보드(ReplyPanel)가 쓰는 기존 경로다.
/guide, /guides 는 카테고리별 답변 품질 가이드다.
/store/* 는 사장님이 리뷰를 붙여넣고 쓰는 단독 화면용이고, 접속 코드로 잠근다.
"""

import asyncio
import logging
import secrets

from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel, Field

from core import config
from core.reply_generator import ReplyGenerator
from core.reply_guide import get_guide, list_guides

logger = logging.getLogger(__name__)
router = APIRouter()


class GuideRequest(BaseModel):
    category: str


def require_access_code(x_access_code: str = Header(default="")):
    """ACCESS_CODE 가 설정돼 있으면 헤더로 같은 코드를 받아야 통과.

    compare_digest 는 비ASCII 문자열을 그대로 받으면 TypeError 를 낸다.
    한국어 코드("도야2026")를 넣으면 모든 요청이 500 이 되므로 bytes 로 비교한다.
    """
    if not config.ACCESS_CODE:
        return
    if not secrets.compare_digest(
        x_access_code.encode("utf-8"), config.ACCESS_CODE.encode("utf-8")
    ):
        raise HTTPException(401, "접속 코드가 맞지 않습니다.")


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


@router.post("/generate", dependencies=[Depends(require_access_code)])
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


@router.post("/generate-batch", dependencies=[Depends(require_access_code)])
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


# ── 사장님용 단독 화면 ──────────────────────────────────────


class StoreReplyRequest(BaseModel):
    review_text: str = Field(default="", max_length=2000)
    rating: int = Field(ge=1, le=5)
    menu: str = Field(default="", max_length=500)
    store_name: str | None = Field(default=None, max_length=100)
    # "다시 만들기" 시 직전 답변과 겹치지 않게 프론트에서 되돌려 보낸다.
    avoid_openings: list[str] = Field(default_factory=list, max_length=10)
    avoid_closings: list[str] = Field(default_factory=list, max_length=10)
    exclude_angles: list[str] = Field(default_factory=list, max_length=10)
    exclude_closings: list[str] = Field(default_factory=list, max_length=10)


@router.get("/config")
async def reply_config():
    """화면이 기본값을 채우는 데 쓰는 설정. 코드 없이도 볼 수 있어야 한다."""
    return {
        "store_name": config.STORE_NAME,
        "model": config.REPLY_LLM_MODEL,
        "requires_code": bool(config.ACCESS_CODE),
    }


@router.post("/verify", dependencies=[Depends(require_access_code)])
async def verify_access_code():
    """접속 코드 확인. 화면 진입 시 한 번 호출한다."""
    return {"ok": True}


@router.post("/store/generate", dependencies=[Depends(require_access_code)])
async def generate_store_reply(request: StoreReplyRequest):
    """리뷰 한 건에 대한 답글 생성. 별점에 따라 긍정/부정 경로로 나뉜다."""
    if not request.review_text.strip() and not request.menu.strip():
        raise HTTPException(400, "리뷰 내용이나 주문 메뉴 중 하나는 입력해 주세요.")

    generator = ReplyGenerator(store_name=request.store_name)
    try:
        result = await asyncio.to_thread(
            generator.generate,
            request.review_text,
            request.rating,
            request.menu,
            avoid_openings=request.avoid_openings,
            avoid_closings=request.avoid_closings,
            exclude_angles=request.exclude_angles,
            exclude_closings=request.exclude_closings,
        )
    except Exception:
        logger.exception("답변 생성 실패")
        raise HTTPException(500, "답변을 만들지 못했습니다. 잠시 후 다시 시도해 주세요.") from None

    return result
