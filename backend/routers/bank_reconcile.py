"""银行对账 API"""
from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from database import get_db
from account_dep import get_account_id, get_operator
from uow import unit_of_work
from commands.base import dispatch
from commands.bank_reconcile import (
    ImportBankStatement, ReconcileBank, ForceMatchBankReconciliation,
    ConfirmBankReconciliation, GenerateReconciliationEntry,
)
from errors import BusinessError, ErrorCode

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
    with unit_of_work(db):
        return dispatch(ImportBankStatement(
            account_id=account_id, operator=operator,
            period_start=body.period_start, period_end=body.period_end,
            opening_balance=body.opening_balance, closing_balance=body.closing_balance,
            lines=[l.model_dump() for l in body.lines],
        ), db)


@router.get("/bank/statement/{stmt_id}")
def get_bank_statement(
    stmt_id: int,
    account_id: int = Depends(get_account_id),
    db: Session = Depends(get_db),
):
    import models_bank
    stmt = db.query(models_bank.BankStatement).filter(
        models_bank.BankStatement.id == stmt_id,
        models_bank.BankStatement.account_id == account_id,
    ).first()
    if not stmt:
        raise BusinessError(code=ErrorCode.ORDER_NOT_FOUND, data={"order_type": "对账单"})
    lines = db.query(models_bank.BankStatementLine).filter(
        models_bank.BankStatementLine.statement_id == stmt_id,
    ).all()
    return {
        "id": stmt.id, "period_start": stmt.period_start.isoformat(),
        "period_end": stmt.period_end.isoformat(),
        "opening_balance": float(stmt.opening_balance), "closing_balance": float(stmt.closing_balance),
        "lines": [{"id": l.id, "transaction_date": l.transaction_date.isoformat(),
                    "amount": float(l.amount), "description": l.description,
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
    import json
    seeds = json.loads(seed) if seed else []
    with unit_of_work(db):
        return dispatch(ReconcileBank(
            account_id=account_id, operator=operator,
            period=period, seed=seeds,
        ), db)


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
        "book_balance": float(rec.book_balance), "statement_balance": float(rec.statement_balance),
        "adjusted_book": float(rec.adjusted_book), "adjusted_statement": float(rec.adjusted_statement),
        "balanced": rec.balanced,
        "items": [{"id": i.id, "item_type": i.item_type, "amount": float(i.amount),
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
