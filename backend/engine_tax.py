"""月结核心税务计算与凭证生成引擎

按需结账，账表同源。补充结账支持历史月份，跨期冲回所得税。
"""

import logging
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Dict

from sqlalchemy.orm import Session
from sqlalchemy import func as sqlfunc

from models_finance import Ledger, AccountMove
from finance_integration import post_journal
from utils import _d, Q2
from utils.period import parse_period, period_hash
from crud.finance._snapshot import LedgerSnapshot
from crud.finance._profit import compute_cumulative_profit
from lineage import reads, TIER_L3
from policy.entity_profile import build_profile, EntityProfile, resolve_taxpayer_type_by_date
from policy.policy_engine import (
    calculate_income_tax as policy_income_tax,
)
from policy.vat_facts import load_vat_facts
from policy.income_tax_facts import load_income_tax_facts
from enums import InvoiceDirection

logger = logging.getLogger("inventory")


class TaxAccrualEngine:

    def __init__(self, db: Session):
        self.db = db

    @reads("Account.taxpayer_type_l3", tier=TIER_L3, source="policy")
    def execute(self, account_id: int, period: str, taxpayer_type: str = "") -> Dict:
        period_start, close_dt = parse_period(period)

        import models
        account = self.db.query(models.Account).filter(
            models.Account.id == account_id
        ).first()
        vat_type_ov = resolve_taxpayer_type_by_date(account, self.db, period_start.date()) if account else None
        profile = build_profile(account, period_start.date(), vat_type_override=vat_type_ov,
                                surcharge_halved=account.surcharge_halved if account else None) if account else EntityProfile(
            vat_type="small_scale", income_type="small_micro", surcharge_halved=True, effective_date=period_start.date()
        )
        ledger = account and self.db.query(Ledger).filter(
            Ledger.code == account.code
        ).first()
        if not ledger:
            return {"status": "error", "msg": "总账未初始化"}

        sn = LedgerSnapshot(self.db, account_id, bs_cutoff=close_dt, period_start=period_start, period_end=close_dt)

        result_lines = []

        # ── VAT 计算（按主体画像分流）──
        if profile.vat_type == "small_scale":
            _, output_vat = sn.biz_dc("222103", period_start, close_dt)
            curr_vat = output_vat
            input_vat = Decimal("0")
            carry_forward = Decimal("0")
        else:
            out_d, out_c = sn.biz_dc("222101", period_start, close_dt)
            output_vat = out_c - out_d
            in_d, in_c = sn.biz_dc("222102", period_start, close_dt)
            input_vat = in_d - in_c

            prev_input_end = period_start - timedelta(seconds=1)
            prev_input_total = sn.bal_at("222102", prev_input_end)
            prev_output_total = sn.crd_at("222101", prev_input_end)
            carry_forward = max(prev_input_total - prev_output_total, Decimal("0"))

            curr_vat = max(output_vat - carry_forward - input_vat, Decimal("0"))

        if curr_vat > Decimal("0"):
            if profile.vat_type != "small_scale":
                vat_xfer_exists = sn.move_exists("vat_transfer_out", period_start, close_dt)
                if not vat_xfer_exists:
                    post_journal(self.db, account_id, "vat_transfer_out", {
                        "amount": curr_vat,
                        "date": close_dt,
                        "source_model": "vat_transfer_out",
                        "source_id": period_hash(period, "vat_xfer"),
                    })
                    logger.info(f"月结 {period} 转出未交增值税: {curr_vat}")

        if profile.vat_type == "small_scale" and period_start.month in (3, 6, 9, 12):
            exemption_closed = sn.move_exists("vat_exemption", period_start, close_dt)
            if not exemption_closed:
                import models
                quarter_start_month = period_start.month - 2
                q_start = datetime(period_start.year, quarter_start_month, 1, 0, 0, 0)
                invs = [inv for inv in sn.invoices()
                        if inv.direction == InvoiceDirection.OUT
                        and inv.issue_date_l1 >= q_start
                        and inv.issue_date_l1 <= close_dt]

                quarterly_revenue = _d(sum(_d(inv.amount_without_tax_l1) for inv in invs))

                from enums import InvoiceType
                ordinary_rev = _d(sum(_d(inv.amount_without_tax_l1) for inv in invs
                                      if inv.invoice_type == InvoiceType.ORDINARY))
                special_rev = _d(sum(_d(inv.amount_without_tax_l1) for inv in invs
                                      if inv.invoice_type == InvoiceType.SPECIAL))

                vat_facts_data = load_vat_facts(period_start.date())
                if quarterly_revenue <= vat_facts_data.small_scale_quarterly_exemption:
                    exemption_amt = (ordinary_rev * vat_facts_data.small_scale_reduced_rate).quantize(Q2)
                else:
                    exemption_amt = Decimal("0")

                if exemption_amt > 0:
                    post_journal(self.db, account_id, "vat_exemption", {
                        "amount": exemption_amt,
                        "date": close_dt,
                        "source_model": "vat_exemption",
                        "source_id": period_hash(period, "exemption"),
                    })
                    result_lines.append(f"增值税减免结转: {exemption_amt} → 营业外收入")
                    logger.info(f"月结 {period} 增值税减免结转: {exemption_amt}")

        # 所得税计算前刷新 snapshot
        sn = LedgerSnapshot(self.db, account_id, bs_cutoff=close_dt,
                            period_start=period_start, period_end=close_dt)

        year_start = datetime(period_start.year, 1, 1, 0, 0, 0)
        cumulative_profit = compute_cumulative_profit(sn, year_start, close_dt)

        ytd_debit, ytd_credit, _ = sn.trace_per_dc("222105", year_start, close_dt)
        posted_tax = (ytd_credit - ytd_debit).quantize(Decimal("0.01"))

        if profile.income_type == "personal":
            result_lines.append("个体工商户：不计提企业所得税（缴个人所得税）")
            return {
                "status": "ok",
                "period": period,
                "curr_vat": float(curr_vat),
                "cumulative_profit": float(cumulative_profit),
                "target_income_tax": 0,
                "posted_income_tax": float(posted_tax),
                "lines": result_lines,
            }

        if profile.income_type == "general":
            income_facts_data = load_income_tax_facts(period_start.date())
            from policy.entity_profile import refine_small_micro
            profile = refine_small_micro(profile, cumulative_profit, income_facts_data.small_micro_threshold)

        income_tax_result = policy_income_tax(
            profile=profile,
            profit=cumulative_profit,
        )
        target_tax = income_tax_result.tax_payable
        if income_tax_result.reduction_item:
            result_lines.append(f"所得税减免: {income_tax_result.reduction_item}（减{income_tax_result.reduction_amount}）")
        delta = target_tax - posted_tax

        if abs(delta) > Decimal("0.01"):
            if delta > Decimal("0"):
                post_journal(self.db, account_id, "tax_income", {
                    "amount": delta,
                    "date": close_dt,
                    "source_model": "tax_income",
                    "source_id": period_hash(period, "income"),
                })
                result_lines.append(f"所得税: +{delta}")
                logger.info(f"月结 {period} 计提所得税: +{delta}")
            else:
                post_journal(self.db, account_id, "tax_income_reversal", {
                    "amount": abs(delta),
                    "date": close_dt,
                    "source_model": "tax_income_reversal",
                    "source_id": period_hash(period, "income_rev"),
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
