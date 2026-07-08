"""银行对账 API"""
from datetime import datetime
from typing import List, Literal, Optional

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from database import get_db
from utils import get_or_404
from account_dep import get_account_id, get_operator
from uow import unit_of_work
from commands.base import dispatch
from commands.bank_reconcile import (
    ImportBankStatement, ReconcileBank, ForceMatchBankReconciliation,
    ConfirmBankReconciliation, GenerateReconciliationEntry,
)
from errors import BusinessError, ErrorCode
from commands.bank_commands import CreateBankEntry

router = APIRouter()


class StmtLine(BaseModel):
    transaction_date: str
    amount: float
    description: str = ""


class ImportStatementBody(BaseModel):
    period_start: str
    period_end: str
    opening_balance: float
    closing_balance: float
    lines: List[StmtLine] = []


@router.post("/bank/statement")
def import_bank_statement(
    body: ImportStatementBody,
    account_id: int = Depends(get_account_id),
    operator: str = Depends(get_operator),
    db: Session = Depends(get_db),
):
    import traceback, logging
    logger = logging.getLogger("inventory")
    try:
        with unit_of_work(db):
            return dispatch(ImportBankStatement(
                account_id=account_id, operator=operator,
                period_start=body.period_start, period_end=body.period_end,
                opening_balance=body.opening_balance, closing_balance=body.closing_balance,
                lines=[l.model_dump() for l in body.lines],
            ), db)
    except BusinessError:
        raise
    except Exception as e:
        logger.error(f"导入对账单失败: {e}\n{traceback.format_exc()}")
        raise BusinessError(
            code=ErrorCode.VALIDATION_ERROR,
            message=f"导入对账单失败: {str(e)}",
        )


@router.get("/bank/statement/{stmt_id}")
def get_bank_statement(
    stmt_id: int,
    account_id: int = Depends(get_account_id),
    db: Session = Depends(get_db),
):
    import models_bank
    stmt = get_or_404(db, models_bank.BankStatement, stmt_id, account_id)
    lines = db.query(models_bank.BankStatementLine).filter(
        models_bank.BankStatementLine.statement_id == stmt_id,
    ).all()
    return {
        "id": stmt.id, "period_start": stmt.period_start.isoformat(),
        "period_end": stmt.period_end.isoformat(),
        "opening_balance": float(stmt.opening_balance_l1), "closing_balance": float(stmt.closing_balance_l1),
        "lines": [{"id": l.id, "transaction_date": l.transaction_date_l1.isoformat(),
                    "amount": float(l.amount_l2), "description": l.description,
                    "matched_tx_ids": l.matched_tx_ids} for l in lines],
    }


class ReconcileSeed(BaseModel):
    item_type: str
    amount: float
    direction: str = "in"
    source_dates: List[str] = []
    notes: str = ""


@router.post("/bank/reconcile")
def reconcile_bank(
    period: str = Query(...),
    seed: Optional[str] = Query(None),
    account_id: int = Depends(get_account_id),
    operator: str = Depends(get_operator),
    db: Session = Depends(get_db),
):
    import json, traceback, logging
    logger = logging.getLogger("inventory")
    seeds = json.loads(seed) if seed else []
    try:
        with unit_of_work(db):
            return dispatch(ReconcileBank(
                account_id=account_id, operator=operator,
                period=period, seed=seeds,
            ), db)
    except BusinessError:
        raise
    except Exception as e:
        logger.error(f"银行对账失败 period={period}: {e}\n{traceback.format_exc()}")
        raise BusinessError(
            code=ErrorCode.VALIDATION_ERROR,
            message=f"银行对账失败: {str(e)}。请确认：1) 已导入对账单 2) 银行账户存在 3) 期初银行流水已录入",
        )


