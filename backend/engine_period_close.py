"""期间损益结转引擎 — 月结最后一步

契约（原方案逐条确认）:
  1. _list_subaccount_balances 列出父科目及其所有子科目的累计余额
  2. 收入类（贷方余额→借方结转）: 6001/6051/6301（含子科目）
  3. 费用类（借方余额→贷方结转）: 6401/6403/6601/6602/6603/6701/6801（含子科目）
  4. 差额进 4103（净利润贷方，净损失借方）
  5. post_journal(account_id, "period_close", {lines, date, source_model, source_id}, force)
  6. source_id = period_hash(period, "period_close")
  7. 12月额外 year_close: 4103→4104，source_id = period_hash(period, "year_close")
  8. force=False 幂等（source_id），force=True 覆盖

破坏性升级（不兼容老数据）:
  - 损益结转按"每个非零余额科目分别结转"原则，确保每个子科目都被结平
  - 原因：附加税计提写入明细 640302/640303/640304，主科目 6403 余额为 0。
    若只汇总到父科目结转，子科目余额会滞留，导致父科目残留贷方、子科目残留借方，
    虽 BS 能"形式上"平衡（父+子净额抵消），但会计核算错误（每个科目应结平）。
  - 正确做法：用 LIKE 'code%' 列出所有子科目，对每个非零余额科目分别生成结转分录。
  - 会计科目编码体系（4-2-2 结构）保证 LIKE 'code%' 前缀匹配不会误伤：
    6001 主营业务收入 → 子科目 600101/600102/...
    6403 税金及附加   → 子科目 640302/640303/640304/...
    不存在跳级编码（如 64031 这种 5 位科目）。
"""

import logging
from datetime import datetime
from decimal import Decimal
from typing import Dict, List, Tuple

from sqlalchemy.orm import Session
from sqlalchemy import func as sqlfunc

import models
from models_finance import AccountMove, AccountMoveLine, Ledger, LedgerAccount
from finance_integration import post_journal, reverse_journal
from utils import _d, Q2
from utils.period import parse_period, period_hash

logger = logging.getLogger("inventory")


