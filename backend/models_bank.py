"""银行对账模型"""
from datetime import datetime
from decimal import Decimal
from sqlalchemy import Column, Integer, String, Numeric, Boolean, DateTime, Date, ForeignKey, JSON, Text
from database import Base


class BankStatement(Base):
    __tablename__ = "bank_statements"
    id = Column(Integer, primary_key=True, index=True)
    bank_account_id = Column(Integer, ForeignKey("bank_accounts.id"), nullable=False)
    account_id = Column(Integer, ForeignKey("accounts.id"), nullable=False)
    period_start = Column(Date, nullable=False)
    period_end = Column(Date, nullable=False)
    opening_balance_l1 = Column(Numeric(14, 2), default=Decimal("0"), info={"tier":"L1","source":"external"})
    closing_balance_l1 = Column(Numeric(14, 2), default=Decimal("0"), info={"tier":"L1","source":"external"})
    status = Column(String(20), default="draft")
    created_at = Column(DateTime, default=datetime.now)


class BankStatementLine(Base):
    __tablename__ = "bank_statement_lines"
    id = Column(Integer, primary_key=True, index=True)
    statement_id = Column(Integer, ForeignKey("bank_statements.id"), nullable=False, index=True)
    transaction_date_l1 = Column(Date, nullable=False, info={"tier":"L1","source":"external"})
    description = Column(String(200))
    amount_l1 = Column(Numeric(14, 2), nullable=False, info={"tier":"L1","source":"external"})  # 正=收入 负=支出
    is_fee = Column(Boolean, default=False)
    match_group_id = Column(Integer, nullable=True)
    matched_tx_ids = Column(JSON, nullable=True)


class BankReconciliation(Base):
    __tablename__ = "bank_reconciliations"
    id = Column(Integer, primary_key=True, index=True)
    bank_account_id = Column(Integer, ForeignKey("bank_accounts.id"), nullable=False)
    account_id = Column(Integer, ForeignKey("accounts.id"), nullable=False, index=True)
    period = Column(String(7), nullable=False)  # YYYY-MM
    book_balance_l4 = Column(Numeric(14, 2), default=Decimal("0"), info={"tier":"L4","source":"derived"})
    statement_balance_l1 = Column(Numeric(14, 2), default=Decimal("0"), info={"tier":"L1","source":"external"})
    adjusted_book_l4 = Column(Numeric(14, 2), default=Decimal("0"), info={"tier":"L4","source":"derived"})
    adjusted_statement_l4 = Column(Numeric(14, 2), default=Decimal("0"), info={"tier":"L4","source":"derived"})
    balanced = Column(Boolean, default=False)
    status = Column(String(20), default="draft")  # draft/matching/balanced/confirmed
    confirmed_at = Column(DateTime, nullable=True)
    confirmed_by = Column(String(50), nullable=True)
    created_at = Column(DateTime, default=datetime.now)


class ReconciliationItem(Base):
    __tablename__ = "reconciliation_items"
    id = Column(Integer, primary_key=True, index=True)
    reconciliation_id = Column(Integer, ForeignKey("bank_reconciliations.id"), nullable=False, index=True)
    item_type = Column(String(30), nullable=False)
    # bank_received_not_book | bank_paid_not_book
    # book_received_not_bank | book_paid_not_bank | adjustment | seed
    source_ids = Column(JSON, nullable=True)
    source_dates = Column(JSON, nullable=True)
    amount_l2 = Column(Numeric(14, 2), nullable=False, info={"tier":"L2","source":"engine"})
    direction = Column(String(10), nullable=False)  # in / out
    match_group_id = Column(Integer, nullable=True)
    forced_match = Column(Boolean, default=False)
    resolved = Column(Boolean, default=False)
    resolved_in = Column(String(7), nullable=True)
    generated_move_id = Column(Integer, nullable=True)
    action = Column(String(20), nullable=True)
    notes = Column(Text, nullable=True)
