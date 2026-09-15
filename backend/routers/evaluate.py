# pylint: disable=import-outside-toplevel
"""AI 모델 평가 메트릭 API 엔드포인트.

## 왜 이 라우터가 수치를 거의 내놓지 않는가

`evaluation/metrics_latest.json` 이 정확도 96.67% 를 서빙하고 있었다.
그 파일은 재현 불가능한 숫자였다:

  * 10개 클래스의 support 가 전부 정확히 6 (=60건)이었다. 실제 리뷰 표본에서
    이런 완벽한 균형은 나오지 않는다.
  * 같은 레포의 `evaluation/evaluation_dataset.csv` 는 100건·16라벨이고
    `battery_issue` 하나가 37건이다. 저 분포에서는 나올 수 없는 수치다.
  * 그 CSV 의 `manual_label` 조차 사람이 단 것이 아니다. 사람용 `notes` 는
    100건 전부 비어 있는데 LLM 출력 필드인 `confidence`·`reasoning` 은
    100건 전부 채워져 있다.

그래서 파일을 지우고, **출처가 증명되지 않은 수치는 구조적으로 서빙할 수 없게**
만들었다. 숫자만 지우고 그 숫자를 다시 만들어내는 경로를 남겨 두면 고친 것이
아니다 — 버튼 한 번이면 같은 상태로 돌아간다.

메트릭 파일은 `ground_truth: "human"` 과 `taxonomy_version` 을 반드시 선언해야
하고, 선언이 없으면 값이 들어 있어도 "측정 전" 으로 응답한다.

실제 측정은 `scripts/eval/run_eval.py` 로 한다 (사람이 직접 라벨링한 표본 필요).
"""

import asyncio
import csv
import json
import logging
from pathlib import Path

from fastapi import APIRouter, HTTPException

logger = logging.getLogger(__name__)
router = APIRouter()

METRICS_FILE = Path(__file__).resolve().parents[2] / "evaluation" / "metrics_latest.json"
DATASET_FILE = Path(__file__).resolve().parents[2] / "evaluation" / "evaluation_dataset.csv"

#: 메트릭 파일이 이 값을 선언해야만 수치를 서빙한다.
REQUIRED_GROUND_TRUTH = "human"

NOT_MEASURED = {
    "status": "not_measured",
    "measured": False,
    "reason": "사람이 직접 라벨링한 평가 표본이 아직 없습니다.",
    "detail": (
        "이전에 서빙되던 정확도 96.67% 는 레포의 어떤 데이터셋에서도 재현되지 "
        "않는 수치여서 제거했습니다. LLM 이 생성한 라벨로 LLM 분류기를 평가하면 "
        "순환 논리가 되어 숫자가 무의미합니다."
    ),
    "how_to_measure": [
        "python scripts/eval/build_sample.py --csv <리뷰CSV> --out evaluation/sample_v1.csv",
        "python scripts/eval/label_tool.py evaluation/sample_v1.csv",
        "python scripts/eval/run_eval.py evaluation/sample_v1.csv --systems all",
    ],
    "labeling_guide": "docs/evaluation/labeling-guide-v1.md",
}


def _load_metrics() -> dict | None:
    """출처가 선언된 메트릭만 돌려준다. 아니면 None."""
    if not METRICS_FILE.exists():
        return None
    try:
        with open(METRICS_FILE, encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, json.JSONDecodeError):
        logger.exception("메트릭 파일을 읽을 수 없습니다: %s", METRICS_FILE)
        return None

    meta = data.get("meta") or {}
    if meta.get("ground_truth") != REQUIRED_GROUND_TRUTH:
        # 값이 들어 있어도 서빙하지 않는다. 출처가 없는 정확도는 정확도가 아니다.
        logger.warning(
            "메트릭 파일에 ground_truth='%s' 선언이 없어 '측정 전' 으로 응답합니다: %s",
            REQUIRED_GROUND_TRUTH, METRICS_FILE,
        )
        return None
    return data


@router.get("/metrics")
async def get_metrics():
    """평가 메트릭 반환. 측정 전이면 그 사실을 명시적으로 알린다.

    404 로 숨기지 않는다. 숨기면 대시보드가 카드를 통째로 안 그리고,
    "아직 측정 안 함" 과 "API 가 죽음" 이 구분되지 않는다.
    """
    data = await asyncio.to_thread(_load_metrics)
    if data is None:
        return NOT_MEASURED
    return {"status": "measured", "measured": True, **data}


@router.get("/dataset/info")
async def get_dataset_info():
    """평가 데이터셋 정보. 라벨 출처를 함께 밝힌다."""
    if not DATASET_FILE.exists():
        return {
            "status": "absent",
            "total_samples": 0,
            "label_distribution": {},
            "ground_truth": None,
            "note": "평가 표본이 없습니다. scripts/eval/build_sample.py 로 만드세요.",
        }

    def _read():
        with open(DATASET_FILE, encoding="utf-8-sig") as f:
            rows = list(csv.DictReader(f))

        label_counts: dict[str, int] = {}
        for row in rows:
            label = (row.get("manual_label") or "").strip()
            if label:
                label_counts[label] = label_counts.get(label, 0) + 1

        # 이 파일이 LLM 라벨인지 사람 라벨인지 구분하는 신호.
        # 사람 라벨링 도구는 notes/labeled_at 을 남기고 confidence/reasoning 은
        # 쓰지 않는다. 반대면 LLM 이 만든 라벨이다.
        fields = set(rows[0]) if rows else set()
        llm_fields = {"confidence", "reasoning"} & fields
        human_labeled = bool(fields & {"labeled_at"}) and not llm_fields

        return {
            "status": "present",
            "total_samples": len(rows),
            "label_distribution": label_counts,
            "distinct_labels": len(label_counts),
            "ground_truth": "human" if human_labeled else "unverified",
            "note": (
                None if human_labeled else
                "이 파일의 라벨은 사람이 단 것으로 확인되지 않습니다 "
                f"(LLM 출력 필드 {sorted(llm_fields) or '없음'}, 사람 라벨링 흔적 없음). "
                "ground truth 로 쓰지 마세요."
            ),
            "dataset_file": DATASET_FILE.name,
        }

    return await asyncio.to_thread(_read)


@router.post("/run")
async def run_evaluation():
    """이 경로는 더 이상 평가를 실행하지 않는다.

    예전에는 `core/experiments/evaluate.py` 를 호출해 metrics_latest.json 을
    덮어썼다. 그 경로에는 결함이 세 개 있다:

      1. ground truth 로 쓰는 CSV 의 라벨이 사람이 단 것이 아니다.
      2. 응답에서 빠진 리뷰를 조용히 'other' 로 채워(evaluate.py:127)
         프롬프트 준수 실패가 정확도로 위장된다.
      3. 이커머스 공산품 기준 영어 10종 체계를 쓰는데, 지금 데이터는
         배달 외식업이라 맛·온도·위생이 poor_quality 하나로 뭉개진다.

    이 상태로 버튼 하나에 숫자가 다시 만들어지면, 파일을 지운 것이 의미가 없다.
    """
    raise HTTPException(
        status_code=409,
        detail={
            "message": "이 경로로는 평가를 실행하지 않습니다.",
            "reason": (
                "기존 평가 경로는 LLM 이 생성한 라벨을 ground truth 로 쓰고, "
                "응답 누락을 'other' 로 채워 정확도를 부풀립니다."
            ),
            "use_instead": "python scripts/eval/run_eval.py <표본CSV> --systems all",
            "labeling_guide": "docs/evaluation/labeling-guide-v1.md",
        },
    )
