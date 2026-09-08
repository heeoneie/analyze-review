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
from sqlalchemy.orm import Session

from backend.database.database import get_db
from backend.database.models import ReplySample, Review, Store
from backend.dependencies import store_or_access_code
from backend.services import reply_history
from core import config, reply_style
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
    # 대시보드에서 수집한 리뷰에 다는 경우 그 리뷰 id. 붙여넣기 화면은 비운다.
    # 이 값이 있어야 목록이 "이 리뷰엔 답글이 있다" 를 알 수 있다.
    review_id: int | None = None


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


@router.post("/store/generate")
async def generate_store_reply(
    request: StoreReplyRequest,
    store: Store | None = Depends(store_or_access_code),
    db: Session = Depends(get_db),
):
    """리뷰 한 건에 대한 답글 생성. 별점에 따라 긍정/부정 경로로 나뉜다.

    매장이 연결돼 있으면 생성 결과를 남기고 `sample_id` 를 함께 돌려준다.
    사장님이 실제로 게시하면 프론트가 그 id 로 /store/finalize 를 부른다.
    게시하지 않은 답글은 채택 근거가 없으므로 말투 학습에 쓰지 않는다.
    """
    if not request.review_text.strip() and not request.menu.strip():
        raise HTTPException(400, "리뷰 내용이나 주문 메뉴 중 하나는 입력해 주세요.")

    # 소유권은 LLM 을 부르기 **전에** 본다. 뒤에서 확인하면 남의 매장 리뷰
    # id 로 요청이 와도 답글을 만들어 버려 요금이 나간다.
    linked_review = None
    if request.review_id is not None and store is not None:
        linked_review = db.get(Review, request.review_id)
        if linked_review is None or linked_review.store_id != store.id:
            raise HTTPException(404, "리뷰를 찾을 수 없습니다.")

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
            style=reply_history.style_profile_for(db, store, request.rating),
        )
    except Exception:
        logger.exception("답변 생성 실패")
        raise HTTPException(500, "답변을 만들지 못했습니다. 잠시 후 다시 시도해 주세요.") from None

    if store is not None:
        sample = reply_history.record_generated(
            db, store_id=store.id,
            review_body=request.review_text, rating=request.rating,
            menu=request.menu, generated_reply=result.get("reply", ""),
        )
        if linked_review is not None:
            sample.review_id = linked_review.id
            db.commit()
        result = {**result, "sample_id": sample.id}

    return result


class FinalizeRequest(BaseModel):
    sample_id: int
    # 사장님이 실제로 게시한 문장. 생성본을 고쳤다면 고친 그대로.
    final_reply: str = Field(min_length=1, max_length=4000)


@router.post("/store/finalize")
def finalize_store_reply(
    body: FinalizeRequest,
    store: Store | None = Depends(store_or_access_code),
    db: Session = Depends(get_db),
):
    """사장님이 게시한 답글을 확정 기록한다. 말투 학습은 이 행만 쓴다."""
    if store is None:
        # 접속코드 경로에는 매장이 없어 남길 곳이 없다. 화면은 그대로 동작한다.
        return {"recorded": False}

    sample = db.get(ReplySample, body.sample_id)
    # 남의 매장 표본을 고치지 못하게 소유권을 확인한다.
    if sample is None or sample.store_id != store.id:
        raise HTTPException(404, "기록을 찾을 수 없습니다.")

    reply_history.finalize(db, sample, body.final_reply)
    return {"recorded": True, "was_edited": sample.was_edited}


# ── 말투 온보딩 ─────────────────────────────────────────────
# 말투 학습은 사장님이 게시한 답글이 있어야 걸린다. 갓 가입한 사장님은
# 표본이 0건이라 아무 효과가 없다 — 답글을 몇 번 달아야 비로소 시작된다.
# 가입 직후에 직접 써 넣게 해서 그 공백을 메운다.

class OnboardingSample(BaseModel):
    review_text: str = Field(min_length=1, max_length=2000)
    rating: int = Field(ge=1, le=5)
    reply: str = Field(min_length=1, max_length=4000)


class OnboardingRequest(BaseModel):
    samples: list[OnboardingSample] = Field(min_length=1, max_length=20)


@router.get("/style/status")
def style_status(
    store: Store | None = Depends(store_or_access_code),
    db: Session = Depends(get_db),
):
    """이 매장이 말투 표본을 몇 건 갖고 있는지.

    화면이 온보딩을 띄울지 정하는 데 쓴다. 긍정·부정을 따로 세는 이유는
    한쪽만 쌓여 있으면 그 성향에서만 말투가 걸리기 때문이다.
    """
    if store is None:
        # 접속코드 경로에는 매장이 없어 표본을 담을 곳이 없다.
        return {
            "store": False, "positive": 0, "negative": 0, "learning": False,
            "needed": reply_style.MIN_SAMPLES_FOR_LENGTH,
            "positive_from": config.POSITIVE_RATING_THRESHOLD,
        }

    positive = len(reply_history.style_examples(
        db, store.id, limit=reply_history.STYLE_POOL_SIZE, positive=True))
    negative = len(reply_history.style_examples(
        db, store.id, limit=reply_history.STYLE_POOL_SIZE, positive=False))

    return {
        "store": True,
        "positive": positive,
        "negative": negative,
        # 한쪽이라도 기준을 채우면 그 성향에서는 말투가 걸린다.
        "learning": max(positive, negative) >= reply_style.MIN_SAMPLES_FOR_LENGTH,
        "needed": reply_style.MIN_SAMPLES_FOR_LENGTH,
        # 화면이 긍정·부정을 같은 기준으로 갈라야 한다. 여기서 내보내지
        # 않으면 프론트가 4를 따로 들고 있게 되고, 서버 값이 바뀌는 날
        # 화면만 조용히 어긋난 안내를 한다.
        "positive_from": config.POSITIVE_RATING_THRESHOLD,
    }


@router.post("/style/onboarding")
def add_onboarding_samples(
    body: OnboardingRequest,
    store: Store | None = Depends(store_or_access_code),
    db: Session = Depends(get_db),
):
    """사장님이 직접 써 넣은 답글을 말투 표본으로 담는다."""
    if store is None:
        raise HTTPException(409, "연결된 매장이 없습니다.")

    for sample in body.samples:
        reply_history.record_onboarding(
            db,
            store_id=store.id,
            review_body=sample.review_text,
            rating=sample.rating,
            owner_reply=sample.reply,
        )

    return {"saved": len(body.samples)}
