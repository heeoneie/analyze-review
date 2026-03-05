"""KPI summary + risk timeline — real numbers from SQLite."""

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Query
from sqlalchemy import case, func
from sqlalchemy.orm import Session

from backend.database.database import get_db
from backend.database.models import Node, Review

router = APIRouter()


@router.get("/summary")
def get_kpi_summary(db: Session = Depends(get_db)):
    """Return live KPI stats from the database."""
    total_reviews = db.query(func.count(Review.id)).scalar() or 0  # pylint: disable=not-callable

    critical_risks = (
        db.query(func.count(Node.id))  # pylint: disable=not-callable
        .filter(Node.severity_score >= 8.0)
        .scalar()
        or 0
    )

    today_start = datetime.now(timezone.utc).replace(
        hour=0, minute=0, second=0, microsecond=0,
    )
    today_ingestions = (
        db.query(func.count(Review.id))  # pylint: disable=not-callable
        .filter(Review.ingested_at >= today_start)
        .scalar()
        or 0
    )

    # Weighted risk score: (sev 8-10)*5 + (sev 4-7)*2 + (sev 1-3)*1
    weight_expr = case(  # pylint: disable=not-callable
        (Node.severity_score >= 8.0, 5),
        (Node.severity_score >= 4.0, 2),
        else_=1,
    )
    overall_risk_score = (
        db.query(func.sum(weight_expr))  # pylint: disable=not-callable
        .scalar()
        or 0
    )

    # Total legal exposure from matched precedents
    total_legal_exposure_usd = (
        db.query(func.sum(Node.estimated_loss_usd))  # pylint: disable=not-callable
        .filter(Node.estimated_loss_usd > 0)
        .scalar()
        or 0
    )

    return {
        "total_scanned_reviews": total_reviews,
        "critical_risks_detected": critical_risks,
        "today_new_ingestions": today_ingestions,
        "overall_risk_score": overall_risk_score,
        "total_legal_exposure_usd": total_legal_exposure_usd,
    }


@router.get("/timeline")
def get_risk_timeline(
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    """Return the most recent high-severity risk detections."""
    rows = (
        db.query(Node)
        .filter(Node.severity_score >= 5.0)
        .order_by(Node.last_seen_at.desc())
        .limit(limit)
        .all()
    )
    return [
        {
            "id": r.id,
            "name": r.name,
            "type": r.type,
            "severity": r.severity_score,
            "source": r.source,
            "detected_at": r.last_seen_at.isoformat() if r.last_seen_at else None,
        }
        for r in rows
    ]
