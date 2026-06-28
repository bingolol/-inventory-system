"""create finance tables + seed accounts

Revision ID: 0001
Revises: None
Create Date: 2026-06-23
"""
from alembic import op
import sqlalchemy as sa
from datetime import datetime

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    conn = op.get_bind()

    # ─── 建表 ───────────────────────────────────────────────

    op.create_table(
        "ledgers",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("type", sa.String(20), nullable=False),
        sa.Column("code", sa.String(50), unique=True),
        sa.Column("taxpayer_type", sa.String(20)),
        sa.Column("created_at", sa.DateTime(), default=datetime.now),
    )

    op.create_table(
        "ledger_accounts",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("ledger_id", sa.Integer(), sa.ForeignKey("ledgers.id"), nullable=False, index=True),
        sa.Column("code", sa.String(20), nullable=False),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("account_type", sa.String(30), nullable=False),
        sa.Column("parent_id", sa.Integer(), sa.ForeignKey("ledger_accounts.id")),
        sa.Column("is_leaf", sa.Boolean(), default=True),
        sa.Column("is_active", sa.Boolean(), default=True),
        sa.Column("currency", sa.String(10), default="CNY"),
        sa.Column("created_at", sa.DateTime(), default=datetime.now),
        sa.Column("updated_at", sa.DateTime(), default=datetime.now),
        sa.UniqueConstraint("ledger_id", "code", name="uq_ledger_account_code"),
    )

    op.create_table(
        "ledger_account_balances",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("ledger_account_id", sa.Integer(), sa.ForeignKey("ledger_accounts.id"),
                  nullable=False, unique=True, index=True),
        sa.Column("balance", sa.Numeric(14, 2), default=0),
        sa.Column("debit_total", sa.Numeric(14, 2), default=0),
        sa.Column("credit_total", sa.Numeric(14, 2), default=0),
        sa.Column("created_at", sa.DateTime(), default=datetime.now),
        sa.Column("updated_at", sa.DateTime(), default=datetime.now),
    )

    op.create_table(
        "account_journals",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("ledger_id", sa.Integer(), sa.ForeignKey("ledgers.id"), nullable=False, index=True),
        sa.Column("name", sa.String(50), nullable=False),
        sa.Column("code", sa.String(20), nullable=False),
        sa.Column("journal_type", sa.String(20), nullable=False),
        sa.Column("default_account_id", sa.Integer(), sa.ForeignKey("ledger_accounts.id")),
        sa.UniqueConstraint("ledger_id", "code", name="uq_journal_code"),
    )

    op.create_table(
        "account_moves",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("ledger_id", sa.Integer(), sa.ForeignKey("ledgers.id"), nullable=False, index=True),
        sa.Column("journal_id", sa.Integer(), sa.ForeignKey("account_journals.id")),
        sa.Column("name", sa.String(30)),
        sa.Column("move_type", sa.String(20), nullable=False),
        sa.Column("date", sa.Date(), nullable=False),
        sa.Column("state", sa.String(10), default="draft"),
        sa.Column("ref", sa.String(200)),
        sa.Column("source_model", sa.String(50)),
        sa.Column("source_id", sa.Integer()),
        sa.Column("amount_total", sa.Numeric(14, 2), default=0),
        sa.Column("amount_untaxed", sa.Numeric(14, 2), default=0),
        sa.Column("amount_tax", sa.Numeric(14, 2), default=0),
        sa.Column("operator_id", sa.Integer()),
        sa.Column("posted_at", sa.DateTime()),
        sa.Column("reversed_entry_id", sa.Integer()),
        sa.Column("is_reversal", sa.Boolean(), default=False),
        sa.Column("created_at", sa.DateTime(), default=datetime.now),
        sa.Column("updated_at", sa.DateTime(), default=datetime.now),
        sa.Index("ix_move_date", "date"),
        sa.Index("ix_move_source", "source_model", "source_id"),
    )

    op.create_table(
        "account_move_lines",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("move_id", sa.Integer(), sa.ForeignKey("account_moves.id"), nullable=False, index=True),
        sa.Column("ledger_account_id", sa.Integer(), sa.ForeignKey("ledger_accounts.id"),
                  nullable=False, index=True),
        sa.Column("debit", sa.Numeric(14, 2), default=0),
        sa.Column("credit", sa.Numeric(14, 2), default=0),
        sa.Column("amount_currency", sa.Numeric(14, 2), default=0),
        sa.Column("currency_id", sa.Integer()),
        sa.Column("name", sa.String(200)),
        sa.Column("partner_id", sa.Integer(), index=True),
        sa.Column("partner_type", sa.String(20)),
        sa.Column("product_id", sa.Integer()),
        sa.Column("display_type", sa.String(20)),
        sa.Column("reconciled", sa.Boolean(), default=False),
        sa.Column("amount_residual", sa.Numeric(14, 2), default=0),
        sa.Index("ix_line_partner", "partner_id", "partner_type"),
    )

    op.create_table(
        "account_partial_reconciles",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("ledger_id", sa.Integer(), sa.ForeignKey("ledgers.id"), nullable=False),
        sa.Column("debit_move_id", sa.Integer(), sa.ForeignKey("account_move_lines.id"), nullable=False),
        sa.Column("credit_move_id", sa.Integer(), sa.ForeignKey("account_move_lines.id"), nullable=False),
        sa.Column("amount", sa.Numeric(14, 2), nullable=False),
        sa.Column("amount_currency", sa.Numeric(14, 2), default=0),
        sa.Column("created_at", sa.DateTime(), default=datetime.now),
    )

    op.create_table(
        "account_periods",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("ledger_id", sa.Integer(), sa.ForeignKey("ledgers.id"), nullable=False),
        sa.Column("name", sa.String(20)),
        sa.Column("date_start", sa.Date(), nullable=False),
        sa.Column("date_end", sa.Date(), nullable=False),
        sa.Column("state", sa.String(10), default="draft"),
        sa.Column("cost_closed", sa.Boolean(), default=False),
        sa.Column("profit_closed", sa.Boolean(), default=False),
        sa.Column("depreciation_done", sa.Boolean(), default=False),
        sa.Column("estimate_reversed", sa.Boolean(), default=False),
        sa.UniqueConstraint("ledger_id", "name", name="uq_period_name"),
    )

    op.create_table(
        "voucher_sequences",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("ledger_id", sa.Integer(), sa.ForeignKey("ledgers.id"), nullable=False),
        sa.Column("journal_code", sa.String(20), nullable=False),
        sa.Column("year", sa.Integer(), nullable=False),
        sa.Column("last_number", sa.Integer(), default=0),
        sa.UniqueConstraint("ledger_id", "journal_code", "year", name="uq_voucher_seq"),
    )

    op.create_table(
        "sale_returns",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("ledger_id", sa.Integer(), sa.ForeignKey("ledgers.id"), nullable=False),
        sa.Column("return_no", sa.String(30), nullable=False),
        sa.Column("original_order_id", sa.Integer()),
        sa.Column("customer_id", sa.Integer()),
        sa.Column("total_with_tax", sa.Numeric(12, 2), nullable=False),
        sa.Column("return_date", sa.DateTime(), nullable=False),
        sa.Column("reason", sa.Text()),
        sa.Column("status", sa.String(20), default="draft"),
        sa.Column("refund_status", sa.String(20), default="pending"),
        sa.Column("receipt_id", sa.Integer()),
        sa.Column("move_id", sa.Integer(), sa.ForeignKey("account_moves.id")),
    )

    op.create_table(
        "sale_return_items",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("return_id", sa.Integer(), sa.ForeignKey("sale_returns.id"), nullable=False),
        sa.Column("product_id", sa.Integer(), nullable=False),
        sa.Column("quantity", sa.Integer(), nullable=False),
        sa.Column("unit_price", sa.Numeric(12, 6), nullable=False),
        sa.Column("tax_rate", sa.Numeric(12, 2), nullable=False),
        sa.Column("total_price", sa.Numeric(12, 2), nullable=False),
    )

    op.create_table(
        "purchase_returns",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("ledger_id", sa.Integer(), sa.ForeignKey("ledgers.id"), nullable=False),
        sa.Column("return_no", sa.String(30), nullable=False),
        sa.Column("original_order_id", sa.Integer()),
        sa.Column("supplier_id", sa.Integer()),
        sa.Column("total_with_tax", sa.Numeric(12, 2), nullable=False),
        sa.Column("return_date", sa.DateTime(), nullable=False),
        sa.Column("reason", sa.Text()),
        sa.Column("status", sa.String(20), default="draft"),
        sa.Column("refund_status", sa.String(20), default="pending"),
        sa.Column("payment_id", sa.Integer()),
        sa.Column("move_id", sa.Integer(), sa.ForeignKey("account_moves.id")),
    )

    op.create_table(
        "bad_debts",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("ledger_id", sa.Integer(), sa.ForeignKey("ledgers.id"), nullable=False),
        sa.Column("partner_id", sa.Integer(), nullable=False),
        sa.Column("partner_type", sa.String(20), nullable=False),
        sa.Column("original_amount", sa.Numeric(14, 2), nullable=False),
        sa.Column("bad_amount", sa.Numeric(14, 2), nullable=False),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("status", sa.String(20), default="pending"),
        sa.Column("provision_move_id", sa.Integer(), sa.ForeignKey("account_moves.id")),
        sa.Column("writeoff_move_id", sa.Integer(), sa.ForeignKey("account_moves.id")),
        sa.Column("created_at", sa.DateTime(), default=datetime.now),
    )

    op.create_table(
        "purchase_estimates",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("ledger_id", sa.Integer(), sa.ForeignKey("ledgers.id"), nullable=False),
        sa.Column("supplier_id", sa.Integer(), nullable=False),
        sa.Column("estimate_no", sa.String(30), nullable=False),
        sa.Column("estimate_date", sa.Date(), nullable=False),
        sa.Column("total_amount", sa.Numeric(12, 2), nullable=False),
        sa.Column("status", sa.String(20), default="estimated"),
        sa.Column("estimate_move_id", sa.Integer(), sa.ForeignKey("account_moves.id")),
        sa.Column("reverse_move_id", sa.Integer(), sa.ForeignKey("account_moves.id")),
        sa.Column("invoice_id", sa.Integer()),
    )

    op.create_table(
        "purchase_estimate_items",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("estimate_id", sa.Integer(), sa.ForeignKey("purchase_estimates.id"), nullable=False),
        sa.Column("product_id", sa.Integer(), nullable=False),
        sa.Column("quantity", sa.Integer(), nullable=False),
        sa.Column("unit_price", sa.Numeric(12, 6), nullable=False),
        sa.Column("total_price", sa.Numeric(12, 2), nullable=False),
    )

    # NOTE: 种子数据已移至 bootstrap.py，本迁移只负责 DDL


def downgrade():
    op.drop_table("purchase_estimate_items")
    op.drop_table("purchase_estimates")
    op.drop_table("bad_debts")
    op.drop_table("purchase_returns")
    op.drop_table("sale_return_items")
    op.drop_table("sale_returns")
    op.drop_table("voucher_sequences")
    op.drop_table("account_periods")
    op.drop_table("account_partial_reconciles")
    op.drop_table("account_move_lines")
    op.drop_table("account_moves")
    op.drop_table("account_journals")
    op.drop_table("ledger_account_balances")
    op.drop_table("ledger_accounts")
    op.drop_table("ledgers")
