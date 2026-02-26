"""리스크 인텔리전스 API 엔드포인트"""

import logging
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from backend.database.database import get_db
from backend.database.models import Edge, Node
from backend.services.risk_service import (
    analyze_demo_scenario,
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
    lang: str = "ko"


@router.post("/ontology")
def create_ontology(
    request: RiskAnalysisRequest,
    db: Session = Depends(get_db),
):
    try:
        return generate_ontology(request.model_dump(), db)
    except Exception as e:
        logger.error("온톨로지 생성 실패: %s", e)
        raise HTTPException(500, f"온톨로지 생성 중 오류: {e}") from e


@router.post("/compliance")
def create_compliance_report(request: RiskAnalysisRequest):
    try:
        return generate_compliance_report(request.model_dump())
    except Exception as e:
        logger.error("컴플라이언스 보고서 생성 실패: %s", e)
        raise HTTPException(500, f"보고서 생성 중 오류: {e}") from e


@router.post("/demo")
def run_demo_scenario(
    industry: str = "ecommerce",
    lang: str = "ko",
    db: Session = Depends(get_db),
):
    """산업별 위기 시나리오 Mock — 4채널 동시 감지 → Red Alert"""
    try:
        return analyze_demo_scenario(industry, lang, db)
    except Exception as e:
        logger.error("데모 시나리오 분석 실패: %s", e)
        raise HTTPException(500, f"데모 분석 중 오류: {e}") from e


@router.post("/meeting")
def create_meeting_agenda(request: RiskAnalysisRequest):
    try:
        return generate_meeting_agenda(request.model_dump())
    except Exception as e:
        logger.error("회의 안건 생성 실패: %s", e)
        raise HTTPException(500, f"회의 안건 생성 중 오류: {e}") from e


@router.get("/ontology/graph")
def get_ontology_graph(
    limit: int = Query(500, ge=1, le=5000),
    min_severity: float = Query(0, ge=0, le=10),
    since: str | None = Query(None, description="ISO datetime filter (e.g. 2026-01-01T00:00:00)"),
    db: Session = Depends(get_db),
):
    """Retrieve the persisted ontology graph in React Flow-friendly format."""
    node_q = db.query(Node).filter(Node.severity_score >= min_severity)

    if since:
        try:
            since_dt = datetime.fromisoformat(since)
        except ValueError as exc:
            raise HTTPException(400, "Invalid 'since' format. Use ISO 8601.") from exc
        if since_dt.tzinfo is None:
            raise HTTPException(
                400,
                "The 'since' parameter must be a timezone-aware ISO datetime "
                "string (e.g., ends with 'Z' or '+00:00').",
            )
        node_q = node_q.filter(Node.last_seen_at >= since_dt)

    nodes = node_q.order_by(Node.severity_score.desc()).limit(limit).all()

    if not nodes:
        return {"nodes": [], "edges": []}

    node_ids = {n.id for n in nodes}

    # Only include edges where BOTH endpoints exist in the filtered node set
    edges = (
        db.query(Edge)
        .filter(Edge.source_node_id.in_(node_ids), Edge.target_node_id.in_(node_ids))
        .all()
    )

    rf_nodes = [
        {
            "id": str(n.id),
            "data": {
                "label": n.name,
                "type": n.type,
                "severity_score": n.severity_score,
            },
            "position": {"x": 0, "y": 0},
        }
        for n in nodes
    ]

    rf_edges = [
        {
            "id": str(e.id),
            "source": str(e.source_node_id),
            "target": str(e.target_node_id),
            "label": e.relationship_type,
            "data": {"weight": e.weight},
        }
        for e in edges
    ]

    return {"nodes": rf_nodes, "edges": rf_edges}
