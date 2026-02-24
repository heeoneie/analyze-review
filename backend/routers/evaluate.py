# pylint: disable=import-outside-toplevel
"""AI 모델 평가 메트릭 API 엔드포인트"""

import asyncio
import json
import logging
from pathlib import Path

from fastapi import APIRouter, HTTPException

logger = logging.getLogger(__name__)
router = APIRouter()

METRICS_FILE = Path(__file__).resolve().parents[2] / "evaluation" / "metrics_latest.json"
DATASET_FILE = Path(__file__).resolve().parents[2] / "evaluation" / "evaluation_dataset.csv"


@router.get("/metrics")
async def get_metrics():
    """Pre-computed 평가 메트릭 반환"""
    if not METRICS_FILE.exists():
        raise HTTPException(404, "평가 결과 파일이 없습니다. 먼저 evaluate.py를 실행하세요.")

    with open(METRICS_FILE, encoding="utf-8") as f:
        return json.load(f)


@router.get("/dataset/info")
async def get_dataset_info():
    """Ground truth 데이터셋 정보 반환"""
    if not DATASET_FILE.exists():
        raise HTTPException(404, "데이터셋 파일이 없습니다.")

    import csv

    with open(DATASET_FILE, encoding="utf-8") as f:
        reader = csv.DictReader(f)
        rows = list(reader)

    label_counts: dict[str, int] = {}
    for row in rows:
        label = row["manual_label"]
        label_counts[label] = label_counts.get(label, 0) + 1

    return {
        "total_samples": len(rows),
        "label_distribution": label_counts,
        "dataset_file": str(DATASET_FILE.name),
    }


@router.post("/run")
async def run_evaluation():
    """평가 실행 (OpenAI API 호출 — 시간 소요)"""
    try:
        from core.experiments.evaluate import (
            Evaluator,  # pylint: disable=import-outside-toplevel
        )

        def _run():
            evaluator = Evaluator(ground_truth_file=str(DATASET_FILE))
            metrics, _ = evaluator.evaluate(mode="baseline")
            # 결과를 metrics_latest.json에 덮어씀
            if metrics:
                import datetime  # pylint: disable=import-outside-toplevel

                from core import (
                    config as _cfg,  # pylint: disable=import-outside-toplevel
                )

                model_name = (
                    _cfg.FALLBACK_LLM_MODEL
                    if _cfg.LLM_PROVIDER == "google"
                    else _cfg.LLM_MODEL
                )
                output = {
                    "meta": {
                        "model": model_name,
                        "temperature": float(_cfg.LLM_TEMPERATURE),
                        "dataset_size": 60,
                        "evaluated_at": datetime.datetime.now().isoformat(),
                        "mode": "baseline",
                        "dataset_file": "evaluation/evaluation_dataset.csv",
                    },
                    "overall": {
                        "accuracy": float(metrics["accuracy"]),
                        "precision_weighted": float(metrics["precision_weighted"]),
                        "recall_weighted": float(metrics["recall_weighted"]),
                        "f1_weighted": float(metrics["f1_weighted"]),
                    },
                    "per_class": {
                        k: {
                            "precision": float(v["precision"]),
                            "recall": float(v["recall"]),
                            "f1": float(v["f1"]),
                            "support": int(v["support"]),
                        }
                        for k, v in metrics["per_class_metrics"].items()
                    },
                }
                with open(METRICS_FILE, "w", encoding="utf-8") as f:
                    json.dump(output, f, indent=2, ensure_ascii=False)
            return metrics

        await asyncio.to_thread(_run)
        # JSON 파일에서 읽어 반환 (numpy 타입 직렬화 문제 회피)
        with open(METRICS_FILE, encoding="utf-8") as f:
            saved = json.load(f)
        return {"status": "completed", "metrics": saved}
    except Exception as e:
        logger.error("평가 실행 실패: %s", e)
        raise HTTPException(500, f"평가 실행 중 오류: {e}") from e
