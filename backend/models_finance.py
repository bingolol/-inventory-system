"""财务模块 ORM 模型

所有新会计系统模型集中在此文件，不混入老 models.py。
"""

from datetime import datetime, date
from decimal import Decimal
from sqlalchemy import (
    Column, Integer, String, Numeric, Boolean, DateTime, Date, Text,
    ForeignKey, JSON, UniqueConstraint, Index, event
)
from sqlalchemy.orm import Session, relationship
from database import Base
from utils import Q2


class Ledger(Base):
    """账本（新会计系统，与旧 accounts 表并存）"""
    __tablename__ = "ledgers"

    id            = Column(Integer, primary_key=True)
    name          = Column(String(100), nullable=False)
    type          = Column(String(20), nullable=False)       # company / personal
    code          = Column(String(50), unique=True)
    taxpayer_type_l3 = Column(String(20), info={"tier":"L3","source":"policy"})                       # [L3-政策] small_scale / general
    created_at    = Column(DateTime, default=datetime.now)


class LedgerAccount(Base):
    """会计科目（所有科目在此定义，余额仅叶子科目拥有）"""
    __tablename__ = "ledger_accounts"

    id            = Column(Integer, primary_key=True)
    ledger_id     = Column(Integer, ForeignKey("ledgers.id"), nullable=False, index=True)
    code          = Column(String(20), nullable=False)
    name          = Column(String(100), nullable=False)
    account_type  = Column(String(30), nullable=False)       # asset/liability/equity/income/expense
    parent_id     = Column(Integer, ForeignKey("ledger_accounts.id"))
    is_leaf       = Column(Boolean, default=True)
    is_active     = Column(Boolean, default=True)
    currency      = Column(String(10), default='CNY')

    created_at    = Column(DateTime, default=datetime.now)
    updated_at    = Column(DateTime, default=datetime.now, onupdate=datetime.now)

    __table_args__ = (
        UniqueConstraint("ledger_id", "code", name="uq_ledger_account_code"),
    )


class LedgerAccountBalance(Base):
    """科目余额（仅叶子科目 is_leaf=True 才有记录）"""
    __tablename__ = "ledger_account_balances"

    id                = Column(Integer, primary_key=True)
    ledger_account_id = Column(Integer, ForeignKey("ledger_accounts.id"),
                                nullable=False, unique=True, index=True)
    balance_l4        = Column(Numeric(14, 2), default=Decimal("0"), info={"tier":"L4","source":"derived"})
    debit_total_l4    = Column(Numeric(14, 2), default=Decimal("0"), info={"tier":"L4","source":"derived"})
    credit_total_l4   = Column(Numeric(14, 2), default=Decimal("0"), info={"tier":"L4","source":"derived"})

    created_at        = Column(DateTime, default=datetime.now)
    updated_at        = Column(DateTime, default=datetime.now, onupdate=datetime.now)


class AccountJournal(Base):
    """日记账"""
    __tablename__ = "account_journals"

    id                 = Column(Integer, primary_key=True)
    ledger_id          = Column(Integer, ForeignKey("ledgers.id"), nullable=False, index=True)
    name               = Column(String(50), nullable=False)
    code               = Column(String(20), nullable=False)
    journal_type       = Column(String(20), nullable=False)
    default_account_id = Column(Integer, ForeignKey("ledger_accounts.id"))

    __table_args__ = (
        UniqueConstraint("ledger_id", "code", name="uq_journal_code"),
    )


class AccountMove(Base):
    """会计凭证"""
    __tablename__ = "account_moves"

    id              = Column(Integer, primary_key=True)
    ledger_id       = Column(Integer, ForeignKey("ledgers.id"), nullable=False, index=True)
    journal_id      = Column(Integer, ForeignKey("account_journals.id"))
    name            = Column(String(30))
    move_type       = Column(String(20), nullable=False)
    date_l1         = Column(Date, nullable=False, info={"tier":"L1","source":"external"})
    state           = Column(String(10), default='draft')
    ref             = Column(String(200))

    source_model    = Column(String(50))
    source_id       = Column(Integer)

    amount_total_l2   = Column(Numeric(14, 2), default=Decimal("0"), info={"tier":"L2","source":"engine"})
    amount_untaxed_l2 = Column(Numeric(14, 2), default=Decimal("0"), info={"tier":"L2","source":"engine"})
    amount_tax_l2     = Column(Numeric(14, 2), default=Decimal("0"), info={"tier":"L2","source":"engine"})

    operator_id     = Column(Integer)
    posted_at       = Column(DateTime)

    reversed_entry_id = Column(Integer)
    is_reversal     = Column(Boolean, default=False)

    created_at      = Column(DateTime, default=datetime.now)
    updated_at      = Column(DateTime, default=datetime.now, onupdate=datetime.now)

    line_ids        = relationship("AccountMoveLine", back_populates="move",
                                   cascade="all, delete-orphan")

    __table_args__ = (
        Index("ix_move_date", "date_l1"),
        Index("ix_move_source", "source_model", "source_id"),
    )


