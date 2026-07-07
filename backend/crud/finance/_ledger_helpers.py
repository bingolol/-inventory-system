"""资产负债表 / 利润表共享的总账查询 helper。

从原 crud/finance.py (bca78966^) 拆分，仅做位置迁移，业务逻辑字节级一致。
"""

from datetime import datetime
from decimal import Decimal
from sqlalchemy.orm import Session
from sqlalchemy import func as sqlfunc

import models
from utils import _d
from models_finance import Ledger, LedgerAccount, AccountMove, AccountMoveLine


def _stock_moves_as_of(db: Session, account_id: int, query_end) -> list:
    """获取截至 query_end 的 StockMove。

    StockMove.move_date_l1 是业务日期真相源（BR-21 强制采购/销售单必须传业务日期，
    InventoryEngine 写入 StockMove 时也会回填业务日期）。
    本函数不再支持 move_date_l1 为 NULL 的兼容分支，所有 StockMove 必须有 move_date_l1。
    """
    moves = db.query(models.StockMove).filter(
        models.StockMove.account_id == account_id,
        models.StockMove.move_date_l1.isnot(None),
    ).all()

    result = []
    for m in moves:
        biz_date = m.move_date_l1
        if biz_date is None:
            continue
        if hasattr(biz_date, "hour"):
            if biz_date <= query_end:
                result.append(m)
        else:
            biz_dt = datetime.combine(biz_date, datetime.min.time())
            if biz_dt <= query_end:
                result.append(m)
    return result


# ── 单一真相源：BS/IS共享的总账查询 ──

def _l(db, ledger, code, cutoff):
    """累计 (debit, credit) 截止cutoff"""
    if not ledger: return Decimal("0"), Decimal("0")
    d = _d(db.query(sqlfunc.coalesce(sqlfunc.sum(AccountMoveLine.debit_l2),0)).join(
        LedgerAccount,AccountMoveLine.ledger_account_id==LedgerAccount.id
    ).join(AccountMove,AccountMoveLine.move_id==AccountMove.id).filter(
        LedgerAccount.ledger_id==ledger.id,LedgerAccount.code==code,
        AccountMove.date_l1<=cutoff).scalar())
    c = _d(db.query(sqlfunc.coalesce(sqlfunc.sum(AccountMoveLine.credit_l2),0)).join(
        LedgerAccount,AccountMoveLine.ledger_account_id==LedgerAccount.id
    ).join(AccountMove,AccountMoveLine.move_id==AccountMove.id).filter(
        LedgerAccount.ledger_id==ledger.id,LedgerAccount.code==code,
        AccountMove.date_l1<=cutoff).scalar())
    return d,c

def _lp(db, ledger, code, start, end, exclude_source_models=None):
    """期间 (debit, credit) [start,end]

    exclude_source_models: 可选，排除指定 source_model 的凭证（如 period_close）
    """
    if not ledger: return Decimal("0"),Decimal("0")
    q_d = db.query(sqlfunc.coalesce(sqlfunc.sum(AccountMoveLine.debit_l2),0)).join(
        LedgerAccount,AccountMoveLine.ledger_account_id==LedgerAccount.id
    ).join(AccountMove,AccountMoveLine.move_id==AccountMove.id).filter(
        LedgerAccount.ledger_id==ledger.id,LedgerAccount.code==code,
        AccountMove.date_l1>=start,AccountMove.date_l1<=end)
    q_c = db.query(sqlfunc.coalesce(sqlfunc.sum(AccountMoveLine.credit_l2),0)).join(
        LedgerAccount,AccountMoveLine.ledger_account_id==LedgerAccount.id
    ).join(AccountMove,AccountMoveLine.move_id==AccountMove.id).filter(
        LedgerAccount.ledger_id==ledger.id,LedgerAccount.code==code,
        AccountMove.date_l1>=start,AccountMove.date_l1<=end)
    if exclude_source_models:
        q_d = q_d.filter(
            AccountMove.source_model.is_(None) |
            ~AccountMove.source_model.in_(exclude_source_models))
        q_c = q_c.filter(
            AccountMove.source_model.is_(None) |
            ~AccountMove.source_model.in_(exclude_source_models))
    d = _d(q_d.scalar())
    c = _d(q_c.scalar())
    return d,c

# 损益结转分录（借贷抵消的会计技术性分录，不是业务真相）
PNL_CLOSE_MODELS = frozenset({"period_close", "year_close"})

# 月结内部结转分录（含税金计提等，部分是业务真相）
INTERNAL_TRANSFER_MODELS = frozenset({
    "vat_transfer_out", "tax_surcharge", "tax_income",
    "tax_income_reversal", "vat_exemption",
    "period_close", "year_close",
})


def business_lp(db, ledger, code, start, end):
    """业务发生额（最严格）：排除所有内部结转
    用于：VAT 计算（222101/102/103），避免 vat_transfer_out 污染销项
    """
    return _lp(db, ledger, code, start, end,
               exclude_source_models=INTERNAL_TRANSFER_MODELS)


def pnl_lp(db, ledger, code, start, end):
    """利润表发生额：只排除损益结转分录
    用于：利润表、资产负债表、engine_tax 累计利润
    保留 tax_surcharge/tax_income/vat_exemption（它们是真实费用/收入）
    """
    return _lp(db, ledger, code, start, end,
               exclude_source_models=PNL_CLOSE_MODELS)


def internal_lp(db, ledger, code, start, end, source_models=None):
    """内部结转发生额

    source_models=None: 全部内部结转凭证
    source_models=["tax_surcharge"]: 只要 tax_surcharge 凭证
    """
    if not ledger:
        return Decimal("0"), Decimal("0")
    include = source_models if source_models is not None else INTERNAL_TRANSFER_MODELS
    q_d = db.query(sqlfunc.coalesce(sqlfunc.sum(AccountMoveLine.debit_l2), 0)).join(
        LedgerAccount, AccountMoveLine.ledger_account_id == LedgerAccount.id
    ).join(AccountMove, AccountMoveLine.move_id == AccountMove.id).filter(
        LedgerAccount.ledger_id == ledger.id,
        LedgerAccount.code == code,
        AccountMove.date_l1 >= start,
        AccountMove.date_l1 <= end,
        AccountMove.source_model.in_(include)
    )
    q_c = db.query(sqlfunc.coalesce(sqlfunc.sum(AccountMoveLine.credit_l2), 0)).join(
        LedgerAccount, AccountMoveLine.ledger_account_id == LedgerAccount.id
    ).join(AccountMove, AccountMoveLine.move_id == AccountMove.id).filter(
        LedgerAccount.ledger_id == ledger.id,
        LedgerAccount.code == code,
        AccountMove.date_l1 >= start,
        AccountMove.date_l1 <= end,
        AccountMove.source_model.in_(include)
    )
    return _d(q_d.scalar()), _d(q_c.scalar())


def _bal(db, ledger, code, cutoff):
    """asset/expense余额: 借-贷"""
    d,c=_l(db,ledger,code,cutoff); return d-c

def _crd(db, ledger, code, cutoff):
    """liability/equity/income余额: 贷-借"""
    d,c=_l(db,ledger,code,cutoff); return c-d

def _pdr(db, ledger, code, start, end, exclude_source_models=None):
    """期内借方"""
    d,_=_lp(db,ledger,code,start,end,exclude_source_models=exclude_source_models); return d
