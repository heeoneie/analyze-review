import glob as g
import json
import os

from fastapi import APIRouter, HTTPException

from backend.routers.data import uploaded_files, analysis_settings
from backend.services.analysis_service import run_full_analysis

router = APIRouter()

AI_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "ai")


@router.post("/run")
async def run_analysis():
    csv_path = uploaded_files.get("current")
    if not csv_path:
        raise HTTPException(400, "먼저 CSV 파일을 업로드해주세요.")

    try:
        rating_threshold = analysis_settings.get("rating_threshold", 3)
        result = run_full_analysis(csv_path, rating_threshold=rating_threshold)
        return result
    except Exception as e:
        raise HTTPException(500, f"분석 중 오류 발생: {e}") from e


@router.get("/experiment-results")
def get_experiment_results():
    results_dir = os.path.join(AI_DIR, "results")
    data = {}

    baseline_files = sorted(g.glob(os.path.join(results_dir, "baseline_metrics_*.json")))
    if baseline_files:
        with open(baseline_files[-1], encoding="utf-8") as f:
            data["baseline"] = json.load(f)

    prompt_files = sorted(g.glob(os.path.join(results_dir, "prompt_experiments_*.json")))
    if prompt_files:
        with open(prompt_files[-1], encoding="utf-8") as f:
            data["prompt_experiments"] = json.load(f)

    rag_files = sorted(g.glob(os.path.join(results_dir, "rag_evaluation_*.json")))
    if rag_files:
        with open(rag_files[-1], encoding="utf-8") as f:
            data["rag"] = json.load(f)

    return data
