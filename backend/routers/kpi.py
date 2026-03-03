"""KPI summary + risk timeline — real numbers from SQLite."""

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func
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

    return {
        "total_scanned_reviews": total_reviews,
        "critical_risks_detected": critical_risks,
        "today_new_ingestions": today_ingestions,
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
