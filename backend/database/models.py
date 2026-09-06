"""SQLAlchemy 2.0 models — 수집한 리뷰, 사장님 계정, 답글 이력."""

# pylint 이 `Mapped[int]` 같은 정상 표기를 unsubscriptable-object 로 본다.
# SQLAlchemy 2.0 의 Mapped 는 Generic 이라 첨자 표기가 맞고, 실제로 모델은
# 정상 동작한다 (마이그레이션 드리프트 검사와 전체 테스트가 이를 고정한다).
# astroid 4.0.4 가 이 모듈에서만 Mapped 추론에 실패한다 — Node/Edge 모델을
# 지우자 나타났고, 클래스 순서나 __table_args__ 위치와는 무관했다.
# 오탐을 이 파일 안으로만 가둔다. 다른 모듈의 진짜 첨자 오류는 계속 잡힌다.
# pylint: disable=unsubscriptable-object

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
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Base(DeclarativeBase):
    pass


class Review(Base):
    """수집한 손님 리뷰 한 건.

    매장별로 갈라 둔다. 리뷰는 손님의 개인정보를 담을 수 있고, 우리는
    사장님의 수탁자로서 매장 사이에 데이터를 섞으면 안 된다 (CLAUDE.md
    참고). 조회는 반드시 store_id 로 거른다.

    store_id 가 NULL 인 행은 카카오 로그인을 켜기 전 접속코드로 들어온
    이행기 데이터다. 그때는 접속코드가 하나뿐이라 매장도 하나다.
    """

    __tablename__ = "reviews"
    __table_args__ = (
        CheckConstraint("rating BETWEEN 1 AND 5", name="ck_reviews_rating_1_5"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    store_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("stores.id", ondelete="CASCADE"),
        nullable=True, index=True,
    )
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
    # 유일 제약이 이관을 원자적으로 1회로 만든다. 없으면 동시 요청 둘이
    # 모두 "아직 없음" 을 보고 같은 매장을 두 번 만든다.
    # 한 사장님이 여러 매장을 갖거나 상호가 겹치는 날에는 (owner, name)
    # 복합 유일로 바꿔야 한다. 지금은 매장을 만드는 경로가 이관 하나뿐이다.
    name: Mapped[str] = mapped_column(String(256), nullable=False, unique=True)
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
