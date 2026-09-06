"""reviews 에 store_id 추가 — 매장별로 리뷰를 가른다

수집한 리뷰를 대시보드에서 보려면 DB 에 남겨야 하고, 남기는 순간
"누구 매장 리뷰인가" 가 필요해진다. 매장 사이에 리뷰가 섞이면 개인정보
보호법 제26조 ⑤ 위반이라 컬럼 없이는 조회를 열 수 없다 (CLAUDE.md).

NULL 을 허용한다. 카카오 로그인을 켜기 전에는 접속코드 하나를 공유하고
매장 개념이 없어서, 그 경로로 들어온 리뷰는 NULL 버킷에 쌓인다. 접속코드가
하나뿐이므로 그때는 매장도 하나다.

기존 행은 없다 — 이 컬럼이 생기기 전까지 reviews 에 쓰던 코드는
amazon_service 하나였고 #42 에서 지웠다. 그래서 백필할 값이 없다.

Revision ID: c3a91f4d70b2
Revises: b7c4e9f21a08
Create Date: 2026-09-06
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "c3a91f4d70b2"
down_revision: Union[str, Sequence[str], None] = "b7c4e9f21a08"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_INDEX = "ix_reviews_store_id"


def _columns() -> set[str]:
    return {c["name"] for c in sa.inspect(op.get_bind()).get_columns("reviews")}


def _indexes() -> set[str]:
    return {i["name"] for i in sa.inspect(op.get_bind()).get_indexes("reviews")}


def upgrade() -> None:
    # create_all 로 만들어진 DB 에는 이미 있을 수 있다.
    if "store_id" not in _columns():
        # SQLite 는 ALTER TABLE ADD COLUMN 에 FK 를 붙이지 못한다. batch 가
        # 테이블을 새로 만들어 옮기므로 제약이 실제로 걸린다.
        with op.batch_alter_table("reviews") as batch_op:
            batch_op.add_column(sa.Column("store_id", sa.Integer(), nullable=True))
            batch_op.create_foreign_key(
                "fk_reviews_store_id", "stores", ["store_id"], ["id"],
                ondelete="CASCADE",
            )

    if _INDEX not in _indexes():
        op.create_index(_INDEX, "reviews", ["store_id"])


def downgrade() -> None:
    """컬럼을 뺀다. store_id 값은 사라지지만 리뷰 행 자체는 남는다."""
    if _INDEX in _indexes():
        op.drop_index(_INDEX, table_name="reviews")

    if "store_id" in _columns():
        with op.batch_alter_table("reviews") as batch_op:
            batch_op.drop_column("store_id")
