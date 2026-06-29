"""月结 Command — 封装税务计提逻辑，处理事务和幂等；结账后自动对账"""

from dataclasses import dataclass, field
from decimal import Decimal
from typing import Any, Optional

from .base import Command, CommandHandler, register
from crud.base import _log
from engine_tax import TaxAccrualEngine
from engine_tax_check import TaxCheckEngine
from errors import BusinessError, ErrorCode


@dataclass
class MonthEndClose(Command):
    period: str = ""                   # YYYY-MM
    taxpayer_type: str = ""            # 空则从 Account 读取


@register(MonthEndClose)
class MonthEndCloseHandler(CommandHandler):
    def handle(self, cmd: MonthEndClose, db: Any) -> Any:
        # ── 前置: 银行调节表必须全部 Confirmed ──
        import models, models_bank
        bank_accounts = db.query(models.BankAccount).filter(
            models.BankAccount.account_id == cmd.account_id,
        ).all()
        for ba in bank_accounts:
            rec = db.query(models_bank.BankReconciliation).filter(
                models_bank.BankReconciliation.bank_account_id == ba.id,
                models_bank.BankReconciliation.account_id == cmd.account_id,
                models_bank.BankReconciliation.period == cmd.period,
            ).first()
            if rec and rec.status != "confirmed":
                raise BusinessError(
                    code=ErrorCode.VALIDATION_ERROR,
                    message=f"银行对账未完成: {ba.bank_name}({ba.account_number}) "
                            f"调节表状态为 {rec.status}，请先完成银行对账并确认"
                )

        # ── 折旧计提（影响利润 → 影响所得税）──
        from engine_fixed_asset import FixedAssetEngine
        depreciations = FixedAssetEngine(db, cmd.account_id).batch_depreciate(cmd.period)

        engine = TaxAccrualEngine(db)
        result = engine.execute(cmd.account_id, cmd.period, cmd.taxpayer_type)

        result["depreciation_count"] = len(depreciations)

        _log(db, cmd.account_id, "close", "month_end", cmd.account_id,
             f"月结 {cmd.period}: {result.get('status')} — {'; '.join(result.get('lines', [])) or result.get('msg', '')}",
             operator=cmd.operator)
        db.flush()

        # 月结后自动税务核对
        check_engine = TaxCheckEngine(db, cmd.account_id)
        check_result = check_engine.execute(cmd.period)
        result["tax_check"] = {
            "all_passed": check_result["all_passed"],
            "checks": check_result["checks"],
            "warnings": check_result["warnings"],
        }

        return result