class AccountMoveLine(Base):
    """凭证分录行"""
    __tablename__ = "account_move_lines"

    id                = Column(Integer, primary_key=True)
    move_id           = Column(Integer, ForeignKey("account_moves.id"), nullable=False, index=True)
    ledger_account_id = Column(Integer, ForeignKey("ledger_accounts.id"), nullable=False, index=True)

    debit_l2          = Column(Numeric(14, 2), default=Decimal("0"), info={"tier":"L2","source":"engine"})
    credit_l2         = Column(Numeric(14, 2), default=Decimal("0"), info={"tier":"L2","source":"engine"})

    amount_currency_l2 = Column(Numeric(14, 2), default=Decimal("0"), info={"tier":"L2","source":"engine"})
    currency_id       = Column(Integer)

    name              = Column(String(200))
    partner_id        = Column(Integer, index=True)
    partner_type      = Column(String(20))
    product_id        = Column(Integer)
    display_type      = Column(String(20))

    reconciled        = Column(Boolean, default=False)
    amount_residual_l2 = Column(Numeric(14, 2), default=Decimal("0"), info={"tier":"L2","source":"engine"})

    move              = relationship("AccountMove", back_populates="line_ids")

    __table_args__ = (
        Index("ix_line_partner", "partner_id", "partner_type"),
    )


class AccountPartialReconcile(Base):
    """核销记录"""
    __tablename__ = "account_partial_reconciles"

    id              = Column(Integer, primary_key=True)
    ledger_id       = Column(Integer, ForeignKey("ledgers.id"), nullable=False)

    debit_move_id   = Column(Integer, ForeignKey("account_move_lines.id"), nullable=False)
    credit_move_id  = Column(Integer, ForeignKey("account_move_lines.id"), nullable=False)

    amount_l2          = Column(Numeric(14, 2), nullable=False, info={"tier":"L2","source":"engine"})
    amount_currency_l2 = Column(Numeric(14, 2), default=Decimal("0"), info={"tier":"L2","source":"engine"})

    created_at      = Column(DateTime, default=datetime.now)


class AccountPeriod(Base):
    """会计期间"""
    __tablename__ = "account_periods"

    id              = Column(Integer, primary_key=True)
    ledger_id       = Column(Integer, ForeignKey("ledgers.id"), nullable=False)
    name            = Column(String(20))
    date_start      = Column(Date, nullable=False)
    date_end        = Column(Date, nullable=False)
    state           = Column(String(10), default='draft')

    cost_closed     = Column(Boolean, default=False)
    profit_closed   = Column(Boolean, default=False)
    depreciation_done = Column(Boolean, default=False)
    estimate_reversed = Column(Boolean, default=False)

    __table_args__ = (
        UniqueConstraint("ledger_id", "name", name="uq_period_name"),
    )


class VoucherSequence(Base):
    """凭证号序列"""
    __tablename__ = "voucher_sequences"

    id           = Column(Integer, primary_key=True)
    ledger_id    = Column(Integer, ForeignKey("ledgers.id"), nullable=False)
    journal_code = Column(String(20), nullable=False)
    year         = Column(Integer, nullable=False)
    last_number  = Column(Integer, default=0)

    __table_args__ = (
        UniqueConstraint("ledger_id", "journal_code", "year", name="uq_voucher_seq"),
    )


