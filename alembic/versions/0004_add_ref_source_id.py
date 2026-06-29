"""add ref_source_id to stock_moves

Revision ID: 0004_add_ref_source_id
Revises: 0003_add_stock_move_date
Create Date: 2026-06-29
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '0004_add_ref_source_id'
down_revision = '0003_add_stock_move_date'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('stock_moves', sa.Column('ref_source_id', sa.Integer(),
                  nullable=True, comment='原始单据ID（部分退货时记录原销售/采购单ID）'))
    op.create_index('ix_stock_moves_ref_source_id', 'stock_moves', ['ref_source_id'])


def downgrade():
    op.drop_index('ix_stock_moves_ref_source_id', table_name='stock_moves')
    op.drop_column('stock_moves', 'ref_source_id')
