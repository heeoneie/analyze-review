"""SQLAlchemy 2.0 models for the persistent ontology graph."""

from datetime import datetime, timezone

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
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
    case_id: Mapped[str | None] = mapped_column(String(32), nullable=True)
    estimated_loss_usd: Mapped[int] = mapped_column(Integer, default=0)
    source: Mapped[str | None] = mapped_column(String(256), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    last_seen_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, onupdate=_utcnow,
    )

    outgoing_edges: Mapped[list["Edge"]] = relationship(
        "Edge", foreign_keys="Edge.source_node_id", back_populates="source_node",
        cascade="all, delete-orphan", passive_deletes=True,
    )
    incoming_edges: Mapped[list["Edge"]] = relationship(
        "Edge", foreign_keys="Edge.target_node_id", back_populates="target_node",
        cascade="all, delete-orphan", passive_deletes=True,
    )

    __table_args__ = (
        UniqueConstraint("normalized_name", "type", name="uq_node_norm_name_type"),
        CheckConstraint("estimated_loss_usd >= 0", name="ck_node_estimated_loss_nonneg"),
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
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    last_seen_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, onupdate=_utcnow,
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


class Review(Base):
    """Ingested review from any source (Amazon, Coupang, CSV, etc.)."""

    __tablename__ = "reviews"
    __table_args__ = (
        CheckConstraint("rating BETWEEN 1 AND 5", name="ck_reviews_rating_1_5"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    source: Mapped[str] = mapped_column(String(64), nullable=False)
    product_url: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    rating: Mapped[int] = mapped_column(Integer, nullable=False)
    title: Mapped[str | None] = mapped_column(String(512), nullable=True)
    body: Mapped[str] = mapped_column(String(4096), nullable=False)
    severity: Mapped[float] = mapped_column(Float, default=0.0)
    risk_label: Mapped[str | None] = mapped_column(String(128), nullable=True)
    ingested_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow,
    )


class User(Base):
    """카카오 로그인으로 만들어지는 사장님 계정.

    비밀번호를 받지 않는다. 카카오가 인증을 대신하므로 우리가 보관할
    자격증명 자체가 없다.
    """

    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    # 카카오가 주는 회원번호. 문자열로 둔다 — 자릿수가 늘어도 안전하다.
    kakao_id: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    # 표시용. 카카오 프로필이 바뀌면 로그인할 때 같이 갱신된다.
    nickname: Mapped[str | None] = mapped_column(String(128), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    last_login_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, onupdate=_utcnow,
    )

    stores: Mapped[list["Store"]] = relationship(
        "Store", back_populates="owner", cascade="all, delete-orphan",
        passive_deletes=True,
    )


class Store(Base):
    """사장님이 운영하는 매장. 답글 말투 학습의 단위다."""

    __tablename__ = "stores"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    owner_user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False,
    )
    name: Mapped[str] = mapped_column(String(256), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)

    owner: Mapped["User"] = relationship("User", back_populates="stores")
    samples: Mapped[list["ReplySample"]] = relationship(
        "ReplySample", back_populates="store", cascade="all, delete-orphan",
        passive_deletes=True,
    )


class ReplySample(Base):
    """리뷰 한 건과 그에 달린 답글. 말투 학습의 재료다.

    한 테이블로 세 가지를 담는다 (`origin` 으로 구분):
      onboarding : 가입 때 사장님이 직접 써 넣은 답글. 생성본이 없다.
      generated  : 우리가 만든 답글을 사장님이 그대로 게시.
      edited     : 우리가 만든 답글을 사장님이 고쳐서 게시.

    few-shot 예시 풀은 `final_reply` 가 있는 행만 쓴다. 생성만 하고
    게시하지 않은 답글은 사장님이 채택했다는 근거가 없어서 학습에 넣으면
    안 된다.

    손님 닉네임은 컬럼 자체를 두지 않는다. 저장할 자리가 없으면 실수로도
    들어가지 않는다.
    """

    __tablename__ = "reply_samples"
    __table_args__ = (
        CheckConstraint("rating BETWEEN 1 AND 5", name="ck_reply_samples_rating_1_5"),
        CheckConstraint(
            "origin IN ('onboarding', 'generated', 'edited')",
            name="ck_reply_samples_origin",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    store_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("stores.id", ondelete="CASCADE"), nullable=False,
    )
    origin: Mapped[str] = mapped_column(String(16), nullable=False)

    review_body: Mapped[str] = mapped_column(Text, nullable=False)
    rating: Mapped[int] = mapped_column(Integer, nullable=False)
    menu: Mapped[str | None] = mapped_column(String(512), nullable=True)

    # 우리가 만든 답글. onboarding 행은 비어 있다.
    generated_reply: Mapped[str | None] = mapped_column(Text, nullable=True)
    # 사장님이 실제로 게시한 답글. 게시 전에는 비어 있다.
    final_reply: Mapped[str | None] = mapped_column(Text, nullable=True)
    # 생성본을 사장님이 고쳤는지. 고친 답글은 말투 학습에 특히 값지다.
    was_edited: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    finalized_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True,
    )

    store: Mapped["Store"] = relationship("Store", back_populates="samples")
