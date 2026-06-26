"""create audit_logs table for automatic field-level auditing

Revision ID: 0002
Revises: 0001
Create Date: 2026-06-25
"""
from alembic import op
import sqlalchemy as sa
from datetime import datetime

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "audit_logs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("account_id", sa.Integer(), index=True, nullable=True),
        sa.Column("operator", sa.String(50), default="system"),
        sa.Column("action", sa.String(20), nullable=False),
        sa.Column("entity_type", sa.String(50), nullable=False),
        sa.Column("entity_id", sa.Integer(), nullable=True),
        sa.Column("before_data", sa.JSON(), nullable=True),
        sa.Column("after_data", sa.JSON(), nullable=True),
        sa.Column("changed_fields", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(), default=datetime.now, index=True),
    )


def downgrade():
    op.drop_table("audit_logs")