def generate_voucher_number(db: Session, ledger_id: int, journal_code: str, date_str: str) -> str:
    """原子性生成凭证号（悲观锁，允许断号）"""
    year = int(date_str[:4])

    seq = db.query(VoucherSequence).filter(
        VoucherSequence.ledger_id == ledger_id,
        VoucherSequence.journal_code == journal_code,
        VoucherSequence.year == year,
    ).with_for_update().first()

    if not seq:
        seq = VoucherSequence(
            ledger_id=ledger_id,
            journal_code=journal_code,
            year=year,
            last_number=0,
        )
        db.add(seq)
        db.flush()

    seq.last_number += 1
    return f"{journal_code}-{year}-{seq.last_number:04d}"


class SaleReturn(Base):
    """销售退货"""
    __tablename__ = "sale_returns"

    id                = Column(Integer, primary_key=True)
    ledger_id         = Column(Integer, ForeignKey("ledgers.id"), nullable=False)
    return_no         = Column(String(30), nullable=False)
    original_order_id = Column(Integer, ForeignKey("sale_orders.id"))
    customer_id       = Column(Integer, ForeignKey("customers.id"))
    total_with_tax_l1 = Column(Numeric(12, 2), nullable=False, info={"tier":"L1","source":"external"})
    return_date_l1    = Column(DateTime, nullable=False, info={"tier":"L1","source":"external"})
    reason            = Column(Text)
    status            = Column(String(20), default='draft')
    refund_status     = Column(String(20), default='pending')
    receipt_id        = Column(Integer)
    move_id           = Column(Integer, ForeignKey("account_moves.id"))

    items             = relationship("SaleReturnItem", back_populates="return_order")


class SaleReturnItem(Base):
    """销售退货明细"""
    __tablename__ = "sale_return_items"

    id         = Column(Integer, primary_key=True)
    return_id  = Column(Integer, ForeignKey("sale_returns.id"), nullable=False)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False)
    quantity_l1 = Column(Integer, nullable=False, info={"tier":"L1","source":"external"})
    unit_price_l1 = Column(Numeric(12, 6), nullable=False, info={"tier":"L1","source":"external"})
    tax_rate_l1   = Column(Numeric(12, 2), nullable=False, info={"tier":"L1","source":"external"})
    total_price_l1 = Column(Numeric(12, 2), nullable=False, info={"tier":"L1","source":"external"})

    return_order = relationship("SaleReturn", back_populates="items")


class PurchaseReturn(Base):
    """采购退货"""
    __tablename__ = "purchase_returns"

    id                = Column(Integer, primary_key=True)
    ledger_id         = Column(Integer, ForeignKey("ledgers.id"), nullable=False)
    return_no         = Column(String(30), nullable=False)
    original_order_id = Column(Integer, ForeignKey("purchase_orders.id"))
    supplier_id       = Column(Integer, ForeignKey("suppliers.id"))
    total_with_tax_l1 = Column(Numeric(12, 2), nullable=False, info={"tier":"L1","source":"external"})
    return_date_l1    = Column(DateTime, nullable=False, info={"tier":"L1","source":"external"})
    reason            = Column(Text)
    status            = Column(String(20), default='draft')
    refund_status     = Column(String(20), default='pending')
    payment_id        = Column(Integer)
    move_id           = Column(Integer, ForeignKey("account_moves.id"))


class BadDebt(Base):
    """坏账记录"""
    __tablename__ = "bad_debts"

    id                = Column(Integer, primary_key=True)
    ledger_id         = Column(Integer, ForeignKey("ledgers.id"), nullable=False)
    partner_id        = Column(Integer, nullable=False)
    partner_type      = Column(String(20), nullable=False)
    original_amount_l1 = Column(Numeric(14, 2), nullable=False, info={"tier":"L1","source":"external"})
    bad_amount_l1      = Column(Numeric(14, 2), nullable=False, info={"tier":"L1","source":"external"})
    reason            = Column(Text, nullable=False)
    status            = Column(String(20), default='pending')

    # 小企业准则不计提坏账准备,只有 writeoff 核销凭证
    writeoff_move_id  = Column(Integer, ForeignKey("account_moves.id"))

    created_at        = Column(DateTime, default=datetime.now)


