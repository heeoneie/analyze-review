"""Tests for ontology graph persistence (in-memory SQLite — no LLM calls)."""

import logging
from datetime import datetime, timezone

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from backend.database.graph_store import persist_ontology
from backend.database.models import Base, Edge, Node


@pytest.fixture()
def db_session():
    """Create an in-memory SQLite database and yield a session."""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
    )
    Base.metadata.create_all(bind=engine)
    session_cls = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    session = session_cls()
    try:
        yield session
    finally:
        session.close()
        engine.dispose()


MOCK_ONTOLOGY = {
    "nodes": [
        {"id": "n1", "label": "Battery Explosion", "type": "event", "severity": 9},
        {"id": "n2", "label": "Product Recall", "type": "impact", "severity": 8},
        {"id": "n3", "label": "Legal Team", "type": "department", "severity": 5},
        {"id": "n4", "label": "  Battery Explosion  ", "type": "event", "severity": 7},
    ],
    "links": [
        {"source": "n1", "target": "n2", "relation": "리스크_유발"},
        {"source": "n2", "target": "n3", "relation": "대응_필요"},
    ],
    "summary": "Test ontology",
}


def test_persist_creates_nodes_and_edges(db_session):
    result = persist_ontology(db_session, MOCK_ONTOLOGY, source="test")

    # n1 and n4 have the same normalized_name "battery explosion" + type "event"
    # so they are deduplicated into one row → 3 unique nodes
    assert result["nodes_upserted"] == 3
    assert result["edges_upserted"] == 2

    nodes = db_session.query(Node).all()
    assert len(nodes) == 3

    edges = db_session.query(Edge).all()
    assert len(edges) == 2


def test_upsert_updates_severity(db_session):
    persist_ontology(db_session, MOCK_ONTOLOGY, source="first")

    node_before = (
        db_session.query(Node)
        .filter(Node.normalized_name == "battery explosion", Node.type == "event")
        .first()
    )
    # n4 overwrites n1 because it runs second → severity should be 7
    assert node_before.severity_score == 7.0

    updated = {
        "nodes": [
            {"id": "n1", "label": "Battery Explosion", "type": "event", "severity": 10},
        ],
        "links": [],
    }
    persist_ontology(db_session, updated, source="second")

    node_after = (
        db_session.query(Node)
        .filter(Node.normalized_name == "battery explosion", Node.type == "event")
        .first()
    )
    assert node_after.severity_score == 10.0
    assert node_after.source == "second"

    # Total node count should not increase
    total = db_session.query(Node).count()
    assert total == 3


def test_normalized_name_dedup_case_insensitive(db_session):
    ontology = {
        "nodes": [
            {"id": "a", "label": "Data Breach", "type": "event", "severity": 8},
            {"id": "b", "label": "data breach", "type": "event", "severity": 6},
            {"id": "c", "label": "  DATA BREACH  ", "type": "event", "severity": 5},
        ],
        "links": [],
    }
    result = persist_ontology(db_session, ontology, source="test")
    assert result["nodes_upserted"] == 1

    node = db_session.query(Node).first()
    assert node.normalized_name == "data breach"
    # Last writer wins for severity
    assert node.severity_score == 5.0


def test_edges_key_alias(db_session):
    """LLM may return 'edges' instead of 'links'."""
    ontology = {
        "nodes": [
            {"id": "x", "label": "Src", "type": "event", "severity": 5},
            {"id": "y", "label": "Tgt", "type": "impact", "severity": 5},
        ],
        "edges": [
            {"source": "x", "target": "y", "relationship_type": "causes"},
        ],
    }
    result = persist_ontology(db_session, ontology, source="test")
    assert result["edges_upserted"] == 1

    edge = db_session.query(Edge).first()
    assert edge.relationship_type == "causes"


def test_empty_ontology_returns_zero(db_session):
    result = persist_ontology(db_session, {"nodes": [], "links": []}, source="test")
    assert result == {"nodes_upserted": 0, "edges_upserted": 0}


def test_dangling_edge_skipped(db_session):
    """Edge referencing a non-existent node temp-id should be silently skipped."""
    ontology = {
        "nodes": [
            {"id": "a", "label": "Only Node", "type": "event", "severity": 5},
        ],
        "links": [
            {"source": "a", "target": "missing", "relation": "causes"},
        ],
    }
    result = persist_ontology(db_session, ontology, source="test")
    assert result["nodes_upserted"] == 1
    assert result["edges_upserted"] == 0


def test_timestamps_are_utc(db_session):
    before = datetime.now(timezone.utc).replace(tzinfo=None)
    persist_ontology(db_session, MOCK_ONTOLOGY, source="test")
    after = datetime.now(timezone.utc).replace(tzinfo=None)

    node = db_session.query(Node).first()
    assert node.created_at is not None
    assert node.last_seen_at is not None
    # SQLite strips tzinfo on round-trip; verify value is within UTC window
    assert before <= node.created_at <= after
    assert before <= node.last_seen_at <= after


def test_db_none_logs_warning_and_returns_zero(caplog):
    """When db=None, persist_ontology must warn and return zero counts."""
    with caplog.at_level(logging.WARNING, logger="ontoreview.graph_store"):
        result = persist_ontology(None, MOCK_ONTOLOGY, source="test")

    assert result == {"nodes_upserted": 0, "edges_upserted": 0}
    assert "persist_ontology skipped: db session not provided" in caplog.text
