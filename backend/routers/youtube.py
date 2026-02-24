"""YouTube 실데이터 수집 + 리스크 분석 API"""

import asyncio
import logging

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from backend.services.risk_service import analyze_youtube_scenario
from backend.services.youtube_service import collect_youtube_signals

logger = logging.getLogger(__name__)
router = APIRouter()


class YouTubeAnalyzeRequest(BaseModel):
    query: str = Field(..., description="검색어 (브랜드명, 제품명, 이슈 키워드)")
    brand: str = Field(..., description="브랜드명 (리포트 제목에 사용)")
    lang: str = Field("ko", description="응답 언어 (ko | en)")
    max_videos: int = Field(3, ge=1, le=5, description="수집할 최대 영상 수")
    max_comments_per_video: int = Field(15, ge=5, le=30, description="영상당 최대 댓글 수")


@router.post("/analyze")
async def analyze_youtube(req: YouTubeAnalyzeRequest):
    """
    YouTube 댓글을 실시간 수집한 뒤 리스크 인텔리전스 분석 수행.
    analyze_demo_scenario 와 동일한 응답 구조 반환.
    """
    def _run():
        signals, meta = collect_youtube_signals(
            query=req.query,
            max_videos=req.max_videos,
            max_comments_per_video=req.max_comments_per_video,
        )
        if not signals:
            raise ValueError(
                f"'{req.query}' 검색 결과에서 댓글을 수집하지 못했습니다. "
                "검색어를 바꾸거나 댓글이 활성화된 영상이 있는지 확인하세요."
            )

        result = analyze_youtube_scenario(signals, brand=req.brand, lang=req.lang)
        result["meta"] = meta
        return result

    try:
        result = await asyncio.to_thread(_run)
        return result
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e)) from e
    except Exception as e:
        logger.error("YouTube 분석 실패: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail=f"YouTube 분석 중 오류: {e}") from e
