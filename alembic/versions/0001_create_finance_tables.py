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

    # ─── 初始化默认账本 ─────────────────────────────────────
    # 如果 ledgers 表为空，插入一个与现有 accounts 表对应的默认账本
    row_count = conn.execute(sa.text("SELECT COUNT(*) FROM ledgers")).scalar()
    if row_count == 0:
        conn.execute(
            sa.text("""
                INSERT INTO ledgers (name, type, code, taxpayer_type, created_at)
                VALUES ('默认账本', 'company', 'default', 'small_scale', :now)
            """),
            {"now": now},
        )

    # ─── 科目初始化（使用动态 ledger_id） ───────────────────
    # 🚨 禁止硬编码 ledger_id=1。使用子查询动态获取首个账本 ID。

    ledger_subquery = "(SELECT id FROM ledgers ORDER BY id LIMIT 1)"

    # 资产类
    asset_accounts = [
        ("1001", "库存现金", "asset"),
        ("1002", "银行存款", "asset"),
        ("1122", "应收账款", "asset_receivable"),
        ("1123", "预付账款", "asset_prepaid"),
        ("1221", "其他应收款", "asset"),
        ("1231", "坏账准备", "asset_contra"),
        ("1405", "库存商品", "asset"),
        ("1601", "固定资产", "asset"),
        ("1602", "累计折旧", "asset_contra"),
        ("1701", "无形资产", "asset"),
        ("1702", "累计摊销", "asset_contra"),
    ]
    # 负债类
    liability_accounts = [
        ("2202", "应付账款", "liability_payable"),
        ("2203", "预收账款", "liability_advance"),
        ("2211", "应付职工薪酬", "liability"),
        ("2221", "应交税费", "liability"),
        ("222101", "应交增值税-销项税额", "liability"),
        ("222102", "应交增值税-进项税额", "liability"),
        ("2241", "其他应付款", "liability"),
    ]
    # 权益类
    equity_accounts = [
        ("4001", "实收资本", "equity"),
        ("4101", "盈余公积", "equity"),
        ("4103", "本年利润", "equity"),
        ("4104", "利润分配", "equity"),
    ]
    # 损益类
    income_accounts = [
        ("6001", "主营业务收入", "income"),
        ("6051", "其他业务收入", "income"),
    ]
    expense_accounts = [
        ("6401", "主营业务成本", "expense"),
        ("6403", "税金及附加", "expense"),
        ("6601", "管理费用", "expense"),
        ("6602", "销售费用", "expense"),
        ("6603", "财务费用", "expense"),
        ("6701", "资产减值损失", "expense"),
        ("6711", "营业外支出", "expense"),
        ("6801", "所得税费用", "expense"),
    ]

    all_accounts = (
        asset_accounts + liability_accounts + equity_accounts
        + income_accounts + expense_accounts
    )
    # 收集插入的科目 ID，为后续插入余额做准备
    account_ids = {}

    for code, name, acct_type in all_accounts:
        conn.execute(
            sa.text(f"""
                INSERT INTO ledger_accounts (ledger_id, code, name, account_type, is_leaf, created_at, updated_at)
                VALUES ({ledger_subquery}, :code, :name, :type, 1, :now, :now)
            """),
            {"code": code, "name": name, "type": acct_type, "now": now},
        )

    # 为每个叶子科目创建余额记录（初始余额为 0）
    conn.execute(
        sa.text("""
            INSERT INTO ledger_account_balances (ledger_account_id, balance, debit_total, credit_total)
            SELECT id, 0, 0, 0 FROM ledger_accounts WHERE is_leaf = 1
        """)
    )


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
