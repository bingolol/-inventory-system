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
from lineage import reads, TIER_L3

logger = logging.getLogger("inventory")


def _l(db: Session, ledger: Ledger, code: str, cutoff: datetime):
    if not ledger:
        return Decimal("0"), Decimal("0")
    d = _d(db.query(sqlfunc.coalesce(sqlfunc.sum(AccountMoveLine.debit_l2), 0)).join(
        LedgerAccount, AccountMoveLine.ledger_account_id == LedgerAccount.id
    ).join(AccountMove, AccountMoveLine.move_id == AccountMove.id).filter(
        LedgerAccount.ledger_id == ledger.id, LedgerAccount.code == code,
        AccountMove.date_l1 <= cutoff).scalar())
    c = _d(db.query(sqlfunc.coalesce(sqlfunc.sum(AccountMoveLine.credit_l2), 0)).join(
        LedgerAccount, AccountMoveLine.ledger_account_id == LedgerAccount.id
    ).join(AccountMove, AccountMoveLine.move_id == AccountMove.id).filter(
        LedgerAccount.ledger_id == ledger.id, LedgerAccount.code == code,
        AccountMove.date_l1 <= cutoff).scalar())
    return d, c


def _lp(db: Session, ledger: Ledger, code: str, start: datetime, end: datetime):
    if not ledger:
        return Decimal("0"), Decimal("0")
    d = _d(db.query(sqlfunc.coalesce(sqlfunc.sum(AccountMoveLine.debit_l2), 0)).join(
        LedgerAccount, AccountMoveLine.ledger_account_id == LedgerAccount.id
    ).join(AccountMove, AccountMoveLine.move_id == AccountMove.id).filter(
        LedgerAccount.ledger_id == ledger.id, LedgerAccount.code == code,
        AccountMove.date_l1 >= start, AccountMove.date_l1 <= end).scalar())
    c = _d(db.query(sqlfunc.coalesce(sqlfunc.sum(AccountMoveLine.credit_l2), 0)).join(
        LedgerAccount, AccountMoveLine.ledger_account_id == LedgerAccount.id
    ).join(AccountMove, AccountMoveLine.move_id == AccountMove.id).filter(
        LedgerAccount.ledger_id == ledger.id, LedgerAccount.code == code,
        AccountMove.date_l1 >= start, AccountMove.date_l1 <= end).scalar())
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

    @reads("Account.taxpayer_type_l3", tier=TIER_L3, source="policy")
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
            taxpayer_type = account.taxpayer_type_l3 if account else "small_scale"

        closed = self._has_closed(ledger, period)
        # 修复 #1：移除顶层"已结账则跳过"守卫，改为允许补提差额
        # 原代码 closed["surcharge"] and closed["income_tax"] 都为 True 时直接 skip，
        # 导致后续利润变动后无法补提所得税/附加税差额。
        # 现在改为：不在此处 skip，由后续各税种的 delta 判断决定是否需要补提。

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
            # 销项税净额 = 贷方(销售销项) - 借方(退货冲红/红字发票冲减)
            out_d, out_c = _lp(self.db, ledger, "222101", period_start, close_dt)
            output_vat = out_c - out_d  # 净销项 = 贷方 - 借方(退货冲红)
            # 进项税净额 = 借方(采购进项) - 贷方(退货冲红/进项转出)
            in_d, in_c = _lp(self.db, ledger, "222102", period_start, close_dt)
            input_vat = in_d - in_c  # 净进项 = 借方 - 贷方(退货冲红)

            prev_input_end = period_start - timedelta(seconds=1)
            prev_input_total = _bal(self.db, ledger, "222102", prev_input_end)
            prev_output_total = _crd(self.db, ledger, "222101", prev_input_end)
            carry_forward = max(prev_input_total - prev_output_total, Decimal("0"))

            curr_vat = max(output_vat - carry_forward - input_vat, Decimal("0"))

        if curr_vat > Decimal("0"):
            # 修复 #1：附加税用 delta 模式，避免已计提后补提失效
            # 按最新政策拆分：城建税7%、教育费附加3%、地方教育附加2%；小规模纳税人减半（2023-2027）
            surcharge_reduction = Decimal("0.5") if taxpayer_type == "small_scale" else Decimal("1")
            surcharge_taxes = {
                "640302": (curr_vat * Decimal("0.07") * surcharge_reduction).quantize(Q2),  # 城建税
                "640303": (curr_vat * Decimal("0.03") * surcharge_reduction).quantize(Q2),  # 教育费附加
                "640304": (curr_vat * Decimal("0.02") * surcharge_reduction).quantize(Q2),  # 地方教育附加
            }
            target_surcharge = sum(surcharge_taxes.values())

            # delta 按明细科目分别计算，支持补提差额
            taxes_delta = {}
            for expense_code, target in surcharge_taxes.items():
                payable_code = {
                    "640302": "222110",
                    "640303": "222111",
                    "640304": "222112",
                }[expense_code]
                posted = _crd(self.db, ledger, payable_code, close_dt)
                delta = target - posted
                if delta > Decimal("0.01"):
                    taxes_delta[expense_code] = delta

            if taxes_delta:
                post_journal(self.db, account_id, "tax_surcharge", {
                    "taxes": taxes_delta,
                    "date": close_dt,
                    "source_model": "tax_surcharge",
                    "source_id": _period_hash(period, "surcharge"),
                }, force=closed["surcharge"])
                result_lines.append(f"附加税: +{sum(taxes_delta.values())}")
                logger.info(f"月结 {period} 计提附加税: {taxes_delta}")

            # VAT 结转：仅一般纳税人执行（222101→222106→222107）
            # 小规模纳税人 222103 本身就是应交增值税，无需结转
            # 修复 #1：移除对 closed["surcharge"] 的依赖，VAT 结转用自身幂等
            if taxpayer_type != "small_scale":
                # 检查是否已结转过（避免重复）
                vat_xfer_exists = self.db.query(AccountMove).filter(
                    AccountMove.ledger_id == ledger.id,
                    AccountMove.source_model == "vat_transfer_out",
                    AccountMove.date_l1 >= period_start,
                    AccountMove.date_l1 <= close_dt,
                ).first() is not None
                if not vat_xfer_exists:
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
                AccountMove.date_l1 >= period_start,
                AccountMove.date_l1 <= close_dt,
            ).first() is not None
            if not exemption_closed:
                # 计算季度总不含税销售额（从发票汇总）
                import models
                from enums import InvoiceDirection
                quarter_start_month = period_start.month - 2  # 季度首月
                q_start = datetime(period_start.year, quarter_start_month, 1, 0, 0, 0)
                quarterly_revenue = _d(self.db.query(sqlfunc.sum(models.Invoice.amount_without_tax_l1)).filter(
                    models.Invoice.account_id == account_id,
                    models.Invoice.direction == InvoiceDirection.OUT,
                models.Invoice.issue_date_l1 >= q_start,
                models.Invoice.issue_date_l1 <= close_dt,
                ).scalar())

                # 季度销项税总额（222103贷方发生额）
                _, quarter_output_vat = _lp(self.db, ledger, "222103", q_start, close_dt)

                QUARTERLY_EXEMPTION = Decimal("300000")
                if quarterly_revenue <= QUARTERLY_EXEMPTION:
                    # 修复 #4：区分普票和专票
                    # 原代码 exemption_amt = quarter_output_vat（全额免），
                    # 导致专票部分也被全额免税（应减按1%缴纳）。
                    # 正确：普票全额免，专票减按1%（减免2%）
                    from enums import InvoiceType
                    ordinary_rev = _d(self.db.query(sqlfunc.sum(models.Invoice.amount_without_tax_l1)).filter(
                        models.Invoice.account_id == account_id,
                        models.Invoice.direction == InvoiceDirection.OUT,
                        models.Invoice.invoice_type == InvoiceType.ORDINARY,
                        models.Invoice.issue_date_l1 >= q_start,
                        models.Invoice.issue_date_l1 <= close_dt,
                    ).scalar())
                    special_rev = _d(self.db.query(sqlfunc.sum(models.Invoice.amount_without_tax_l1)).filter(
                        models.Invoice.account_id == account_id,
                        models.Invoice.direction == InvoiceDirection.OUT,
                        models.Invoice.invoice_type == InvoiceType.SPECIAL,
                        models.Invoice.issue_date_l1 >= q_start,
                        models.Invoice.issue_date_l1 <= close_dt,
                    ).scalar())

                    # 普票全额免：已记的1%销项税转出至营业外收入
                    exemption_amt = (ordinary_rev * Decimal("0.01")).quantize(Q2)
                else:
                    # 超过30万：全部减按1%征收
                    # 销售时已按1%记销项税，实际就是应缴税额，无需减免结转
                    exemption_amt = Decimal("0")

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
        # 小企业准则：固定资产处置损益计入营业外收支(6301/6701)，不使用"资产处置损益"(6111/6711)
        non_op_income = _crd(self.db, ledger, "6301", close_dt)
        non_op_expense = _bal(self.db, ledger, "6701", close_dt)
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

        # 调用 AccountingEngine.calculate_income_tax 计算所得税（与所得税报表同一真相源）
        # 修复：原代码直接将 VAT 口径 taxpayer_type 映射为所得税率，绕过了小型微利企业的
        # 利润门槛判断（≤300万 → 5%，>300万 → 25%），导致小规模+利润>300万少计提80%。
        # 类型映射规则（与 routers/income_tax.py:142-143 一致）：
        #   VAT small_scale → 所得税 small_micro
        #   VAT general → 所得税 general
        # 注：calculate_income_tax 内部已处理 entity_type=personal → 不计提、profit<0 → 0 的兜底
        from accounting_engine import AccountingEngine
        income_tax_type = "small_micro" if taxpayer_type in ("small_scale", "small_micro") else "general"
        income_tax_result = AccountingEngine().calculate_income_tax(
            profit=cumulative_profit,
            taxpayer_type=income_tax_type,
            entity_type=entity_type,
        )
        target_tax = income_tax_result.tax_payable
        if income_tax_result.reduction_item:
            result_lines.append(f"所得税减免说明: {income_tax_result.reduction_item}")
        posted_tax = _crd(self.db, ledger, "222105", close_dt)
        delta = target_tax - posted_tax

        if abs(delta) > Decimal("0.01"):
            # 修复 #1：移除 not closed["income_tax"] 守卫，允许补提差额
            # 原代码在已存在 tax_income 凭证时跳过补提，导致跨期补录利润变动后
            # 所得税永久漏提。现在：首次用普通过账（幂等），后续用 force=True 补提差额。
            if delta > Decimal("0"):
                post_journal(self.db, account_id, "tax_income", {
                    "amount": delta,
                    "date": close_dt,
                    "source_model": "tax_income",
                    "source_id": _period_hash(period, "income"),
                }, force=closed["income_tax"])
                result_lines.append(f"所得税: +{delta}")
                logger.info(f"月结 {period} 计提所得税: +{delta}")
            else:
                # 冲回分支也需要 force，否则第二次冲回被幂等拦截
                income_rev_exists = self.db.query(AccountMove).filter(
                    AccountMove.ledger_id == ledger.id,
                    AccountMove.source_model == "tax_income_reversal",
                    AccountMove.date_l1 >= period_start,
                    AccountMove.date_l1 <= close_dt,
                ).first() is not None
                post_journal(self.db, account_id, "tax_income_reversal", {
                    "amount": abs(delta),
                    "date": close_dt,
                    "source_model": "tax_income_reversal",
                    "source_id": _period_hash(period, "income_rev"),
                }, force=income_rev_exists)
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
            AccountMove.date_l1 >= period_start,
            AccountMove.date_l1 <= period_end,
        ).first() is not None

        income_exists = self.db.query(AccountMove).filter(
            AccountMove.ledger_id == ledger.id,
            AccountMove.source_model == "tax_income",
            AccountMove.date_l1 >= period_start,
            AccountMove.date_l1 <= period_end,
        ).first() is not None

        return {"surcharge": surcharge_exists, "income_tax": income_exists}


def _parse_period(period: str):
    year, month = int(period[:4]), int(period[5:7])
    _, last_day = monthrange(year, month)
    start_dt = datetime(year, month, 1, 0, 0, 0)
    end_dt = datetime(year, month, last_day, 23, 59, 59)
    return start_dt, end_dt


def _period_hash(period: str, tag: str) -> int:
    # 修复 #3：扩展哈希空间从 31 位到 63 位，降低碰撞风险
    h = 0
    for c in f"{period}_{tag}":
        h = ((h << 5) - h) + ord(c)
        h &= 0x7FFFFFFFFFFFFFFF  # 63 位空间（2^63-1 ≈ 9.2×10^18）
    return h
