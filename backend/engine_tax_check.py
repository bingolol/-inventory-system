"""税务核对引擎 — 6 项账表核对，月结后自动联动"""

import logging
from decimal import Decimal
from typing import Dict, List, Optional

from sqlalchemy.orm import Session

from models_finance import Ledger
from crud.finance._snapshot import LedgerSnapshot
from utils import _d, Q2
from utils.period import parse_period

logger = logging.getLogger("inventory")


class TaxCheckEngine:

    def __init__(self, db: Session, account_id: int):
        self.db = db
        self.account_id = account_id
        import models
        account = db.query(models.Account).filter(models.Account.id == account_id).first()
        self.ledger = account and db.query(Ledger).filter(Ledger.code == account.code).first()
        self.warnings: List[str] = []

    def execute(self, period: str, declared: Optional[Dict] = None) -> Dict:
        declared = declared or {}
        start_dt, end_dt = parse_period(period)
        checks = []

        sn = LedgerSnapshot(self.db, self.account_id, bs_cutoff=end_dt, period_start=start_dt, period_end=end_dt)

        # ── 1. 销售额: 申报 vs 6001+6051 贷方净额(扣减退货冲红) ──
        s1d, s1c = sn.per_dc("6001", start_dt, end_dt)
        _, s1b = sn.per_dc("6051", start_dt, end_dt)
        checks.append(self._ck("销售额", declared.get("sales"),
                               (s1c - s1d + s1b).quantize(Q2)))

        # ── 2. 销项税额: 申报 vs 222101 贷方净额(扣减退货冲红/红字发票) ──
        b2d, b2c = sn.per_dc("222101", start_dt, end_dt)
        checks.append(self._ck("销项税额", declared.get("output_vat"),
                               (b2c - b2d).quantize(Q2)))

        # ── 3. 进项税额: 申报 vs 222102 借方净额(扣减退货冲红/进项转出) ──
        b3d, b3c = sn.per_dc("222102", start_dt, end_dt)
        checks.append(self._ck("进项税额", declared.get("input_vat"),
                               (b3d - b3c).quantize(Q2)))

        # ── 4. 未交增值税: 申报"应补税额" vs 222107 贷方余额 ──
        b4 = sn.crd("222107")
        checks.append(self._ck("未交增值税", declared.get("unpaid_vat"),
                               b4.quantize(Q2)))

        # ── 5. 所得税: 申报 vs 6801 借方发生额 ──
        b5, b5c = sn.per_dc("6801", start_dt, end_dt)
        checks.append(self._ck("所得税费用", declared.get("income_tax"),
                               (b5 - b5c).quantize(Q2)))

        # ── 6. 附加税: 申报计税依据 vs 222106借方, 申报附加税 vs 6403借方 ──
        b6a, _ = sn.per_dc("222106", start_dt, end_dt)
        b6b, b6c = sn.per_dc("6403", start_dt, end_dt)
        checks.append(self._ck("附加税-计税依据(转出未交增值税)",
                               declared.get("vat_payable"),
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
