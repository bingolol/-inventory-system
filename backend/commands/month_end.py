"""月结 Command — 封装税务计提逻辑，处理事务和幂等；结账后自动对账"""

from dataclasses import dataclass, field
from decimal import Decimal
from typing import Any, Optional

from .base import Command, CommandHandler, register
from crud.base import log_op
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

        # ── 折旧/摊销计提（影响利润 → 影响所得税）──
        from engine_fixed_asset import FixedAssetEngine
        from engine_intangible_asset import IntangibleAssetEngine
        depreciations = FixedAssetEngine(db, cmd.account_id).batch_depreciate(cmd.period)
        amortizations = IntangibleAssetEngine(db, cmd.account_id).batch_amortize(cmd.period)

        engine = TaxAccrualEngine(db)
        result = engine.execute(cmd.account_id, cmd.period, cmd.taxpayer_type)

        result["depreciation_count"] = len(depreciations)
        result["amortization_count"] = len(amortizations)

        # ── 损益结转（月结最后一步，在税务计提之后）──
        # 将收入/费用科目余额结转到 4103（本年利润），12月额外年结 4103→4104
        from engine_period_close import PeriodCloseEngine
        close_engine = PeriodCloseEngine(db)
        close_result = close_engine.execute(cmd.account_id, cmd.period, force=False)
        result["period_close"] = close_result

        # ── 月结后自动税务核对（必须在日志 flush 前执行）──
        check_engine = TaxCheckEngine(db, cmd.account_id)
        check_result = check_engine.execute(cmd.period)
        result["tax_check"] = {
            "all_passed": check_result["all_passed"],
            "checks": check_result["checks"],
            "warnings": check_result["warnings"],
        }

        log_op(db, cmd.account_id, "close", "month_end", cmd.account_id,
             f"月结 {cmd.period}: {result.get('status')} — {'; '.join(result.get('lines', [])) or result.get('msg', '')}",
             operator=cmd.operator)
        db.flush()

        return result
