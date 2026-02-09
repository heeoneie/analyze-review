import asyncio
import glob as g
import json
import logging
from pathlib import Path

from fastapi import APIRouter, HTTPException

from backend.routers.data import uploaded_files, analysis_settings
from backend.services.analysis_service import run_full_analysis

logger = logging.getLogger(__name__)
router = APIRouter()

AI_DIR = str(Path(__file__).resolve().parents[2] / "ai")


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


@router.get("/experiment-results")
def get_experiment_results():
    results_dir = str(Path(AI_DIR) / "results")
    data = {}

    for key, pattern in [
        ("baseline", "baseline_metrics_*.json"),
        ("prompt_experiments", "prompt_experiments_*.json"),
        ("rag", "rag_evaluation_*.json"),
    ]:
        files = sorted(g.glob(str(Path(results_dir) / pattern)))
        if files:
            try:
                with open(files[-1], encoding="utf-8") as f:
                    data[key] = json.load(f)
            except (OSError, json.JSONDecodeError) as e:
                logger.warning("Failed to load %s: %s", key, e)

    return data
