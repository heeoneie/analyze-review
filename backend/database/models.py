"""SQLAlchemy 2.0 models for the persistent ontology graph."""

from datetime import datetime, timezone

from sqlalchemy import (
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Base(DeclarativeBase):
    pass


class Node(Base):
    __tablename__ = "nodes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(512), nullable=False)
    normalized_name: Mapped[str] = mapped_column(String(512), nullable=False)
    type: Mapped[str] = mapped_column(String(64), nullable=False)
    severity_score: Mapped[float] = mapped_column(Float, default=0.0)
    source: Mapped[str | None] = mapped_column(String(256), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)
    last_seen_at: Mapped[datetime] = mapped_column(
        DateTime, default=_utcnow, onupdate=_utcnow,
    )

    outgoing_edges: Mapped[list["Edge"]] = relationship(
        "Edge", foreign_keys="Edge.source_node_id", back_populates="source_node",
        cascade="all, delete-orphan",
    )
    incoming_edges: Mapped[list["Edge"]] = relationship(
        "Edge", foreign_keys="Edge.target_node_id", back_populates="target_node",
        cascade="all, delete-orphan",
    )

    __table_args__ = (
        UniqueConstraint("normalized_name", "type", name="uq_node_norm_name_type"),
    )


class Edge(Base):
    __tablename__ = "edges"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    source_node_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("nodes.id", ondelete="CASCADE"), nullable=False,
    )
    target_node_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("nodes.id", ondelete="CASCADE"), nullable=False,
    )
    relationship_type: Mapped[str] = mapped_column(String(128), nullable=False)
    weight: Mapped[float] = mapped_column(Float, default=1.0)
    source: Mapped[str | None] = mapped_column(String(256), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)
    last_seen_at: Mapped[datetime] = mapped_column(
        DateTime, default=_utcnow, onupdate=_utcnow,
    )

    source_node: Mapped["Node"] = relationship(
        "Node", foreign_keys=[source_node_id], back_populates="outgoing_edges",
    )
    target_node: Mapped["Node"] = relationship(
        "Node", foreign_keys=[target_node_id], back_populates="incoming_edges",
    )

    __table_args__ = (
        UniqueConstraint(
            "source_node_id", "target_node_id", "relationship_type",
            name="uq_edge_src_tgt_rel",
        ),
    )
