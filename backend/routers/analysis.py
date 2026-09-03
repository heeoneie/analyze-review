import asyncio
import logging

from fastapi import APIRouter, HTTPException

from backend.routers.data import analysis_settings, uploaded_files
from backend.services.analysis_service import run_full_analysis

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/run")
async def run_analysis():
    csv_path = uploaded_files.get("current")
    if not csv_path:
        raise HTTPException(400, "먼저 CSV 파일을 업로드해주세요.")

    try:
        rating_threshold = analysis_settings.get("rating_threshold", 3)
        result = await asyncio.to_thread(
            run_full_analysis, csv_path, rating_threshold=rating_threshold
        )
        return result
    except Exception as e:
        raise HTTPException(500, f"분석 중 오류 발생: {e}") from e
