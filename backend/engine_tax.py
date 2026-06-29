"""月结核心税务计算与凭证生成引擎

按需结账，账表同源。补充结账支持历史月份，跨期冲回所得税。
"""

import logging
from calendar import monthrange
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Dict

from sqlalchemy.orm import Session
from sqlalchemy import func as sqlfunc

from models_finance import Ledger, LedgerAccount, AccountMove, AccountMoveLine
from finance_integration import post_journal
from utils import _d, Q2

logger = logging.getLogger("inventory")


def _l(db: Session, ledger: Ledger, code: str, cutoff: datetime):
    if not ledger:
        return Decimal("0"), Decimal("0")
    d = _d(db.query(sqlfunc.coalesce(sqlfunc.sum(AccountMoveLine.debit), 0)).join(
        LedgerAccount, AccountMoveLine.ledger_account_id == LedgerAccount.id
    ).join(AccountMove, AccountMoveLine.move_id == AccountMove.id).filter(
        LedgerAccount.ledger_id == ledger.id, LedgerAccount.code == code,
        AccountMove.date <= cutoff).scalar())
    c = _d(db.query(sqlfunc.coalesce(sqlfunc.sum(AccountMoveLine.credit), 0)).join(
        LedgerAccount, AccountMoveLine.ledger_account_id == LedgerAccount.id
    ).join(AccountMove, AccountMoveLine.move_id == AccountMove.id).filter(
        LedgerAccount.ledger_id == ledger.id, LedgerAccount.code == code,
        AccountMove.date <= cutoff).scalar())
    return d, c


def _lp(db: Session, ledger: Ledger, code: str, start: datetime, end: datetime):
    if not ledger:
        return Decimal("0"), Decimal("0")
    d = _d(db.query(sqlfunc.coalesce(sqlfunc.sum(AccountMoveLine.debit), 0)).join(
        LedgerAccount, AccountMoveLine.ledger_account_id == LedgerAccount.id
    ).join(AccountMove, AccountMoveLine.move_id == AccountMove.id).filter(
        LedgerAccount.ledger_id == ledger.id, LedgerAccount.code == code,
        AccountMove.date >= start, AccountMove.date <= end).scalar())
    c = _d(db.query(sqlfunc.coalesce(sqlfunc.sum(AccountMoveLine.credit), 0)).join(
        LedgerAccount, AccountMoveLine.ledger_account_id == LedgerAccount.id
    ).join(AccountMove, AccountMoveLine.move_id == AccountMove.id).filter(
        LedgerAccount.ledger_id == ledger.id, LedgerAccount.code == code,
        AccountMove.date >= start, AccountMove.date <= end).scalar())
    return d, c


def _bal(db, ledger, code, cutoff):
    d, c = _l(db, ledger, code, cutoff)
    return d - c


def _crd(db, ledger, code, cutoff):
    d, c = _l(db, ledger, code, cutoff)
    return c - d


