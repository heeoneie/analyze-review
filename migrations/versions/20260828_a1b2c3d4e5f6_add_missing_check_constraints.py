"""nodes/reviews 에 빠져 있던 CHECK 제약 복구

모델에는 있었지만 DB 에는 없던 두 제약을 채운다. create_all 은 이미 있는
테이블을 손대지 않아서, 모델에 제약을 더한 시점 이전에 만들어진 DB 는
계속 제약 없이 돌고 있었다. `alembic check` 가 이 어긋남을 잡아냈다.

SQLite 는 ALTER TABLE ADD CONSTRAINT 가 없다. batch 모드가 테이블을 새로
만들어 데이터를 옮기고 이름을 바꿔치기한다. 위반 행이 있으면 이 단계에서
실패하므로, 실패한다면 데이터를 먼저 고쳐야 한다.

Revision ID: a1b2c3d4e5f6
Revises: d0effa13eb85
Create Date: 2026-08-28
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "a1b2c3d4e5f6"
down_revision: Union[str, Sequence[str], None] = "d0effa13eb85"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# (테이블, 제약 이름, 조건)
_CONSTRAINTS = (
    ("nodes", "ck_node_estimated_loss_nonneg", "estimated_loss_usd >= 0"),
    ("reviews", "ck_reviews_rating_1_5", "rating BETWEEN 1 AND 5"),
)


def _existing_check_names(table: str) -> set[str]:
    inspector = sa.inspect(op.get_bind())
    return {
        c["name"] for c in inspector.get_check_constraints(table) if c.get("name")
    }


def upgrade() -> None:
    for table, name, condition in _CONSTRAINTS:
        # baseline 을 새로 실행한 DB 에는 이미 있다. 두 번 넣으면 중복된다.
        if name in _existing_check_names(table):
            continue
        with op.batch_alter_table(table) as batch_op:
            batch_op.create_check_constraint(name, condition)


def downgrade() -> None:
    for table, name, _ in _CONSTRAINTS:
        if name not in _existing_check_names(table):
            continue
        with op.batch_alter_table(table) as batch_op:
            batch_op.drop_constraint(name, type_="check")
