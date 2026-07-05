"""期间损益结转引擎 — 月结最后一步

契约（原方案逐条确认）:
  1. _l 取累计余额，不排除 period_close（与 engine_tax 的 _lp+排除相反）
  2. 收入类（贷方余额→借方结转）: 6001/6051/6301
  3. 费用类（借方余额→贷方结转）: 6401/6403/6601/6602/6603/6701/6801
  4. 差额进 4103（净利润贷方，净损失借方）
  5. post_journal(account_id, "period_close", {lines, date, source_model, source_id}, force)
  6. source_id = _period_hash(period, "period_close")
  7. 12月额外 year_close: 4103→4104，source_id = _period_hash(period, "year_close")
  8. force=False 幂等（source_id），force=True 覆盖
"""

import logging
from calendar import monthrange
from datetime import datetime
from decimal import Decimal
from typing import Dict

from sqlalchemy.orm import Session

import models
from models_finance import AccountMove, Ledger
from finance_integration import post_journal, reverse_journal
from crud.finance._ledger_helpers import _l
from utils import Q2

logger = logging.getLogger("inventory")


def _parse_period(period: str):
    year, month = int(period[:4]), int(period[5:7])
    _, last_day = monthrange(year, month)
    start_dt = datetime(year, month, 1, 0, 0, 0)
    end_dt = datetime(year, month, last_day, 23, 59, 59)
    return start_dt, end_dt


def _period_hash(period: str, tag: str) -> int:
    h = 0
    for c in f"{period}_{tag}":
        h = ((h << 5) - h) + ord(c)
        h &= 0x7FFFFFFFFFFFFFFF
    return h


class PeriodCloseEngine:

    INCOME_CODES = ["6001", "6051", "6301"]
    EXPENSE_CODES = ["6401", "6403", "6601", "6602", "6603", "6701", "6801"]

    def __init__(self, db: Session):
        self.db = db

    def execute(self, account_id: int, period: str, force: bool = False) -> Dict:
        period_start, close_dt = _parse_period(period)
        ledger = self.db.query(Ledger).join(
            models.Account, Ledger.code == models.Account.code
        ).filter(models.Account.id == account_id).first()

        if not ledger:
            return {"status": "error", "msg": "总账未初始化"}

        # ── 第 1 步：幂等检查 ──
        if not force:
            existing = self.db.query(AccountMove).filter(
                AccountMove.ledger_id == ledger.id,
                AccountMove.source_model == "period_close",
                AccountMove.date_l1 >= period_start,
                AccountMove.date_l1 <= close_dt,
            ).first()
            if existing:
                return {"status": "skipped", "period": period,
                        "msg": "已结转过，使用 force=True 重跑"}

        # ── 第 2 步：取损益科目余额（_l 累计，不排除 period_close）──
        lines = []
        total_revenue = Decimal("0")
        total_expense = Decimal("0")

        for code in self.INCOME_CODES:
            d, c = _l(self.db, ledger, code, close_dt)
            balance = c - d
            amt = balance.quantize(Q2)
            if abs(amt) >= Decimal("0.01"):
                if balance > 0:
                    lines.append({"account_code": code,
                                  "debit": amt, "credit": Decimal("0")})
                else:
                    lines.append({"account_code": code,
                                  "debit": Decimal("0"), "credit": abs(amt)})
                total_revenue += amt

        for code in self.EXPENSE_CODES:
            d, c = _l(self.db, ledger, code, close_dt)
            balance = d - c
            amt = balance.quantize(Q2)
            if abs(amt) >= Decimal("0.01"):
                if balance > 0:
                    lines.append({"account_code": code,
                                  "debit": Decimal("0"), "credit": amt})
                else:
                    lines.append({"account_code": code,
                                  "debit": abs(amt), "credit": Decimal("0")})
                total_expense += amt

        # ── 第 3 步：差额进 4103 ──
        net_profit = total_revenue - total_expense
        if abs(net_profit) >= Decimal("0.01"):
            if net_profit > 0:
                lines.append({"account_code": "4103",
                              "debit": Decimal("0"),
                              "credit": net_profit.quantize(Q2)})
            else:
                lines.append({"account_code": "4103",
                              "debit": abs(net_profit).quantize(Q2),
                              "credit": Decimal("0")})

        # ── 第 4 步：force 模式下先冲红旧凭证 ──
        if force:
            reverse_journal(self.db, account_id, "period_close",
                            _period_hash(period, "period_close"),
                            reversal_date=close_dt, force=True)

        # ── 第 5 步：过账 period_close ──
        if lines:
            post_journal(self.db, account_id, "period_close", {
                "lines": lines,
                "date": close_dt,
                "source_model": "period_close",
                "source_id": _period_hash(period, "period_close"),
            }, force=force)
            logger.info(f"损益结转 {period}: 收入={total_revenue:.2f} 费用={total_expense:.2f} 净利润={net_profit:.2f}")

        # ── 第 6 步：12月额外 year_close ──
        year_close_result = None
        if period_start.month == 12:
            year_close_result = self._execute_year_close(
                ledger, account_id, period, close_dt, force
            )

        return {
            "status": "ok",
            "period": period,
            "total_revenue": float(total_revenue),
            "total_expense": float(total_expense),
            "net_profit": float(net_profit),
            "year_close": year_close_result,
        }

    def _execute_year_close(self, ledger: Ledger, account_id: int,
                            period: str, close_dt: datetime,
                            force: bool) -> Dict:
        d, c = _l(self.db, ledger, "4103", close_dt)
        balance_4103 = (c - d).quantize(Q2)

        if balance_4103 == Decimal("0"):
            return {"status": "skipped", "reason": "4103 余额为 0"}

        if balance_4103 > 0:
            year_lines = [
                {"account_code": "4103", "debit": balance_4103,
                 "credit": Decimal("0")},
                {"account_code": "4104", "debit": Decimal("0"),
                 "credit": balance_4103},
            ]
        else:
            bal = abs(balance_4103)
            year_lines = [
                {"account_code": "4104", "debit": bal,
                 "credit": Decimal("0")},
                {"account_code": "4103", "debit": Decimal("0"),
                 "credit": bal},
            ]

        if force:
            reverse_journal(self.db, account_id, "year_close",
                            _period_hash(period, "year_close"),
                            reversal_date=close_dt, force=True)

        post_journal(self.db, account_id, "year_close", {
            "lines": year_lines,
            "date": close_dt,
            "source_model": "year_close",
            "source_id": _period_hash(period, "year_close"),
        }, force=force)

        logger.info(f"年结 {period}: 4103→4104 结转 {balance_4103:.2f}")
        return {
            "status": "ok",
            "transferred": float(balance_4103),
        }
