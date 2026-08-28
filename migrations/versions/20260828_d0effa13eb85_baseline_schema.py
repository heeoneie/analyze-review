"""baseline schema

지금까지 create_all 이 만들어 오던 스키마를 그대로 옮긴 기준점이다.
create_all 로 이미 테이블이 생긴 DB 도 그대로 받아들일 수 있어야 한다. 그래서
이 리비전만 예외적으로 "있으면 건너뛴다". 덕분에 새 DB 든 기존 DB 든
`alembic upgrade head` 한 줄로 끝나고, stamp 를 사람이 손으로 칠 일이 없다.
이후 리비전은 이런 방어를 하지 않는다 — 여기서부터는 이력이 정확하다.

Revision ID: d0effa13eb85
Revises:
Create Date: 2026-08-28
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = 'd0effa13eb85'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# create_all 시절 DB 를 흡수하기 위한 예외 처리. 새 마이그레이션에 베끼지 말 것.
def _existing_tables() -> set[str]:
    return set(sa.inspect(op.get_bind()).get_table_names())


def upgrade() -> None:
    existing = _existing_tables()

    if 'nodes' not in existing:
        op.create_table('nodes',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('name', sa.String(length=512), nullable=False),
        sa.Column('normalized_name', sa.String(length=512), nullable=False),
        sa.Column('type', sa.String(length=64), nullable=False),
        sa.Column('severity_score', sa.Float(), nullable=False),
        sa.Column('case_id', sa.String(length=32), nullable=True),
        sa.Column('estimated_loss_usd', sa.Integer(), nullable=False),
        sa.Column('source', sa.String(length=256), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('last_seen_at', sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint('estimated_loss_usd >= 0', name='ck_node_estimated_loss_nonneg'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('normalized_name', 'type', name='uq_node_norm_name_type')
        )
    if 'reviews' not in existing:
        op.create_table('reviews',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('source', sa.String(length=64), nullable=False),
        sa.Column('product_url', sa.String(length=1024), nullable=True),
        sa.Column('rating', sa.Integer(), nullable=False),
        sa.Column('title', sa.String(length=512), nullable=True),
        sa.Column('body', sa.String(length=4096), nullable=False),
        sa.Column('severity', sa.Float(), nullable=False),
        sa.Column('risk_label', sa.String(length=128), nullable=True),
        sa.Column('ingested_at', sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint('rating BETWEEN 1 AND 5', name='ck_reviews_rating_1_5'),
        sa.PrimaryKeyConstraint('id')
        )
    if 'users' not in existing:
        op.create_table('users',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('kakao_id', sa.String(length=64), nullable=False),
        sa.Column('nickname', sa.String(length=128), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('last_login_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('kakao_id')
        )
    if 'edges' not in existing:
        op.create_table('edges',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('source_node_id', sa.Integer(), nullable=False),
        sa.Column('target_node_id', sa.Integer(), nullable=False),
        sa.Column('relationship_type', sa.String(length=128), nullable=False),
        sa.Column('weight', sa.Float(), nullable=False),
        sa.Column('source', sa.String(length=256), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('last_seen_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['source_node_id'], ['nodes.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['target_node_id'], ['nodes.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('source_node_id', 'target_node_id', 'relationship_type', name='uq_edge_src_tgt_rel')
        )
    if 'stores' not in existing:
        op.create_table('stores',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('owner_user_id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=256), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['owner_user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
        )
    if 'reply_samples' not in existing:
        op.create_table('reply_samples',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('store_id', sa.Integer(), nullable=False),
        sa.Column('origin', sa.String(length=16), nullable=False),
        sa.Column('review_body', sa.Text(), nullable=False),
        sa.Column('rating', sa.Integer(), nullable=False),
        sa.Column('menu', sa.String(length=512), nullable=True),
        sa.Column('generated_reply', sa.Text(), nullable=True),
        sa.Column('final_reply', sa.Text(), nullable=True),
        sa.Column('was_edited', sa.Boolean(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('finalized_at', sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint("origin IN ('onboarding', 'generated', 'edited')", name='ck_reply_samples_origin'),
        sa.CheckConstraint('rating BETWEEN 1 AND 5', name='ck_reply_samples_rating_1_5'),
        sa.ForeignKeyConstraint(['store_id'], ['stores.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
        )


def downgrade() -> None:
    # 자식 테이블부터. 반대로 지우면 FK 참조가 남아 실패한다.
    op.drop_table('reply_samples')
    op.drop_table('stores')
    op.drop_table('edges')
    op.drop_table('users')
    op.drop_table('reviews')
    op.drop_table('nodes')
