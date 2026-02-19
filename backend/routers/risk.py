"""리스크 인텔리전스 API 엔드포인트"""

import asyncio
import logging

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from backend.services.risk_service import (
    generate_compliance_report,
    generate_meeting_agenda,
    generate_ontology,
)

logger = logging.getLogger(__name__)
router = APIRouter()


class RiskAnalysisRequest(BaseModel):
    top_issues: list = []
    emerging_issues: list = []
    recommendations: list = []
    all_categories: dict = {}
    stats: dict = {}
    industry: str = "ecommerce"


@router.post("/ontology")
async def create_ontology(request: RiskAnalysisRequest):
    try:
        result = await asyncio.to_thread(
            generate_ontology, request.model_dump()
        )
        return result
    except Exception as e:
        logger.error("온톨로지 생성 실패: %s", e)
        raise HTTPException(500, f"온톨로지 생성 중 오류: {e}") from e


@router.post("/compliance")
async def create_compliance_report(request: RiskAnalysisRequest):
    try:
        result = await asyncio.to_thread(
            generate_compliance_report, request.model_dump()
        )
        return result
    except Exception as e:
        logger.error("컴플라이언스 보고서 생성 실패: %s", e)
        raise HTTPException(500, f"보고서 생성 중 오류: {e}") from e


@router.post("/meeting")
async def create_meeting_agenda(request: RiskAnalysisRequest):
    try:
        result = await asyncio.to_thread(
            generate_meeting_agenda, request.model_dump()
        )
        return result
    except Exception as e:
        logger.error("회의 안건 생성 실패: %s", e)
        raise HTTPException(500, f"회의 안건 생성 중 오류: {e}") from e
