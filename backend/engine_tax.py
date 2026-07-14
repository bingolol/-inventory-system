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
from lineage import reads, TIER_L3
from policy.entity_profile import build_profile, EntityProfile, resolve_taxpayer_type_by_date
from policy.vat_facts import load_vat_facts
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
                                surcharge_halved_l3=account.surcharge_halved_l3 if account else None) if account else EntityProfile(
            vat_type="small_scale", income_type="small_micro", surcharge_halved_l3=True, effective_date=period_start.date()
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
            carry_forward_l1 = Decimal("0")
        else:
            out_d, out_c = sn.biz_dc("222101", period_start, close_dt)
            output_vat = out_c - out_d
            in_d, in_c = sn.biz_dc("222102", period_start, close_dt)
            input_vat = in_d - in_c

            prev_input_end = period_start - timedelta(seconds=1)
            prev_input_total = sn.bal_at("222102", prev_input_end)
            prev_output_total = sn.crd_at("222101", prev_input_end)
            carry_forward_l1 = max(prev_input_total - prev_output_total, Decimal("0"))

            curr_vat = max(output_vat - carry_forward_l1 - input_vat, Decimal("0"))

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
                # 兼容 issue_date_l1 存储为 date 或 datetime 的混合情况
                def _to_datetime(d):
                    if hasattr(d, 'hour'):
                        return d
                    return datetime(d.year, d.month, d.day)
                invs = [inv for inv in sn.invoices()
                        if inv.direction == InvoiceDirection.OUT
                        and _to_datetime(inv.issue_date_l1) >= q_start
                        and _to_datetime(inv.issue_date_l1) <= close_dt]

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

        # ── 所得税计算（委托 IncomeTaxEngine）──
        from engine_income_tax import IncomeTaxEngine
        r = IncomeTaxEngine(self.db).calculate(account_id, period)

        rate_info = r.trace.get("rate", {})
        reason = rate_info.get("reason", "")
        reduction = rate_info.get("reduction", "")
        if reason:
            result_lines.append(reason)
        if reduction:
            result_lines.append(f"所得税减免: {reduction}")

        if r.tax_rate_l2 > 0 and abs(r.delta_l2) > Decimal("0.01"):
            if r.delta_l2 > Decimal("0"):
                post_journal(self.db, account_id, "tax_income", {
                    "amount": r.delta_l2,
                    "date": close_dt,
                    "source_model": "tax_income",
                    "source_id": period_hash(period, "income"),
                })
                result_lines.append(f"所得税: +{r.delta_l2}")
                logger.info(f"月结 {period} 计提所得税: +{r.delta_l2}")
            else:
                post_journal(self.db, account_id, "tax_income_reversal", {
                    "amount": abs(r.delta_l2),
                    "date": close_dt,
                    "source_model": "tax_income_reversal",
                    "source_id": period_hash(period, "income_rev"),
                })
                result_lines.append(f"所得税: -{abs(r.delta_l2)} (冲回)")
                logger.info(f"月结 {period} 冲回所得税: {abs(r.delta_l2)}")

        return {
            "status": "ok",
            "period": period,
            "curr_vat": float(curr_vat),
            "cumulative_profit": float(r.profit_l2),
            "target_income_tax": float(r.tax_payable_l2),
            "posted_income_tax": float(r.posted_l2),
            "lines": result_lines,
        }