class PeriodCloseEngine:

    INCOME_CODES = ["6001", "6051", "6301"]
    EXPENSE_CODES = ["6401", "6403", "6601", "6602", "6603", "6701", "6711", "6801"]

    def __init__(self, db: Session):
        self.db = db

    def _list_subaccount_balances(self, ledger: Ledger, code: str,
                                  close_dt: datetime) -> List[Tuple[str, Decimal, Decimal]]:
        """列出 code 及其所有子科目（以 code 为前缀）的累计 (debit, credit)。

        返回 [(sub_code, debit, credit), ...]，每个子科目一行。
        损益结转必须按子科目分别结平：附加税计提写入 640302/640303/640304，
        必须对每个子科目分别生成结转分录，否则子科目余额会滞留。
        """
        if not ledger:
            return []
        pattern = f"{code}%"
        rows = self.db.query(
            LedgerAccount.code,
            sqlfunc.coalesce(sqlfunc.sum(AccountMoveLine.debit_l2), 0),
            sqlfunc.coalesce(sqlfunc.sum(AccountMoveLine.credit_l2), 0),
        ).join(
            AccountMoveLine, AccountMoveLine.ledger_account_id == LedgerAccount.id
        ).join(
            AccountMove, AccountMoveLine.move_id == AccountMove.id
        ).filter(
            LedgerAccount.ledger_id == ledger.id,
            LedgerAccount.code.like(pattern),
            AccountMove.date_l1 <= close_dt
        ).group_by(LedgerAccount.code).all()
        return [(row[0], _d(row[1]), _d(row[2])) for row in rows]

    def execute(self, account_id: int, period: str, force: bool = False) -> Dict:
        period_start, close_dt = parse_period(period)
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

        # ── 第 2 步：force 模式下先冲红旧凭证（必须在读余额之前）──
        # 冲红后收入/费用余额恢复为原始值 + 新增调整（如附加税），
        # 然后读取的余额才是正确的待结转金额。
        if force:
            # 12月需要先冲红 year_close，否则 4103 余额不正确
            if period_start.month == 12:
                reverse_journal(self.db, account_id, "year_close",
                                period_hash(period, "year_close"),
                                reversal_date=close_dt, force=True)
            reverse_journal(self.db, account_id, "period_close",
                            period_hash(period, "period_close"),
                            reversal_date=close_dt, force=True)

        # ── 第 3 步：取损益科目余额（按子科目分别列出）──
        lines = []
        total_revenue_l1 = Decimal("0")
        total_expense = Decimal("0")

        for code in self.INCOME_CODES:
            # 收入类：贷方余额 → 借方结转
            for sub_code, d, c in self._list_subaccount_balances(ledger, code, close_dt):
                balance = c - d
                amt = balance.quantize(Q2)
                if abs(amt) >= Decimal("0.01"):
                    if balance > 0:
                        lines.append({"account_code": sub_code,
                                      "debit": amt, "credit": Decimal("0")})
                    else:
                        lines.append({"account_code": sub_code,
                                      "debit": Decimal("0"), "credit": abs(amt)})
                    total_revenue_l1 += amt

        for code in self.EXPENSE_CODES:
            # 费用类：借方余额 → 贷方结转
            for sub_code, d, c in self._list_subaccount_balances(ledger, code, close_dt):
                balance = d - c
                amt = balance.quantize(Q2)
                if abs(amt) >= Decimal("0.01"):
                    if balance > 0:
                        lines.append({"account_code": sub_code,
                                      "debit": Decimal("0"), "credit": amt})
                    else:
                        lines.append({"account_code": sub_code,
                                      "debit": abs(amt), "credit": Decimal("0")})
                    total_expense += amt

        # ── 第 4 步：差额进 4103 ──
        net_profit = total_revenue_l1 - total_expense
        if abs(net_profit) >= Decimal("0.01"):
            if net_profit > 0:
                lines.append({"account_code": "4103",
                              "debit": Decimal("0"),
                              "credit": net_profit.quantize(Q2)})
            else:
                lines.append({"account_code": "4103",
                              "debit": abs(net_profit).quantize(Q2),
                              "credit": Decimal("0")})

        # ── 第 5 步：过账 period_close ──
        if lines:
            post_journal(self.db, account_id, "period_close", {
                "lines": lines,
                "date": close_dt,
                "source_model": "period_close",
                "source_id": period_hash(period, "period_close"),
            }, force=force)
            logger.info(f"损益结转 {period}: 收入={total_revenue_l1:.2f} 费用={total_expense:.2f} 净利润={net_profit:.2f}")

        # ── 第 6 步：12月额外 year_close ──
        year_close_result = None
        if period_start.month == 12:
            year_close_result = self._execute_year_close(
                ledger, account_id, period, close_dt, force
            )

        return {
            "status": "ok",
            "period": period,
            "total_revenue_l1": float(total_revenue_l1),
            "total_expense": float(total_expense),
            "net_profit": float(net_profit),
            "year_close": year_close_result,
        }

    def _execute_year_close(self, ledger: Ledger, account_id: int,
                            period: str, close_dt: datetime,
                            force: bool) -> Dict:
        # 注意：year_close 的冲红已在 execute() Step 2 中完成（force 模式下）
        # 此处只需读取 4103 余额并过账新的 year_close

        # 4103 无子科目，但用 _list_subaccount_balances 保持口径一致
        # 取列表第一项（4103 自身）；列表为空表示无 4103 科目
        rows = self._list_subaccount_balances(ledger, "4103", close_dt)
        if rows:
            _, d, c = rows[0]
        else:
            d, c = Decimal("0"), Decimal("0")
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

        post_journal(self.db, account_id, "year_close", {
            "lines": year_lines,
            "date": close_dt,
            "source_model": "year_close",
            "source_id": period_hash(period, "year_close"),
        }, force=force)

        logger.info(f"年结 {period}: 4103→4104 结转 {balance_4103:.2f}")
        return {
            "status": "ok",
            "transferred": float(balance_4103),
        }
