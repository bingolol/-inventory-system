"""税务核对引擎 — 6 项账表核对，月结后自动联动

核对基准（project_memory「发票是真相源」原则）：
  - 核对项 1/2/3（销售额/销项税/进项税）：从发票表取数，发票是 L1 外部输入真相源
  - 核对项 4/6a（未交增值税/附加税计税依据）：总账余额，资产负债表科目月结不结转
  - 核对项 5/6b（所得税/附加税金额）：总账 pnl_dc，排除 period_close/year_close 结转分录
  - 损益核对：利润表 gross_profit_total

期间粒度：按纳税人类型自动切换
  - 小规模纳税人：按季度（增值税按季申报），period=YYYY-MM → 取当季发票
  - 一般纳税人：按月，period=YYYY-MM → 取当月发票
"""

import logging
from decimal import Decimal
from datetime import datetime
from typing import Dict, List, Optional

from sqlalchemy.orm import Session

from models_finance import Ledger
from crud.finance._snapshot import LedgerSnapshot
from crud.finance.tax_declarations import aggregate_vat_invoices
from utils import _d, Q2
from utils.period import parse_period, quarter_bounds
from enums import TaxpayerType

logger = logging.getLogger("inventory")


class TaxCheckEngine:

    def __init__(self, db: Session, account_id: int):
        self.db = db
        self.account_id = account_id
        import models
        self.account = db.query(models.Account).filter(models.Account.id == account_id).first()
        self.ledger = self.account and db.query(Ledger).filter(Ledger.code == self.account.code).first()
        self.warnings: List[str] = []

    def _resolve_invoice_period(self, period: str):
        """按纳税人类型解析发票查询期间（左闭右开）。

        小规模纳税人增值税按季申报，period=YYYY-MM 取当季 [季度初, 季度初+3月)。
        一般纳税人按月申报，取当月 [月初, 月末+1天)。
        """
        year, month = int(period[:4]), int(period[5:7])
        if self.account and self.account.taxpayer_type_l3 == TaxpayerType.GENERAL:
            # 一般纳税人：按月
            from calendar import monthrange
            start = datetime(year, month, 1)
            if month == 12:
                end_exclusive = datetime(year + 1, 1, 1)
            else:
                end_exclusive = datetime(year, month + 1, 1)
            return start, end_exclusive
        else:
            # 小规模纳税人：按季
            quarter = (month - 1) // 3 + 1
            return quarter_bounds(year, quarter)

    def execute(self, period: str, declared: Optional[Dict] = None) -> Dict:
        declared = declared or {}
        start_dt, end_dt = parse_period(period)
        checks = []

        sn = LedgerSnapshot(self.db, self.account_id, bs_cutoff=end_dt, period_start=start_dt, period_end=end_dt)

        # ── 发票汇总（核对项 1/2/3 的数据源）──
        # 发票是 L1 外部输入真相源，红字发票金额为负，汇总时自动抵消（等效于扣减退货冲红）
        inv_start, inv_end_exclusive = self._resolve_invoice_period(period)
        agg = aggregate_vat_invoices(self.db, self.account_id, inv_start, inv_end_exclusive)

        # ── 1. 销售额: 申报 vs 销项发票不含税金额合计 ──
        # 发票真相源：红字发票金额为负，汇总时自动抵消（等效于扣减退货冲红）
        checks.append(self._ck("销售额", declared.get("sales"),
                               agg["output_total"].quantize(Q2)))

        # ── 2. 销项税额: 申报 vs 销项发票税额合计 ──
        checks.append(self._ck("销项税额", declared.get("output_vat"),
                               agg["output_tax_l1"].quantize(Q2)))

        # ── 3. 进项税额: 申报 vs 进项发票税额合计（仅一般纳税人已认证专票）──
        checks.append(self._ck("进项税额", declared.get("input_vat"),
                               agg["input_tax_l1"].quantize(Q2)))

        # ── 4. 未交增值税: 申报"应补税额" vs 222107 贷方余额 ──
        # 资产负债表科目，月结不结转，总账余额是正确数据源
        b4 = sn.crd("222107")
        checks.append(self._ck("未交增值税", declared.get("unpaid_vat"),
                               b4.quantize(Q2)))

        # ── 5. 所得税: 申报 vs 6801 借方发生额（排除月结结转）──
        # pnl_dc 排除 period_close/year_close，避免结转分录抵消实际计提额
        b5, b5c = sn.pnl_dc("6801", start_dt, end_dt)
        checks.append(self._ck("所得税费用", declared.get("income_tax"),
                               (b5 - b5c).quantize(Q2)))

        # ── 6. 附加税: 申报计税依据 vs 222106借方, 申报附加税 vs 6403借方 ──
        # 222106 是资产负债表科目（转出未交增值税），月结不结转，用 per_dc
        b6a, _ = sn.per_dc("222106", start_dt, end_dt)
        # 6403 是损益类科目，月结会结转，用 pnl_dc 排除结转分录
        b6b, b6c = sn.pnl_dc("6403", start_dt, end_dt)
        checks.append(self._ck("附加税-计税依据(转出未交增值税)",
                               declared.get("vat_payable_l1"),
                               b6a.quantize(Q2)))
        checks.append(self._ck("附加税-金额(税金及附加)",
                               declared.get("surcharge"),
                               (b6b - b6c).quantize(Q2)))

        # ── 损益核对: 申报"利润总额" vs 利润表 ──
        from crud.finance import generate_income_statement
        ist = generate_income_statement(self.db, self.account_id,
                                        start_dt.strftime("%Y-%m-%d"),
                                        end_dt.strftime("%Y-%m-%d"))
        checks.append(self._ck("利润总额", declared.get("gross_profit"),
                               ist["gross_profit_total"]))

        return {
            "period": period,
            "period_start": start_dt.strftime("%Y-%m-%d"),
            "period_end": end_dt.strftime("%Y-%m-%d"),
            "checks": checks,
            "all_passed": all(c["passed"] for c in checks),
            "warnings": self.warnings,
        }

    def _ck(self, name: str, declared, book: Decimal) -> dict:
        if declared is None:
            self.warnings.append(f"缺失申报数据: {name}")
            return {
                "name": name, "declared": None,
                "book": float(book.quantize(Q2)), "diff": None,
                "passed": False, "status": "no_data",
            }
        diff = round(float(Decimal(str(declared))) - float(book), 2)
        passed = abs(diff) <= 0.01
        if not passed:
            self.warnings.append(f"{name}: 申报{declared} vs 账面{float(book)} 差异{diff}")
        return {
            "name": name,
            "declared": float(Decimal(str(declared))),
            "book": float(book.quantize(Q2)),
            "diff": diff,
            "passed": passed,
            "status": "ok" if passed else "mismatch",
        }
