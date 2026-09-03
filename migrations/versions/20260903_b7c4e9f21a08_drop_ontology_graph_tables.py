"""온톨로지 그래프 테이블(nodes, edges) 제거

리스크 인텔리전스(OntoReview) 갈래를 저장소에서 뺐다. 두 테이블에 쓰고
읽던 코드가 `risk_service` 와 `graph_store` 뿐이었고 둘 다 사라졌다.
모델(`Node`, `Edge`)도 이 커밋에서 함께 지운다. 테이블만 남겨 두면
다음에 누가 `alembic revision --autogenerate` 를 돌릴 때 관계없는
drop_table 이 딸려 들어온다.

⚠️ upgrade 는 두 테이블의 **데이터를 지운다.** 되돌릴 수 없다.
   담긴 것은 리뷰에서 뽑아낸 리스크 온톨로지 산출물이고, 이제 이
   저장소에는 그것을 읽을 코드도 다시 만들 코드도 없다.

   배포 전에 백업할 것. 돌고 있는 DB 는 `cp` 로 뜨지 않는다 — 쓰기가
   진행 중이면 반쪽짜리 파일이 나오고, 나중에 WAL 을 켜면 커밋된 내용이
   -wal 파일에 남아 아예 빠진다. sqlite 온라인 백업 API 를 쓴다:

       docker compose exec app python -c "import sqlite3; \
         src=sqlite3.connect('/app/var/app.db'); \
         dst=sqlite3.connect('/app/var/app.db.bak'); \
         src.backup(dst); src.close(); dst.close()"
       docker compose cp app:/app/var/app.db.bak ./app.db.bak

   경로는 docker-compose.yml 의 DATABASE_URL 기준이다 (/app/var/app.db).

⚠️ downgrade 는 **빈 테이블만 복원한다.** 스키마는 돌아오지만 행은
   돌아오지 않는다. 백업 파일이 유일한 복구 수단이다.

Revision ID: b7c4e9f21a08
Revises: a1b2c3d4e5f6
Create Date: 2026-09-03
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "b7c4e9f21a08"
down_revision: Union[str, Sequence[str], None] = "a1b2c3d4e5f6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _existing_tables() -> set[str]:
    return set(sa.inspect(op.get_bind()).get_table_names())


def upgrade() -> None:
    existing = _existing_tables()

    # edges 가 nodes 를 FK 로 참조하므로 자식부터 지운다.
    if "edges" in existing:
        op.drop_table("edges")
    if "nodes" in existing:
        op.drop_table("nodes")


def downgrade() -> None:
    """스키마만 되돌린다. 데이터는 복구되지 않는다.

    베이스라인이 만들던 정의를 그대로 옮겼다. 제약 이름까지 같아야
    `alembic downgrade` 후 다시 `upgrade` 할 때 어긋나지 않는다.
    """
    existing = _existing_tables()

    if "nodes" not in existing:
        op.create_table(
            "nodes",
            sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
            sa.Column("name", sa.String(length=512), nullable=False),
            sa.Column("normalized_name", sa.String(length=512), nullable=False),
            sa.Column("type", sa.String(length=64), nullable=False),
            sa.Column("severity_score", sa.Float(), nullable=False),
            sa.Column("case_id", sa.String(length=32), nullable=True),
            sa.Column("estimated_loss_usd", sa.Integer(), nullable=False),
            sa.Column("source", sa.String(length=256), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=False),
            sa.CheckConstraint(
                "estimated_loss_usd >= 0", name="ck_node_estimated_loss_nonneg"
            ),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint(
                "normalized_name", "type", name="uq_node_norm_name_type"
            ),
        )

    if "edges" not in existing:
        op.create_table(
            "edges",
            sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
            sa.Column("source_node_id", sa.Integer(), nullable=False),
            sa.Column("target_node_id", sa.Integer(), nullable=False),
            sa.Column("relationship_type", sa.String(length=128), nullable=False),
            sa.Column("weight", sa.Float(), nullable=False),
            sa.Column("source", sa.String(length=256), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=False),
            sa.ForeignKeyConstraint(
                ["source_node_id"], ["nodes.id"], ondelete="CASCADE"
            ),
            sa.ForeignKeyConstraint(
                ["target_node_id"], ["nodes.id"], ondelete="CASCADE"
            ),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint(
                "source_node_id",
                "target_node_id",
                "relationship_type",
                name="uq_edge_src_tgt_rel",
            ),
        )
