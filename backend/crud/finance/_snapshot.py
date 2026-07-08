"""LedgerSnapshot — 一次性加载账本财务数据的 deep module。

替代 _ledger_helpers.py 中逐科目逐个查询的模式（约 20-40 次独立 SQL），
用一条 SQL 加载全部 AccountMoveLine，在内存中按 code 分组，按需计算。

接口：
  cum_dc(code) -> (debit, credit)            替代 _l（累计到 bs_cutoff）
  per_dc(code, start, end, exclude) -> (d,c)  替代 _lp（任意区间）
  pnl_dc(code, start, end) -> (d,c)           替代 pnl_lp
  biz_dc(code, start, end) -> (d,c)           替代 business_lp
  intl_dc(code, start, end, source_models) -> (d,c)  替代 internal_lp
  bal(code) -> Decimal                        替代 _bal
  crd(code) -> Decimal                        替代 _crd
  stock_moves() -> list                       替代 _stock_moves_as_of
  bank_transactions() -> list                 替代 CF 中 BankTransaction 查询
  cash_flow_transactions() -> list            替代 CF 中 CashFlowTransaction 查询
  opening_balance -> OpeningBalance           替代 get_latest_opening_balance

实例追溯（trace_* 系列）：
  trace_cum_dc(code) -> (debit, credit, [aml_ids])
  trace_per_dc(code, start, end, exclude) -> (debit, credit, [aml_ids])
  trace_pnl_dc(code, start, end) -> (debit, credit, [aml_ids])
  trace_biz_dc(code, start, end) -> (debit, credit, [aml_ids])
  trace_intl_dc(code, start, end, source_models) -> (debit, credit, [aml_ids])
  trace_bal(code) -> (balance, [aml_ids])
  trace_crd(code) -> (balance, [aml_ids])
  trace_bal_at(code, cutoff) -> (balance, [aml_ids])
  trace_crd_at(code, cutoff) -> (balance, [aml_ids])
  get_move_meta(aml_ids) -> {aml_id: {move_id, move_name, move_date, source_model, source_id}}
"""

from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Dict, FrozenSet, List, Set, Tuple

from sqlalchemy.orm import Session

import models
from utils import _d
from models_finance import Ledger, LedgerAccount, AccountMove, AccountMoveLine
from errors import BusinessError, ErrorCode

from .opening_balances import get_latest_opening_balance
from ._ledger_helpers import PNL_CLOSE_MODELS, INTERNAL_TRANSFER_MODELS


DataRow = Tuple[str, str, datetime, Decimal, Decimal]
"""一行：(code, source_model, date_l1, debit_l2, credit_l2)"""


@dataclass
class TraceItem:
    """分录行追溯项：含 AML.id + AccountMove 元数据"""
    aml_id: int
    code: str
    source_model: str
    source_id: int
    date_l1: datetime
    debit_l2: Decimal
    credit_l2: Decimal
    move_id: int
    move_name: str


