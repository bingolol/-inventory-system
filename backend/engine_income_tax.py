"""所得税计算引擎 — 纯计算，不写入。"""

from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from typing import Dict, List

from sqlalchemy.orm import Session

from crud.finance._snapshot import LedgerSnapshot
from crud.finance._profit import (
    REVENUE_CODES, COST_CODES, EXPENSE_CODES, SURCHARGE_SUB_CODES,
    NON_OP_INCOME_CODES, NON_OP_EXPENSE_CODES,
    compute_cumulative_profit,
)
from lineage import reads, TIER_L2, TIER_L3
from policy.entity_profile import build_profile, resolve_taxpayer_type_by_date, refine_small_micro
from policy.policy_engine import calculate_income_tax as policy_income_tax
from policy.income_tax_facts import load_income_tax_facts
from utils import Q2
from utils.period import parse_period


@dataclass
class IncomeTaxResult:
    """所得税计算结果 — 全部 _l2 后缀"""
    profit_l2: Decimal
    tax_rate_l2: Decimal
    tax_payable_l2: Decimal
    posted_l2: Decimal
    delta_l2: Decimal
    trace: dict = field(default_factory=dict)
    """{profit, rate, posted} 三组明细，可 JSON 序列化"""


class IncomeTaxEngine:
    """只算不写。caller 拿 delta_l2 决定是否过账。"""

    def __init__(self, db: Session):
        self.db = db

    @reads("AccountMoveLine.debit_l2", tier=TIER_L2, source="engine")
    @reads("AccountMoveLine.credit_l2", tier=TIER_L2, source="engine")
    @reads("Account.taxpayer_type_l3", tier=TIER_L3, source="policy")
    def calculate(self, account_id: int, period: str) -> IncomeTaxResult:
        period_start, close_dt = parse_period(period)
        year_start = datetime(period_start.year, 1, 1)

        import models
        account = self.db.query(models.Account).filter(models.Account.id == account_id).first()
        vat_ov = resolve_taxpayer_type_by_date(account, self.db, period_start.date()) if account else None
        profile = build_profile(account, period_start.date(), vat_type_override=vat_ov,
                                surcharge_halved_l3=account.surcharge_halved_l3 if account else None)

        sn = LedgerSnapshot(self.db, account_id, bs_cutoff=close_dt,
                            period_start=period_start, period_end=close_dt)

        # ── 1. 利润 + 科目明细 ──
        profit_trace = {}
        for code in REVENUE_CODES:
            d, c, _ = sn.trace_pnl_dc(code, year_start, close_dt)
            profit_trace[code] = {"debit": float(d), "credit": float(c), "net": float(c - d)}
        for code in COST_CODES:
            d, c, _ = sn.trace_pnl_dc(code, year_start, close_dt)
            profit_trace[code] = {"debit": float(d), "credit": float(c), "net": float(d - c)}
        for code in EXPENSE_CODES:
            d, c, _ = sn.trace_pnl_dc(code, year_start, close_dt)
            net = d - c
            if code == "6403" and net == Decimal("0"):
                for sub in SURCHARGE_SUB_CODES:
                    sd, sc, _ = sn.trace_pnl_dc(sub, year_start, close_dt)
                    net += sd - sc
            profit_trace[code] = {"debit": float(d), "credit": float(c), "net": float(net)}
        for code in NON_OP_INCOME_CODES:
            d, c, _ = sn.trace_pnl_dc(code, year_start, close_dt)
            profit_trace[code] = {"debit": float(d), "credit": float(c), "net": float(c - d)}
        for code in NON_OP_EXPENSE_CODES:
            d, c, _ = sn.trace_pnl_dc(code, year_start, close_dt)
            profit_trace[code] = {"debit": float(d), "credit": float(c), "net": float(d - c)}

        cumulative_profit = compute_cumulative_profit(sn, year_start, close_dt)

        # ── 2. 已计提 ──
        posted_d, posted_c, move_ids = sn.trace_per_dc("222105", year_start, close_dt)
        posted = (posted_c - posted_d).quantize(Q2)
        posted_trace = {
            "科目": "222105 应交所得税",
            "贷方": float(posted_c), "借方": float(posted_d),
            "净额": float(posted), "凭证ID": [int(mid) for mid in move_ids],
        }

        # ── 3. 税率判定 ──
        income_type = profile.income_type

        if income_type == "personal":
            return IncomeTaxResult(
                profit_l2=cumulative_profit, tax_rate_l2=Decimal("0"),
                tax_payable_l2=Decimal("0"), posted_l2=posted,
                delta_l2=Decimal("0"),
                trace={"profit": profit_trace,
                       "rate": {"income_type": "personal", "rate": 0, "reason": "个体工商户缴个税"},
                       "posted": posted_trace},
            )

        if income_type == "general":
            facts = load_income_tax_facts(period_start.date())
            if cumulative_profit <= facts.small_micro_threshold:
                profile = refine_small_micro(profile, cumulative_profit, facts.small_micro_threshold)

        result = policy_income_tax(profile=profile, profit=cumulative_profit)

        return IncomeTaxResult(
            profit_l2=cumulative_profit, tax_rate_l2=result.tax_rate,
            tax_payable_l2=result.tax_payable, posted_l2=posted,
            delta_l2=(result.tax_payable - posted).quantize(Q2),
            trace={
                "profit": profit_trace,
                "rate": {"income_type": income_type, "final_type": profile.income_type,
                         "rate": float(result.tax_rate),
                         "reduction": result.reduction_item or "",
                         "profit_l2": float(cumulative_profit)},
                "posted": posted_trace,
            },
        )
