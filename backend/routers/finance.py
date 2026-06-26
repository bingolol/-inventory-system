"""财务管理查询 API — 只读，跨账本隔离"""
from datetime import date, datetime
from decimal import Decimal
from typing import Optional

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from database import get_db
from models_finance import (
    LedgerAccount, LedgerAccountBalance, AccountMove, AccountMoveLine,
)
from finance_integration import get_ledger_id
from engine_ledger import LedgerEngine
from engine_receivable import ReceivableEngine
from account_dep import get_account_id
from errors import BusinessError, ErrorCode


# ── 响应模型 ──

class AccountChartItem(BaseModel):
    id: int
    code: str
    name: str
    account_type: str
    parent_id: Optional[int] = None
    is_leaf: bool = True
    is_active: bool = True
    balance: Decimal = Decimal("0")

    model_config = {"from_attributes": True}


class AccountMoveSummary(BaseModel):
    id: int
    name: Optional[str] = None
    move_type: str
    date: date
    state: str = "draft"
    amount_total: Decimal = Decimal("0")
    source_model: Optional[str] = None
    source_id: Optional[int] = None
    is_reversal: bool = False
    created_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class AccountMoveLineOut(BaseModel):
    id: int
    account_code: str = ""
    account_name: str = ""
    debit: Decimal = Decimal("0")
    credit: Decimal = Decimal("0")
    partner_id: Optional[int] = None
    partner_type: Optional[str] = None
    amount_residual: Decimal = Decimal("0")
    reconciled: bool = False


class AccountMoveDetail(AccountMoveSummary):
    lines: list[AccountMoveLineOut] = []


class TrialBalanceRow(BaseModel):
    code: str
    name: str
    debit: Decimal = Decimal("0")
    credit: Decimal = Decimal("0")


class TrialBalanceReport(BaseModel):
    rows: list[TrialBalanceRow] = []
    total_debit: Decimal = Decimal("0")
    total_credit: Decimal = Decimal("0")
    balanced: bool = True


class PartnerBalanceOut(BaseModel):
    partner_id: int
    partner_type: str
    balance: Decimal = Decimal("0")
    account_type: Optional[str] = None
    aging: Optional[dict[str, Decimal]] = None

router = APIRouter()


@router.get("/accounts/chart")
def get_account_chart(
    db: Session = Depends(get_db),
    account_id: int = Depends(get_account_id),
):
    """获取当前账本的科目表（扁平列表，含实时余额）"""
    ledger_id = get_ledger_id(db, account_id)
    ledger_engine = LedgerEngine(db)

    accounts = db.query(LedgerAccount).filter(
        LedgerAccount.ledger_id == ledger_id,
    ).order_by(LedgerAccount.code).all()

    items = []
    for acct in accounts:
        balance = ledger_engine.get_balance(acct.id)
        items.append(AccountChartItem(
            id=acct.id,
            code=acct.code,
            name=acct.name,
            account_type=acct.account_type,
            parent_id=acct.parent_id,
            is_leaf=acct.is_leaf,
            is_active=acct.is_active,
            balance=balance,
        ))

    return {"items": items}


@router.get("/journal/moves")
def get_journal_moves(
    date_from: Optional[str] = Query(None, description="起始日期 YYYY-MM-DD"),
    date_to: Optional[str] = Query(None, description="截止日期 YYYY-MM-DD"),
    move_type: Optional[str] = Query(None, description="凭证类型: sale_order/purchase_order/receipt/payment/expense"),
    state: Optional[str] = Query(None, description="状态: draft/posted"),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    db: Session = Depends(get_db),
    account_id: int = Depends(get_account_id),
):
    """凭证列表（分页，支持日期/类型/状态过滤）"""
    ledger_id = get_ledger_id(db, account_id)

    query = db.query(AccountMove).filter(
        AccountMove.ledger_id == ledger_id
    )

    if date_from:
        query = query.filter(AccountMove.date >= date_from)
    if date_to:
        query = query.filter(AccountMove.date <= date_to)
    if move_type:
        query = query.filter(AccountMove.move_type == move_type)
    if state:
        query = query.filter(AccountMove.state == state)

    total = query.count()
    moves = query.order_by(
        AccountMove.date.desc(), AccountMove.id.desc()
    ).offset(skip).limit(limit).all()

    return {
        "total": total,
        "items": [AccountMoveSummary.model_validate(m) for m in moves],
    }