class PurchaseEstimate(Base):
    """暂估入库"""
    __tablename__ = "purchase_estimates"

    id              = Column(Integer, primary_key=True)
    ledger_id       = Column(Integer, ForeignKey("ledgers.id"), nullable=False)
    supplier_id     = Column(Integer, ForeignKey("suppliers.id"), nullable=False)
    estimate_no     = Column(String(30), nullable=False)
    estimate_date_l1 = Column(Date, nullable=False, info={"tier":"L1","source":"external"})
    total_amount_l1  = Column(Numeric(12, 2), nullable=False, info={"tier":"L1","source":"external"})
    status          = Column(String(20), default='estimated')

    estimate_move_id = Column(Integer, ForeignKey("account_moves.id"))
    reverse_move_id  = Column(Integer, ForeignKey("account_moves.id"))
    invoice_id      = Column(Integer)

    items           = relationship("PurchaseEstimateItem", back_populates="estimate")


class PurchaseEstimateItem(Base):
    """暂估入库明细"""
    __tablename__ = "purchase_estimate_items"

    id         = Column(Integer, primary_key=True)
    estimate_id = Column(Integer, ForeignKey("purchase_estimates.id"), nullable=False)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False)
    quantity_l1 = Column(Integer, nullable=False, info={"tier":"L1","source":"external"})
    unit_price_l1 = Column(Numeric(12, 6), nullable=False, info={"tier":"L1","source":"external"})
    total_price_l1 = Column(Numeric(12, 2), nullable=False, info={"tier":"L1","source":"external"})

    estimate   = relationship("PurchaseEstimate", back_populates="items")


# ═══════════════════════════════════════════════════════════
# 税务申报声明（L1 外部输入）
# ═══════════════════════════════════════════════════════════


class VATDeclaration(Base):
    """增值税申报声明（L1）— 用户提交时锁定快照"""
    __tablename__ = "vat_declarations"

    id                  = Column(Integer, primary_key=True)
    account_id          = Column(Integer, nullable=False, index=True)
    period              = Column(String(10), nullable=False)
    taxpayer_type       = Column(String(20), nullable=False)
    total_revenue       = Column(Numeric(14, 2), default=Decimal("0"))
    output_tax          = Column(Numeric(14, 2), default=Decimal("0"))
    input_tax           = Column(Numeric(14, 2), default=Decimal("0"))
    vat_payable         = Column(Numeric(14, 2), default=Decimal("0"))
    carry_forward       = Column(Numeric(14, 2), default=Decimal("0"))
    period_start        = Column(Date, nullable=False)
    period_end          = Column(Date, nullable=False)
    snapshot_at         = Column(DateTime, default=datetime.now)
    created_at          = Column(DateTime, default=datetime.now)

    __table_args__ = (
        UniqueConstraint("account_id", "period", name="uq_vat_declaration_period"),
    )


class SurchargeDeclaration(Base):
    """附加税申报声明（L1）— 用户录入的实际值，录入即过账"""
    __tablename__ = "surcharge_declarations"

    id                        = Column(Integer, primary_key=True)
    account_id                = Column(Integer, nullable=False, index=True)
    period                    = Column(String(10), nullable=False)
    vat_declaration_id        = Column(Integer, nullable=False)
    vat_payable               = Column(Numeric(14, 2), default=Decimal("0"))
    urban_construction_tax    = Column(Numeric(14, 2), default=Decimal("0"))
    education_surcharge       = Column(Numeric(14, 2), default=Decimal("0"))
    local_education_surcharge = Column(Numeric(14, 2), default=Decimal("0"))
    total                     = Column(Numeric(14, 2), default=Decimal("0"))
    declared_at               = Column(DateTime, default=datetime.now)
    notes                     = Column(Text, default="")
    status                    = Column(String(20), default="posted")
    created_at                = Column(DateTime, default=datetime.now)

    __table_args__ = (
        UniqueConstraint("account_id", "period", name="uq_surcharge_declaration_period"),
    )


# ═══════════════════════════════════════════════════════════
# before_update 事件：会计凭证真相源禁止 UPDATE
# ═══════════════════════════════════════════════════════════

@event.listens_for(AccountMove, 'before_update')
def prevent_account_move_update(mapper, connection, target):
    from errors import BusinessError, ErrorCode
    raise BusinessError(
        code=ErrorCode.DATA_INTEGRITY_ERROR,
        data={"details": "AccountMove 是会计凭证真相源，一经生成严禁修改"}
    )


# AccountMoveLine 需核销时更新 amount_residual/reconciled，不做全拦