class LedgerSnapshot:

    def __init__(
        self,
        db: Session,
        account_id: int,
        bs_cutoff: datetime = None,
        period_start: datetime = None,
        period_end: datetime = None,
    ):
        self._db = db
        self._account_id = account_id
        self._bs_cutoff = bs_cutoff
        self._period_start = period_start
        self._period_end = period_end

        acct = db.query(models.Account).filter(models.Account.id == account_id).first()
        if not acct:
            raise BusinessError(code=ErrorCode.ORDER_NOT_FOUND, data={"order_type": "账本", "order_id": account_id})

        ledger = db.query(Ledger).filter(Ledger.code == acct.code).first()
        self._ledger = ledger

        # ── 确定最大日期以加载全部会计数据 ──
        max_date = None
        for d in [bs_cutoff, period_end]:
            if d is not None and (max_date is None or d > max_date):
                max_date = d

        # ── 预计算：累计到 bs_cutoff ──
        self._cum: Dict[str, Tuple[Decimal, Decimal]] = {}
        """{code: (debit_sum, credit_sum)} 累计到 bs_cutoff"""

        # ── 全部行数据：按 code 分桶 ──
        self._rows: Dict[str, List[DataRow]] = defaultdict(list)
        """{code: [(sm, date, debit, credit), ...]} 全部期间行"""

        # ── 实例追溯：按 code 分桶的 TraceItem ──
        self._trace_rows_by_code: Dict[str, List[TraceItem]] = defaultdict(list)
        """{code: [TraceItem, ...]} 含 AML.id + AccountMove 元数据"""

        if ledger and max_date is not None:
            self._load(db, ledger, bs_cutoff, max_date)

        # ── 库存 / 银行 / 现金流 / 发票 懒加载缓存 ──
        self._stock_moves_cache = None
        self._bank_tx_cache = None
        self._cf_tx_cache = None
        self._invoice_cache = None

        # ── 期初余额 ──
        bs_date_str = None
        if bs_cutoff is not None:
            bs_date_str = bs_cutoff.strftime("%Y-%m-%d") if hasattr(bs_cutoff, "strftime") else str(bs_cutoff)
        self._opening_balance = get_latest_opening_balance(db, account_id, bs_date_str) if bs_date_str else None

    def _load(self, db, ledger, bs_cutoff, max_date):
        rows = db.query(
            LedgerAccount.code,
            AccountMove.source_model,
            AccountMove.date_l1,
            AccountMoveLine.debit_l2,
            AccountMoveLine.credit_l2,
            AccountMoveLine.id,
            AccountMove.id,
            AccountMove.name,
            AccountMove.source_id,
        ).join(
            LedgerAccount, AccountMoveLine.ledger_account_id == LedgerAccount.id
        ).join(
            AccountMove, AccountMoveLine.move_id == AccountMove.id
        ).filter(
            LedgerAccount.ledger_id == ledger.id,
            AccountMove.date_l1 <= max_date,
        ).all()

        for code, sm, date_raw, debit_raw, credit_raw, aml_id, move_id, move_name, source_id in rows:
            d = _d(debit_raw)
            c = _d(credit_raw)
            sm_norm = (sm or "").strip()
            row = (code, sm_norm, date_raw, d, c)

            self._rows[code].append(row)

            if bs_cutoff is not None and date_raw is not None and self._date_le(date_raw, bs_cutoff):
                prev = self._cum.get(code, (Decimal("0"), Decimal("0")))
                self._cum[code] = (prev[0] + d, prev[1] + c)

            # ── 实例追溯：完整 TraceItem ──
            self._trace_rows_by_code[code].append(TraceItem(
                aml_id=aml_id,
                code=code,
                source_model=sm_norm,
                source_id=source_id or 0,
                date_l1=date_raw,
                debit_l2=d,
                credit_l2=c,
                move_id=move_id,
                move_name=(move_name or "").strip(),
            ))

    # ── 日期工具 ──
    @staticmethod
    def _date_le(date_val, cutoff) -> bool:
        if hasattr(date_val, "hour"):
            return date_val <= cutoff
        return datetime.combine(date_val, datetime.min.time()) <= cutoff

    @staticmethod
    def _date_ge(date_val, start) -> bool:
        if hasattr(date_val, "hour"):
            return date_val >= start
        return datetime.combine(date_val, datetime.min.time()) >= start

    @staticmethod
    def _in_range(date_val, start, end) -> bool:
        if start is None or end is None:
            return False
        return LedgerSnapshot._date_ge(date_val, start) and LedgerSnapshot._date_le(date_val, end)

    # ── 公开查询方法 ──

    def cum_dc(self, code: str) -> Tuple[Decimal, Decimal]:
        """累计 (debit, credit) 截止 bs_cutoff。替代 _l()"""
        return self._cum.get(code, (Decimal("0"), Decimal("0")))

    def per_dc(self, code: str, start: datetime, end: datetime,
               exclude: FrozenSet[str] = None) -> Tuple[Decimal, Decimal]:
        """期间 (debit, credit) [start, end]，可选排除 source_model。替代 _lp()"""
        d = Decimal("0")
        c = Decimal("0")
        for _, sm, date_raw, debit, credit in self._rows.get(code, []):
            if self._in_range(date_raw, start, end):
                if exclude and sm in exclude:
                    continue
                d += debit
                c += credit
        return d, c

    def pnl_dc(self, code: str, start: datetime, end: datetime) -> Tuple[Decimal, Decimal]:
        """利润表发生额：排除 period_close/year_close。替代 pnl_lp()"""
        return self.per_dc(code, start, end, exclude=PNL_CLOSE_MODELS)

    def biz_dc(self, code: str, start: datetime, end: datetime) -> Tuple[Decimal, Decimal]:
        """业务发生额：排除所有内部结转。替代 business_lp()"""
        return self.per_dc(code, start, end, exclude=INTERNAL_TRANSFER_MODELS)

    def intl_dc(self, code: str, start: datetime, end: datetime,
                source_models: List[str] = None) -> Tuple[Decimal, Decimal]:
        """内部结转发生额。替代 internal_lp()"""
        include = frozenset(source_models) if source_models is not None else INTERNAL_TRANSFER_MODELS
        d = Decimal("0")
        c = Decimal("0")
        for _, sm, date_raw, debit, credit in self._rows.get(code, []):
            if self._in_range(date_raw, start, end) and sm in include:
                d += debit
                c += credit
        return d, c

    def cum_dc_at(self, code: str, cutoff: datetime) -> Tuple[Decimal, Decimal]:
        """任意截止日的累计 (debit, credit)。替代 _l() 的 cutoff 参数。"""
        d = Decimal("0")
        c = Decimal("0")
        for _, _, date_raw, debit, credit in self._rows.get(code, []):
            if date_raw is not None and self._date_le(date_raw, cutoff):
                d += debit
                c += credit
        return d, c

    def bal(self, code: str) -> Decimal:
        """资产/费用余额: 借-贷。替代 _bal()"""
        d, c = self.cum_dc(code)
        return d - c

    def bal_at(self, code: str, cutoff: datetime) -> Decimal:
        """资产/费用余额在任意截止日。替代 _bal(db, ledger, code, cutoff)。"""
        d, c = self.cum_dc_at(code, cutoff)
        return d - c

    def crd(self, code: str) -> Decimal:
        """负债/权益/收入余额: 贷-借。替代 _crd()"""
        d, c = self.cum_dc(code)
        return c - d

    def crd_at(self, code: str, cutoff: datetime) -> Decimal:
        """负债/权益/收入余额在任意截止日。替代 _crd(db, ledger, code, cutoff)。"""
        d, c = self.cum_dc_at(code, cutoff)
        return c - d

    # ── 实例追溯方法 ──

    def trace_cum_dc(self, code: str) -> Tuple[Decimal, Decimal, List[int]]:
        """累计 (debit, credit, [aml_ids]) 截止 bs_cutoff。"""
        d = Decimal("0")
        c = Decimal("0")
        ids: List[int] = []
        cutoff = self._bs_cutoff
        for item in self._trace_rows_by_code.get(code, []):
            if cutoff is not None and item.date_l1 is not None and self._date_le(item.date_l1, cutoff):
                d += item.debit_l2
                c += item.credit_l2
                ids.append(item.aml_id)
        return d, c, ids

    def trace_cum_dc_at(self, code: str, cutoff: datetime) -> Tuple[Decimal, Decimal, List[int]]:
        """任意截止日的累计 (debit, credit, [aml_ids])。"""
        d = Decimal("0")
        c = Decimal("0")
        ids: List[int] = []
        for item in self._trace_rows_by_code.get(code, []):
            if item.date_l1 is not None and self._date_le(item.date_l1, cutoff):
                d += item.debit_l2
                c += item.credit_l2
                ids.append(item.aml_id)
        return d, c, ids

    def trace_per_dc(self, code: str, start: datetime, end: datetime,
                     exclude: FrozenSet[str] = None) -> Tuple[Decimal, Decimal, List[int]]:
        """期间 (debit, credit, [aml_ids]) [start, end]，可选排除 source_model。"""
        d = Decimal("0")
        c = Decimal("0")
        ids: List[int] = []
        for item in self._trace_rows_by_code.get(code, []):
            if self._in_range(item.date_l1, start, end):
                if exclude and item.source_model in exclude:
                    continue
                d += item.debit_l2
                c += item.credit_l2
                ids.append(item.aml_id)
        return d, c, ids

    def trace_pnl_dc(self, code: str, start: datetime, end: datetime) -> Tuple[Decimal, Decimal, List[int]]:
        """利润表发生额：排除 period_close/year_close。"""
        return self.trace_per_dc(code, start, end, exclude=PNL_CLOSE_MODELS)

    def trace_biz_dc(self, code: str, start: datetime, end: datetime) -> Tuple[Decimal, Decimal, List[int]]:
        """业务发生额：排除所有内部结转。"""
        return self.trace_per_dc(code, start, end, exclude=INTERNAL_TRANSFER_MODELS)

    def trace_intl_dc(self, code: str, start: datetime, end: datetime,
                      source_models: List[str] = None) -> Tuple[Decimal, Decimal, List[int]]:
        """内部结转发生额（带 AML ids）。"""
        include = frozenset(source_models) if source_models is not None else INTERNAL_TRANSFER_MODELS
        d = Decimal("0")
        c = Decimal("0")
        ids: List[int] = []
        for item in self._trace_rows_by_code.get(code, []):
            if self._in_range(item.date_l1, start, end) and item.source_model in include:
                d += item.debit_l2
                c += item.credit_l2
                ids.append(item.aml_id)
        return d, c, ids

    def trace_bal(self, code: str) -> Tuple[Decimal, List[int]]:
        """资产/费用余额 + AML ids: 借-贷。"""
        d, c, ids = self.trace_cum_dc(code)
        return d - c, ids

    def trace_bal_at(self, code: str, cutoff: datetime) -> Tuple[Decimal, List[int]]:
        """资产/费用余额在任意截止日 + AML ids。"""
        d, c, ids = self.trace_cum_dc_at(code, cutoff)
        return d - c, ids

    def trace_crd(self, code: str) -> Tuple[Decimal, List[int]]:
        """负债/权益/收入余额 + AML ids: 贷-借。"""
        d, c, ids = self.trace_cum_dc(code)
        return c - d, ids

    def trace_crd_at(self, code: str, cutoff: datetime) -> Tuple[Decimal, List[int]]:
        """负债/权益/收入余额在任意截止日 + AML ids。"""
        d, c, ids = self.trace_cum_dc_at(code, cutoff)
        return c - d, ids

    def get_move_meta(self, aml_ids: Set[int]) -> Dict[int, dict]:
        """按 AML.id 查回 AccountMove 元数据

        返回: {aml_id: {move_id, move_name, move_date, source_model, source_id}}
        """
        result: Dict[int, dict] = {}
        for items in self._trace_rows_by_code.values():
            for item in items:
                if item.aml_id in aml_ids and item.aml_id not in result:
                    result[item.aml_id] = {
                        "move_id": item.move_id,
                        "move_name": item.move_name,
                        "move_date": item.date_l1,
                        "source_model": item.source_model,
                        "source_id": item.source_id,
                    }
        return result

    # ── 库存 ──
    def stock_moves(self) -> List[models.StockMove]:
        if self._stock_moves_cache is not None:
            return self._stock_moves_cache
        moves = self._db.query(models.StockMove).filter(
            models.StockMove.account_id == self._account_id,
            models.StockMove.move_date_l1.isnot(None),
        ).all()
        result = []
        cutoff = self._bs_cutoff
        if cutoff is not None:
            for m in moves:
                biz_date = m.move_date_l1
                if biz_date is not None and self._date_le(biz_date, cutoff):
                    result.append(m)
        else:
            result = list(moves)
        self._stock_moves_cache = result
        return result

    # ── 银行流水 ──
    def bank_transactions(self) -> List[models.BankTransaction]:
        if self._bank_tx_cache is not None:
            return self._bank_tx_cache
        q = self._db.query(models.BankTransaction).filter(
            models.BankTransaction.account_id == self._account_id,
        )
        if self._period_start is not None:
            q = q.filter(models.BankTransaction.transaction_date_l1 >= self._period_start)
        if self._period_end is not None:
            q = q.filter(models.BankTransaction.transaction_date_l1 <= self._period_end)
        self._bank_tx_cache = q.all()
        return self._bank_tx_cache

    # ── 现金流交易 ──
    def cash_flow_transactions(self) -> List[models.CashFlowTransaction]:
        if self._cf_tx_cache is not None:
            return self._cf_tx_cache
        q = self._db.query(models.CashFlowTransaction).filter(
            models.CashFlowTransaction.account_id == self._account_id,
        )
        if self._period_start is not None:
            q = q.filter(models.CashFlowTransaction.transaction_date_l1 >= self._period_start)
        if self._period_end is not None:
            q = q.filter(models.CashFlowTransaction.transaction_date_l1 <= self._period_end)
        self._cf_tx_cache = q.all()
        return self._cf_tx_cache

    # ── 发票 ──
    def invoices(self) -> list:
        """懒加载发票列表"""
        if self._invoice_cache is not None:
            return self._invoice_cache
        q = self._db.query(models.Invoice).filter(
            models.Invoice.account_id == self._account_id,
        )
        cutoff = self._bs_cutoff
        if cutoff is not None:
            cutoff_date = cutoff.date() if hasattr(cutoff, "date") else cutoff
            q = q.filter(models.Invoice.issue_date_l1 <= cutoff_date)
        self._invoice_cache = q.all()
        return self._invoice_cache

    def move_exists(self, source_model: str, start: datetime, end: datetime) -> bool:
        """检查期间内是否存在指定 source_model 的 AccountMove"""
        for items in self._trace_rows_by_code.values():
            for item in items:
                if item.source_model == source_model and self._in_range(item.date_l1, start, end):
                    return True
        return False

    # ── 现金流分类追溯 ──

    def trace_bank_txns_classified(self) -> dict:
        """银行流水按 CF 项目分类聚合 → {cf_code: (net_amount, [("bank_txn", id), ...])}"""
        from .cash_flow_classifier import classify_bank_transaction, CF_LINE_MAP

        result = {code: (Decimal("0"), []) for code in CF_LINE_MAP}
        for txn in self.bank_transactions():
            code = classify_bank_transaction(self._db, txn)
            if code not in result:
                result[code] = (Decimal("0"), [])
            sign = Decimal("1") if txn.transaction_type == "inflow" else Decimal("-1")
            amount, ids = result[code]
            result[code] = (amount + sign * _d(txn.amount_l2), ids + [("bank_txn", txn.id)])
        return result

    def trace_cash_txns_classified(self) -> dict:
        """现金流水按 CF 项目分类聚合 → {cf_code: (net_amount, [("cash_txn", id), ...])}"""
        from .cash_flow_classifier import classify_cash_flow_transaction, CF_LINE_MAP

        result = {code: (Decimal("0"), []) for code in CF_LINE_MAP}
        for txn in self.cash_flow_transactions():
            code = classify_cash_flow_transaction(txn)
            if code not in result:
                result[code] = (Decimal("0"), [])
            sign = Decimal("1") if txn.type == "inflow" else Decimal("-1")
            amount, ids = result[code]
            result[code] = (amount + sign * _d(txn.amount_l2), ids + [("cash_txn", txn.id)])
        return result

    # ── 期初余额 ──
    @property
    def opening_balance(self):
        return self._opening_balance

    @property
    def ledger(self):
        return self._ledger