@router.get("/journal/moves/{move_id}")
def get_journal_move(
    move_id: int,
    db: Session = Depends(get_db),
    account_id: int = Depends(get_account_id),
):
    """凭证详情（含所有分录行 + 科目编码/名称）"""
    ledger_id = get_ledger_id(db, account_id)

    move = db.query(AccountMove).filter(
        AccountMove.id == move_id,
        AccountMove.ledger_id == ledger_id,
    ).first()

    if not move:
        raise BusinessError(
            code=ErrorCode.VALIDATION_ERROR,
            message=f"凭证不存在: {move_id}",
        )

    acct_ids = list(set(
        line.ledger_account_id for line in move.line_ids
    ))
    accounts = db.query(LedgerAccount).filter(
        LedgerAccount.id.in_(acct_ids)
    ).all()
    acct_map = {a.id: a for a in accounts}

    lines = [
        AccountMoveLineOut(
            id=line.id,
            account_code=acct_map[line.ledger_account_id].code if line.ledger_account_id in acct_map else "",
            account_name=acct_map[line.ledger_account_id].name if line.ledger_account_id in acct_map else "",
            debit=line.debit,
            credit=line.credit,
            partner_id=line.partner_id,
            partner_type=line.partner_type,
            amount_residual=line.amount_residual,
            reconciled=line.reconciled,
        )
        for line in move.line_ids
    ]

    return AccountMoveDetail(
        id=move.id,
        name=move.name,
        move_type=move.move_type,
        date=move.date,
        state=move.state,
        amount_total=move.amount_total,
        source_model=move.source_model,
        source_id=move.source_id,
        is_reversal=move.is_reversal,
        created_at=move.created_at,
        lines=lines,
    )


@router.get("/reports/trial-balance")
def get_trial_balance(
    date: str = Query(..., description="日期 YYYY-MM-DD"),
    db: Session = Depends(get_db),
    account_id: int = Depends(get_account_id),
):
    """试算平衡表"""
    ledger_id = get_ledger_id(db, account_id)
    engine = LedgerEngine(db)
    result = engine.get_trial_balance(ledger_id, date)

    return TrialBalanceReport(
        rows=[TrialBalanceRow(**r) for r in result["rows"]],
        total_debit=result["total_debit"],
        total_credit=result["total_credit"],
        balanced=result["balanced"],
    )


@router.get("/receivable/partner/{partner_id}")
def get_partner_receivable(
    partner_id: int,
    partner_type: str = Query(..., pattern="^(customer|supplier)$"),
    as_of_date: Optional[str] = Query(None, description="截止日期 YYYY-MM-DD，默认今天"),
    db: Session = Depends(get_db),
    account_id: int = Depends(get_account_id),
):
    """往来余额 + 账龄分析"""
    ledger_id = get_ledger_id(db, account_id)
    engine = ReceivableEngine(db)

    as_of = as_of_date or date.today().isoformat()
    acct_type = "asset_receivable" if partner_type == "customer" else "liability_payable"

    balance = engine.get_partner_balance(
        partner_id, partner_type, account_type=acct_type, as_of=as_of,
    )

    aging = engine.get_aging_report(
        partner_id, partner_type, as_of_date=as_of, account_type=acct_type,
    )

    return PartnerBalanceOut(
        partner_id=partner_id,
        partner_type=partner_type,
        balance=balance,
        account_type=acct_type,
        aging=aging,
    )
