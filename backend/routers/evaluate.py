# pylint: disable=import-outside-toplevel
"""AI 모델 평가 메트릭 API 엔드포인트"""

import asyncio
import csv
import json
import logging
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path

from fastapi import APIRouter, HTTPException

logger = logging.getLogger(__name__)
router = APIRouter()

_eval_lock = asyncio.Lock()

METRICS_FILE = Path(__file__).resolve().parents[2] / "evaluation" / "metrics_latest.json"
DATASET_FILE = Path(__file__).resolve().parents[2] / "evaluation" / "evaluation_dataset.csv"


@router.get("/metrics")
async def get_metrics():
    """Pre-computed 평가 메트릭 반환"""
    if not METRICS_FILE.exists():
        raise HTTPException(404, "평가 결과 파일이 없습니다. 먼저 evaluate.py를 실행하세요.")

    def _read():
        with open(METRICS_FILE, encoding="utf-8") as f:
            return json.load(f)

    return await asyncio.to_thread(_read)


@router.get("/dataset/info")
async def get_dataset_info():
    """Ground truth 데이터셋 정보 반환"""
    if not DATASET_FILE.exists():
        raise HTTPException(404, "데이터셋 파일이 없습니다.")

    def _read():
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

    return await asyncio.to_thread(_read)


@router.post("/run")
async def run_evaluation():
    """평가 실행 (OpenAI API 호출 — 시간 소요)"""
    if _eval_lock.locked():
        raise HTTPException(409, "평가가 이미 실행 중입니다. 완료 후 다시 시도하세요.")
    async with _eval_lock:
        try:
            from core.experiments.evaluate import Evaluator

            def _run():
                evaluator = Evaluator(ground_truth_file=str(DATASET_FILE))
                metrics, _ = evaluator.evaluate(mode="baseline")
                if metrics is None:
                    raise RuntimeError("평가 실패: Ground Truth 라벨이 부족하거나 데이터셋을 확인하세요.")

                from core import config as _cfg

                model_name = (
                    _cfg.FALLBACK_LLM_MODEL
                    if _cfg.LLM_PROVIDER == "google"
                    else _cfg.LLM_MODEL
                )

                with open(DATASET_FILE, encoding="utf-8") as f:
                    dataset_size = sum(1 for _ in csv.DictReader(f))

                output = {
                    "meta": {
                        "model": model_name,
                        "temperature": float(_cfg.LLM_TEMPERATURE),
                        "dataset_size": dataset_size,
                        "evaluated_at": datetime.now(timezone.utc).isoformat(),
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
                dir_path = METRICS_FILE.parent
                dir_path.mkdir(parents=True, exist_ok=True)
                fd, tmp_path = tempfile.mkstemp(dir=str(dir_path), suffix=".tmp")
                try:
                    with os.fdopen(fd, "w", encoding="utf-8") as f:
                        json.dump(output, f, indent=2, ensure_ascii=False)
                    os.replace(tmp_path, str(METRICS_FILE))
                except BaseException:
                    os.unlink(tmp_path)
                    raise
                return output

            saved = await asyncio.to_thread(_run)
            return {"status": "completed", "metrics": saved}
        except Exception as e:
            logger.exception("평가 실행 실패")
            raise HTTPException(500, "서버 오류로 평가를 실행하지 못했습니다.") from e
