"""Ontology graph persistence — upsert nodes & edges from LLM output."""

import logging
from datetime import datetime, timezone

from sqlalchemy.dialects.sqlite import insert as sqlite_upsert
from sqlalchemy.orm import Session

from backend.database.models import Edge, Node

logger = logging.getLogger("ontoreview.graph_store")

_ZERO_RESULT = {"nodes_upserted": 0, "edges_upserted": 0}


def persist_ontology(  # pylint: disable=too-many-locals
    db: Session | None, ontology: dict, source: str = "risk_intelligence",
) -> dict:
    """
    Parse an LLM-generated ontology dict and upsert nodes/edges into SQLite.

    The caller owns the session — this function commits on success
    and rolls back on failure, but never closes the session.

    Accepts both ``"links"`` and ``"edges"`` as the edge key.
    Returns ``{"nodes_upserted": int, "edges_upserted": int}``.
    """
    if db is None:
        logger.warning("persist_ontology skipped: db session not provided")
        return _ZERO_RESULT

    raw_nodes = ontology.get("nodes") or []
    raw_edges = ontology.get("links") or ontology.get("edges") or []

    if not raw_nodes:
        return _ZERO_RESULT

    now = datetime.now(timezone.utc)

    try:
        # --- upsert nodes ---
        # Map LLM temp id → DB id
        temp_to_db: dict[str, int] = {}

        for n in raw_nodes:
            name = (n.get("label") or n.get("name") or "").strip()
            ntype = (n.get("type") or "unknown").strip()
            severity = float(n.get("severity") or n.get("severity_score") or 0)

            if not name:
                continue

            normalized = name.strip().lower()

            stmt = sqlite_upsert(Node).values(
                name=name,
                normalized_name=normalized,
                type=ntype,
                severity_score=severity,
                source=source,
                created_at=now,
                last_seen_at=now,
            )
            stmt = stmt.on_conflict_do_update(
                index_elements=["normalized_name", "type"],
                set_={
                    "severity_score": stmt.excluded.severity_score,
                    "last_seen_at": stmt.excluded.last_seen_at,
                    "source": stmt.excluded.source,
                },
            )
            db.execute(stmt)
            db.flush()

            # Retrieve the actual row id
            row = (
                db.query(Node.id)
                .filter(Node.normalized_name == normalized, Node.type == ntype)
                .first()
            )
            if row:
                temp_to_db[str(n.get("id", ""))] = row[0]

        # --- upsert edges ---
        edges_upserted = 0
        for e in raw_edges:
            src_temp = str(e.get("source", ""))
            tgt_temp = str(e.get("target", ""))
            rel = (
                e.get("relation")
                or e.get("relationship_type")
                or e.get("label")
                or "related"
            ).strip()
            weight = float(e.get("weight") or 1.0)

            src_id = temp_to_db.get(src_temp)
            tgt_id = temp_to_db.get(tgt_temp)
            if src_id is None or tgt_id is None:
                continue

            stmt = sqlite_upsert(Edge).values(
                source_node_id=src_id,
                target_node_id=tgt_id,
                relationship_type=rel,
                weight=weight,
                source=source,
                created_at=now,
                last_seen_at=now,
            )
            stmt = stmt.on_conflict_do_update(
                index_elements=["source_node_id", "target_node_id", "relationship_type"],
                set_={
                    "weight": stmt.excluded.weight,
                    "last_seen_at": stmt.excluded.last_seen_at,
                    "source": stmt.excluded.source,
                },
            )
            db.execute(stmt)
            edges_upserted += 1

        db.commit()
        # Expire cached ORM objects so subsequent reads see the committed state
        db.expire_all()
        # Count unique DB rows, not LLM temp IDs (duplicates map to same row)
        nodes_upserted = len(set(temp_to_db.values()))
        logger.info(
            "Ontology persisted: %d nodes, %d edges (source=%s)",
            nodes_upserted, edges_upserted, source,
        )
        return {"nodes_upserted": nodes_upserted, "edges_upserted": edges_upserted}

    except Exception:  # pylint: disable=broad-exception-caught
        db.rollback()
        logger.error("Failed to persist ontology", exc_info=True)
        return _ZERO_RESULT
