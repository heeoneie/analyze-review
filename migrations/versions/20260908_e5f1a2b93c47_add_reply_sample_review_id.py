"""reply_samples 에 review_id 추가 — 수집한 리뷰와 답글을 잇는다

"모은 리뷰 전체에 한번에 답글 만들기" 를 하려면 어떤 리뷰가 아직 답글이
없는지 알아야 한다. 지금은 답글이 리뷰 본문 텍스트만 들고 있어서, 다시
누르면 이미 만든 것을 또 만든다.

붙여넣기로 만든 답글은 가리킬 리뷰가 없으므로 NULL 을 허용한다.
리뷰가 지워져도 답글은 남긴다(SET NULL) — 말투 학습의 재료다.

Revision ID: e5f1a2b93c47
Revises: c3a91f4d70b2
Create Date: 2026-09-08
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "e5f1a2b93c47"
down_revision: Union[str, Sequence[str], None] = "c3a91f4d70b2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_INDEX = "ix_reply_samples_review_id"


def _columns() -> set[str]:
    return {c["name"] for c in sa.inspect(op.get_bind()).get_columns("reply_samples")}


def _indexes() -> set[str]:
    return {i["name"] for i in sa.inspect(op.get_bind()).get_indexes("reply_samples")}


def upgrade() -> None:
    if "review_id" not in _columns():
        # SQLite 는 ALTER TABLE ADD COLUMN 에 FK 를 붙이지 못한다.
        # batch 가 테이블을 새로 만들어 옮기므로 제약이 실제로 걸린다.
        with op.batch_alter_table("reply_samples") as batch_op:
            batch_op.add_column(sa.Column("review_id", sa.Integer(), nullable=True))
            batch_op.create_foreign_key(
                "fk_reply_samples_review_id", "reviews", ["review_id"], ["id"],
                ondelete="SET NULL",
            )

    if _INDEX not in _indexes():
        op.create_index(_INDEX, "reply_samples", ["review_id"])


def downgrade() -> None:
    """컬럼을 뺀다. 어느 리뷰의 답글이었는지는 잃지만 답글 자체는 남는다."""
    if _INDEX in _indexes():
        op.drop_index(_INDEX, table_name="reply_samples")

    if "review_id" in _columns():
        with op.batch_alter_table("reply_samples") as batch_op:
            batch_op.drop_column("review_id")
