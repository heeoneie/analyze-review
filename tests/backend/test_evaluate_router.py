"""평가 라우터 테스트 — 출처 없는 정확도가 다시 새어 나가지 않게 막는다.

이 라우터는 한때 재현 불가능한 96.67% 를 서빙했다. 숫자만 지우고 끝내면
같은 상태로 돌아오므로, "출처가 선언되지 않은 수치는 구조적으로 서빙할 수 없다"
는 성질 자체를 테스트로 고정한다.
"""

import json

import pytest
from starlette.testclient import TestClient

from backend.main import app
from backend.routers import evaluate as evaluate_router


@pytest.fixture(name="client")
def _client():
    return TestClient(app)


@pytest.fixture(name="metrics_path")
def _metrics_path(tmp_path, monkeypatch):
    path = tmp_path / "metrics_latest.json"
    monkeypatch.setattr(evaluate_router, "METRICS_FILE", path)
    return path


@pytest.fixture(name="dataset_path")
def _dataset_path(tmp_path, monkeypatch):
    path = tmp_path / "evaluation_dataset.csv"
    monkeypatch.setattr(evaluate_router, "DATASET_FILE", path)
    return path


# ── /evaluate/metrics ──────────────────────────────────────

def test_no_metrics_file_reports_not_measured(client, metrics_path):
    """404 로 숨기지 않는다. 숨기면 '측정 안 함' 과 'API 죽음' 이 구분되지 않는다."""
    assert not metrics_path.exists()
    res = client.get("/api/evaluate/metrics")
    assert res.status_code == 200
    body = res.json()
    assert body["measured"] is False
    assert body["status"] == "not_measured"
    assert "how_to_measure" in body


def test_metrics_without_provenance_are_not_served(client, metrics_path):
    """이게 이 PR 의 핵심이다. 값이 들어 있어도 출처 선언이 없으면 안 내보낸다.

    제거된 파일이 정확히 이 모양이었다 — meta 에 model/temperature 는 있고
    ground_truth 는 없었다.
    """
    metrics_path.write_text(json.dumps({
        "meta": {"model": "gemini-2.0-flash", "dataset_size": 60},
        "overall": {"accuracy": 0.9667, "f1_weighted": 0.9646},
    }), encoding="utf-8")

    body = client.get("/api/evaluate/metrics").json()
    assert body["measured"] is False
    assert "overall" not in body
    assert "0.9667" not in json.dumps(body)


def test_metrics_with_llm_ground_truth_are_not_served(client, metrics_path):
    """LLM 이 단 라벨이라고 정직하게 선언해도 서빙하지 않는다."""
    metrics_path.write_text(json.dumps({
        "meta": {"ground_truth": "llm", "taxonomy_version": "v1"},
        "overall": {"accuracy": 0.95},
    }), encoding="utf-8")
    assert client.get("/api/evaluate/metrics").json()["measured"] is False


def test_metrics_with_human_ground_truth_are_served(client, metrics_path):
    metrics_path.write_text(json.dumps({
        "meta": {"ground_truth": "human", "taxonomy_version": "v1", "model": "gpt-4o-mini"},
        "overall": {"accuracy": 0.72},
    }), encoding="utf-8")
    body = client.get("/api/evaluate/metrics").json()
    assert body["measured"] is True
    assert body["status"] == "measured"
    assert body["overall"]["accuracy"] == 0.72


def test_corrupt_metrics_file_degrades_to_not_measured(client, metrics_path):
    metrics_path.write_text("{ 깨진 json", encoding="utf-8")
    assert client.get("/api/evaluate/metrics").json()["measured"] is False


# ── /evaluate/dataset/info ─────────────────────────────────

def test_absent_dataset_reports_absent(client, dataset_path):
    assert not dataset_path.exists()
    body = client.get("/api/evaluate/dataset/info").json()
    assert body["status"] == "absent"
    assert body["ground_truth"] is None


def test_llm_labeled_dataset_is_flagged_unverified(client, dataset_path):
    """confidence/reasoning 이 있고 labeled_at 이 없으면 LLM 이 단 라벨이다.
    제거 대상이던 evaluation_dataset.csv 가 정확히 이 모양이다."""
    dataset_path.write_text(
        "review_id,review_text,rating,manual_label,notes,confidence,reasoning\n"
        "1,배터리 빨리 닳아요,1,battery_issue,,0.95,배터리 언급\n"
        "2,화면이 이상해요,2,display_issue,,0.9,화면 언급\n",
        encoding="utf-8",
    )
    body = client.get("/api/evaluate/dataset/info").json()
    assert body["ground_truth"] == "unverified"
    assert "ground truth 로 쓰지 마세요" in body["note"]
    assert body["total_samples"] == 2


def test_human_labeled_dataset_is_recognised(client, dataset_path):
    dataset_path.write_text(
        "sample_id,review_text,rating,primary_label,alt_label,manual_label,notes,labeled_at\n"
        "1,국물이 식어서 왔어요,5,temperature,delivery_delay,temperature,,2026-09-15T00:00:00Z\n",
        encoding="utf-8",
    )
    body = client.get("/api/evaluate/dataset/info").json()
    assert body["ground_truth"] == "human"
    assert body["note"] is None


# ── /evaluate/run ──────────────────────────────────────────

def test_run_refuses_and_points_at_the_real_pipeline(client):
    """숫자를 지우고 그 숫자를 다시 만드는 버튼을 남겨 두면 고친 것이 아니다."""
    res = client.post("/api/evaluate/run")
    assert res.status_code == 409
    detail = res.json()["detail"]
    assert "scripts/eval/run_eval.py" in detail["use_instead"]
    assert "labeling_guide" in detail


def test_run_never_writes_a_metrics_file(client, metrics_path):
    client.post("/api/evaluate/run")
    assert not metrics_path.exists()
