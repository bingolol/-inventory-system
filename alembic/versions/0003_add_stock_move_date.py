"""add move_date column to stock_moves

Revision ID: 0003
Revises: 0002
Create Date: 2026-06-28
"""
from alembic import op
import sqlalchemy as sa

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("stock_moves", sa.Column("move_date", sa.DateTime(), nullable=True))


def downgrade():
    op.drop_column("stock_moves", "move_date")
