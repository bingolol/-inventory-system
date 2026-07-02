"""银行对账 API"""
from datetime import datetime
from decimal import Decimal
from typing import List, Literal, Optional

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
from crud.base import _log
from errors import BusinessError, ErrorCode
from operation_result import OperationResult, EntityType, OperationType

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
        "book_balance": float(rec.book_balance), "statement_balance": float(rec.statement_balance),
        "adjusted_book": float(rec.adjusted_book), "adjusted_statement": float(rec.adjusted_statement),
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


@router.post("/bank/entry")
def create_bank_entry(
    body: BankEntryBody,
    account_id: int = Depends(get_account_id),
    operator: str = Depends(get_operator),
    db: Session = Depends(get_db),
):
    """直接录入银行利息收入/手续费（无需走完整对账流程）

    凭证锚点设计：BankTransaction.id 作为 AccountMove 的 source_id，
    红冲时 reverse_journal(source_model="bank_entry", source_id=tx.id) 即可
    借贷互换红冲原始凭证，无需 post_journal 生成补偿凭证。
    """
    import models
    from finance_integration import post_journal

    if body.entry_type not in ("interest_income", "bank_fee"):
        raise BusinessError(code=ErrorCode.VALIDATION_ERROR,
                            message=f"无效 entry_type: {body.entry_type}，仅支持 interest_income / bank_fee")

    amt = Decimal(str(body.amount))
    dt = datetime.strptime(body.transaction_date, "%Y-%m-%d")
    direction = "in" if body.entry_type == "interest_income" else "out"

    with unit_of_work(db):
        ba = db.query(models.BankAccount).filter(
            models.BankAccount.account_id == account_id,
        ).with_for_update().first()
        if not ba:
            raise BusinessError(code=ErrorCode.BANK_ACCOUNT_NOT_FOUND)

        # 1. 先更新余额
        if direction == "in":
            ba.balance_l4 += amt
        else:
            ba.balance_l4 -= amt

        # 2. 创建 BankTransaction → flush 获取 tx.id（作为凭证锚点）
        tx = models.BankTransaction(
            account_id=account_id, bank_account_id=ba.id,
            transaction_type="inflow" if direction == "in" else "outflow",
            amount_l2=amt, balance_after_l4=ba.balance_l4,
            transaction_date_l1=dt, description=body.description or body.entry_type,
            flow_category_l2="operating",
        )
        db.add(tx)
        db.flush()
        tx_id = tx.id

        # 3. 用 tx.id 作为 source_id 过账，建立 BankTransaction ↔ AccountMove 一一对应
        post_journal(db, account_id, "bank_fee_entry", {
            "amount": amt,
            "direction": direction,
            "date": body.transaction_date,
            "source_model": "bank_entry",
            "source_id": tx_id,
        })

        _log(db, account_id, "create", "bank_entry", tx_id,
             f"{'利息收入' if body.entry_type == 'interest_income' else '手续费'}: {body.amount}",
             operator=operator)

    entry_label = "利息收入" if body.entry_type == "interest_income" else "手续费"
    changes = {"cash": {"amount": f"+{body.amount}" if direction == "in" else f"-{body.amount}"}}

    result = OperationResult(
        operation=OperationType.CREATE,
        entity_type=EntityType.BANK_ENTRY,
        entity_id=tx_id,
        summary=f"{entry_label}录入成功，金额 {body.amount}",
        ai_hint=f"{entry_label}已录入，银行存款余额已更新。",
        changes=changes,
    )
    return result.to_dict()