class TaxAccrualEngine:

    def __init__(self, db: Session):
        self.db = db

    def execute(self, account_id: int, period: str, taxpayer_type: str = "") -> Dict:
        period_start, close_dt = _parse_period(period)

        import models
        account = self.db.query(models.Account).filter(
            models.Account.id == account_id
        ).first()
        ledger = account and self.db.query(Ledger).filter(
            Ledger.code == account.code
        ).first()
        if not ledger:
            return {"status": "error", "msg": "总账未初始化"}
        if not taxpayer_type:
            taxpayer_type = account.taxpayer_type if account else "small_scale"

        closed = self._has_closed(ledger, period)
        if closed["surcharge"] and closed["income_tax"]:
            return {"status": "skipped", "msg": f"期 {period} 已结账", "detail": closed}

        result_lines = []

        # ── VAT 计算（按纳税人类型分流）──
        if taxpayer_type == "small_scale":
            # 小规模纳税人：销项税在 222103，不能抵扣进项，不走转出未交增值税
            _, output_vat = _lp(self.db, ledger, "222103", period_start, close_dt)
            curr_vat = output_vat  # 应交增值税 = 销项税（全额）
            input_vat = Decimal("0")
            carry_forward = Decimal("0")
        else:
            # 一般纳税人：222101(销项) - 222102(进项)，考虑留抵
            _, output_vat = _lp(self.db, ledger, "222101", period_start, close_dt)
            in_d, _ = _lp(self.db, ledger, "222102", period_start, close_dt)
            input_vat = in_d

            prev_input_end = period_start - timedelta(seconds=1)
            prev_input_total = _bal(self.db, ledger, "222102", prev_input_end)
            prev_output_total = _crd(self.db, ledger, "222101", prev_input_end)
            carry_forward = max(prev_input_total - prev_output_total, Decimal("0"))

            curr_vat = max(output_vat - carry_forward - input_vat, Decimal("0"))

        if curr_vat > Decimal("0") and not closed["surcharge"]:
            surcharge_amt = (curr_vat * Decimal("0.12")).quantize(Q2)
            if surcharge_amt > 0:
                post_journal(self.db, account_id, "tax_surcharge", {
                    "amount": surcharge_amt,
                    "date": close_dt,
                    "source_model": "tax_surcharge",
                    "source_id": _period_hash(period, "surcharge"),
                })
                result_lines.append(f"附加税: +{surcharge_amt}")
                logger.info(f"月结 {period} 计提附加税: {surcharge_amt}")

            # VAT 结转：仅一般纳税人执行（222101→222106→222107）
            # 小规模纳税人 222103 本身就是应交增值税，无需结转
            if taxpayer_type != "small_scale":
                post_journal(self.db, account_id, "vat_transfer_out", {
                    "amount": curr_vat,
                    "date": close_dt,
                    "source_model": "vat_transfer_out",
                    "source_id": _period_hash(period, "vat_xfer"),
                })
                logger.info(f"月结 {period} 转出未交增值税: {curr_vat}")

        # 小规模纳税人减免税结转（季度末月：3/6/9/12）
        # 依据：财税〔2008〕151号 — 减免的增值税需计入营业外收入缴企业所得税
        # 实务：小规模按季申报，季度末确认减免额，借222103 贷6301
        if taxpayer_type == "small_scale" and period_start.month in (3, 6, 9, 12):
            exemption_closed = self.db.query(AccountMove).filter(
                AccountMove.ledger_id == ledger.id,
                AccountMove.source_model == "vat_exemption",
                AccountMove.date >= period_start,
                AccountMove.date <= close_dt,
            ).first() is not None
            if not exemption_closed:
                # 计算季度总不含税销售额（从发票汇总）
                import models
                from enums import InvoiceDirection
                quarter_start_month = period_start.month - 2  # 季度首月
                q_start = datetime(period_start.year, quarter_start_month, 1, 0, 0, 0)
                quarterly_revenue = _d(self.db.query(sqlfunc.sum(models.Invoice.amount_without_tax)).filter(
                    models.Invoice.account_id == account_id,
                    models.Invoice.direction == InvoiceDirection.OUT,
                models.Invoice.issue_date >= q_start,
                models.Invoice.issue_date <= close_dt,
                ).scalar())

                # 季度销项税总额（222103贷方发生额）
                _, quarter_output_vat = _lp(self.db, ledger, "222103", q_start, close_dt)

                QUARTERLY_EXEMPTION = Decimal("300000")
                if quarterly_revenue <= QUARTERLY_EXEMPTION:
                    # 季度≤30万：全额免征（普票免税，专票减按1%）
                    # 简化：按全额减免处理（专票部分实际需缴纳，此处取减征额）
                    exemption_amt = quarter_output_vat  # 全额减免
                else:
                    # 超过30万：减按1%征收，减免2%
                    exemption_amt = (quarterly_revenue * Decimal("0.02")).quantize(Q2)

                if exemption_amt > 0:
                    post_journal(self.db, account_id, "vat_exemption", {
                        "amount": exemption_amt,
                        "date": close_dt,
                        "source_model": "vat_exemption",
                        "source_id": _period_hash(period, "exemption"),
                    })
                    result_lines.append(f"增值税减免结转: {exemption_amt} → 营业外收入")
                    logger.info(f"月结 {period} 增值税减免结转: {exemption_amt}")

        revenue = _crd(self.db, ledger, "6001", close_dt) + _crd(self.db, ledger, "6051", close_dt)
        cogs = _bal(self.db, ledger, "6401", close_dt)
        opex = (_bal(self.db, ledger, "6601", close_dt)
                + _bal(self.db, ledger, "6602", close_dt)
                + _bal(self.db, ledger, "6603", close_dt)
                + _bal(self.db, ledger, "6403", close_dt))
        non_op_income = _crd(self.db, ledger, "6301", close_dt) + _crd(self.db, ledger, "6111", close_dt)
        non_op_expense = _bal(self.db, ledger, "6701", close_dt) + _bal(self.db, ledger, "6711", close_dt)
        cumulative_profit = revenue - cogs - opex + non_op_income - non_op_expense

        # 个体工商户不缴企业所得税（缴个人所得税，系统不处理个税）
        # 依据：《个体工商户个人所得税计税办法》
        entity_type = account.type if account and account.type else "company"
        if entity_type == "personal":
            result_lines.append("个体工商户：不计提企业所得税（缴个人所得税）")
            return {
                "status": "ok",
                "period": period,
                "curr_vat": float(curr_vat),
                "cumulative_profit": float(cumulative_profit),
                "target_income_tax": 0,
                "posted_income_tax": float(_crd(self.db, ledger, "222105", close_dt)),
                "lines": result_lines,
            }

        income_tax_rate = Decimal("0.25") if taxpayer_type == "general" else Decimal("0.05")
        target_tax = max(cumulative_profit * income_tax_rate, Decimal("0")).quantize(Q2)
        posted_tax = _crd(self.db, ledger, "222105", close_dt)
        delta = target_tax - posted_tax

        if abs(delta) > Decimal("0.01") and not closed["income_tax"]:
            if delta > Decimal("0"):
                post_journal(self.db, account_id, "tax_income", {
                    "amount": delta,
                    "date": close_dt,
                    "source_model": "tax_income",
                    "source_id": _period_hash(period, "income"),
                })
                result_lines.append(f"所得税: +{delta}")
                logger.info(f"月结 {period} 计提所得税: +{delta}")
            else:
                post_journal(self.db, account_id, "tax_income_reversal", {
                    "amount": abs(delta),
                    "date": close_dt,
                    "source_model": "tax_income_reversal",
                    "source_id": _period_hash(period, "income_rev"),
                })
                result_lines.append(f"所得税: -{abs(delta)} (冲回)")
                logger.info(f"月结 {period} 冲回所得税: {abs(delta)}")

        return {
            "status": "ok",
            "period": period,
            "curr_vat": float(curr_vat),
            "cumulative_profit": float(cumulative_profit),
            "target_income_tax": float(target_tax),
            "posted_income_tax": float(posted_tax),
            "lines": result_lines,
        }

    def _has_closed(self, ledger: Ledger, period: str) -> Dict[str, bool]:
        period_start, period_end = _parse_period(period)
        surcharge_exists = self.db.query(AccountMove).filter(
            AccountMove.ledger_id == ledger.id,
            AccountMove.source_model == "tax_surcharge",
            AccountMove.date >= period_start,
            AccountMove.date <= period_end,
        ).first() is not None

        income_exists = self.db.query(AccountMove).filter(
            AccountMove.ledger_id == ledger.id,
            AccountMove.source_model == "tax_income",
            AccountMove.date >= period_start,
            AccountMove.date <= period_end,
        ).first() is not None

        return {"surcharge": surcharge_exists, "income_tax": income_exists}


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
        h &= 0x7FFFFFFF
    return h