@router.get("/bank/reconciliation")
def get_reconciliation(
    period: str = Query(...),
    account_id: int = Depends(get_account_id),
    db: Session = Depends(get_db),
):
    import models_bank, models
    ba = db.query(models.BankAccount).filter(
        models.BankAccount.account_id == account_id,
    ).first()
    if not ba:
        raise BusinessError(code=ErrorCode.BANK_ACCOUNT_NOT_FOUND, data={"details": "无银行账户"})

    rec = db.query(models_bank.BankReconciliation).filter(
        models_bank.BankReconciliation.bank_account_id == ba.id,
        models_bank.BankReconciliation.account_id == account_id,
        models_bank.BankReconciliation.period == period,
    ).first()
    if not rec:
        return {"exists": False}

    items = db.query(models_bank.ReconciliationItem).filter(
        models_bank.ReconciliationItem.reconciliation_id == rec.id,
    ).all()
    return {
        "id": rec.id, "period": rec.period, "status": rec.status,
        "book_balance": float(rec.book_balance_l4), "statement_balance": float(rec.statement_balance_l1),
        "adjusted_book": float(rec.adjusted_book_l4), "adjusted_statement": float(rec.adjusted_statement_l4),
        "balanced": rec.balanced,
        "items": [{"id": i.id, "item_type": i.item_type, "amount": float(i.amount_l2),
                    "direction": i.direction, "resolved": i.resolved,
                    "action": i.action, "notes": i.notes} for i in items],
    }


class ForceMatchBody(BaseModel):
    stmt_line_ids: List[int]
    bank_tx_ids: List[int]
    reason: str


@router.post("/bank/reconciliation/{rec_id}/match")
def force_match(
    rec_id: int,
    body: ForceMatchBody,
    account_id: int = Depends(get_account_id),
    operator: str = Depends(get_operator),
    db: Session = Depends(get_db),
):
    with unit_of_work(db):
        return dispatch(ForceMatchBankReconciliation(
            account_id=account_id, operator=operator,
            reconciliation_id=rec_id,
            stmt_line_ids=body.stmt_line_ids,
            bank_tx_ids=body.bank_tx_ids,
            reason=body.reason,
        ), db)


@router.post("/bank/reconciliation/{rec_id}/confirm")
def confirm_reconciliation(
    rec_id: int,
    account_id: int = Depends(get_account_id),
    operator: str = Depends(get_operator),
    db: Session = Depends(get_db),
):
    with unit_of_work(db):
        return dispatch(ConfirmBankReconciliation(
            account_id=account_id, operator=operator,
            reconciliation_id=rec_id,
        ), db)


@router.post("/bank/reconciliation/{rec_id}/generate-entry")
def generate_reconciliation_entry(
    rec_id: int,
    account_id: int = Depends(get_account_id),
    operator: str = Depends(get_operator),
    db: Session = Depends(get_db),
):
    with unit_of_work(db):
        return dispatch(GenerateReconciliationEntry(
            account_id=account_id, operator=operator,
            reconciliation_id=rec_id,
        ), db)


class BankEntryBody(BaseModel):
    entry_type: Literal["interest_income", "bank_fee"]  # interest_income(利息收入) | bank_fee(银行手续费)
    amount: float
    transaction_date: str  # YYYY-MM-DD
    description: str = ""
    bank_account_id: Optional[int] = Field(default=None, description="银行账户ID，为空时自动选择首个账户")


@router.post("/bank/entry")
def create_bank_entry(
    body: BankEntryBody,
    account_id: int = Depends(get_account_id),
    operator: str = Depends(get_operator),
    db: Session = Depends(get_db),
):
    """直接录入银行利息收入/手续费（无需走完整对账流程）"""
    with unit_of_work(db):
        return dispatch(CreateBankEntry(
            account_id=account_id,
            operator=operator,
            entry_type=body.entry_type,
            amount=body.amount,
            transaction_date=body.transaction_date,
            description=body.description,
            bank_account_id=body.bank_account_id,
        ), db)
