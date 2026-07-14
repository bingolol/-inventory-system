"""税务声明 Command — 增值税/附加税申报声明的命令

VATDeclaration: 用户提交时锁定 VAT 快照（L1 外部输入）
SurchargeDeclaration: 用户录入实际附加税（L1 外部输入），录入即过账 + 级联修正
"""
import logging
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Any, Optional

from sqlalchemy.orm import Session

from .base import Command, CommandHandler, register
from crud.base import log_op
from models_finance import VATDeclaration, SurchargeDeclaration
from finance_integration import post_journal, get_or_create_ledger_id
from errors import BusinessError, ErrorCode
from utils import _d, Q2

logger = logging.getLogger("inventory")
from utils.period import period_hash


# ── VAT 声明 ──

@dataclass
class DeclareVAT(Command):
    period: str = ""
    taxpayer_type: str = "small_scale"


@register(DeclareVAT)
class DeclareVATHandler(CommandHandler):
    def handle(self, cmd: DeclareVAT, db: Any) -> Any:
        import models
        from models import TaxpayerTypeHistory
        from crud.finance import aggregate_vat_invoices
        from crud.finance.tax_declarations import compute_carry_forward
        from policy.entity_profile import build_profile
        from policy.policy_engine import calculate_vat as policy_vat
        from utils.period import parse_period

        account = db.query(models.Account).filter(
            models.Account.id == cmd.account_id
        ).first()
        if not account:
            raise BusinessError(code=ErrorCode.NOT_FOUND, message="账本不存在")

        # 解析期间
        taxpayer_type = cmd.taxpayer_type or account.taxpayer_type_l3
        if not taxpayer_type:
            raise BusinessError(code=ErrorCode.VALIDATION_ERROR,
                                message="纳税人类型未配置")
        if taxpayer_type == "small_scale":
            parts = cmd.period.split("-Q")
            if len(parts) != 2:
                raise BusinessError(code=ErrorCode.VALIDATION_ERROR, message="小规模期间格式必须为 YYYY-QQ，如 2026-Q2")
            year, q = int(parts[0]), int(parts[1])
            start_month = (q - 1) * 3 + 1
            end_month = q * 3
            period_start = datetime(year, start_month, 1)
            import calendar
            last_day = calendar.monthrange(year, end_month)[1]
            period_end = datetime(year, end_month, last_day, 23, 59, 59)
            period_ym = f"{year}-{end_month:02d}"
        else:
            parts = cmd.period.split("-")
            if len(parts) != 2:
                raise BusinessError(code=ErrorCode.VALIDATION_ERROR, message="一般纳税人期间格式必须为 YYYY-MM，如 2026-07")
            period_start = datetime(int(parts[0]), int(parts[1]), 1)
            import calendar
            last_day = calendar.monthrange(int(parts[0]), int(parts[1]))[1]
            period_end = datetime(int(parts[0]), int(parts[1]), last_day, 23, 59, 59)
            period_ym = cmd.period

        # 小规模季度申报：检查季度内是否有纳税人类型切换，自动截断
        if taxpayer_type == "small_scale":
            transition = db.query(TaxpayerTypeHistory).filter(
                TaxpayerTypeHistory.account_id == cmd.account_id,
                TaxpayerTypeHistory.taxpayer_type_l3 == "general",
                TaxpayerTypeHistory.effective_period > f"{year}-{start_month:02d}",
                TaxpayerTypeHistory.effective_period <= period_ym,
            ).order_by(TaxpayerTypeHistory.effective_period).first()
            if transition:
                yr, mo = int(transition.effective_period[:4]), int(transition.effective_period[5:7])
                prev_mo = 12 if mo == 1 else mo - 1
                prev_yr = yr - 1 if mo == 1 else yr
                last_day = calendar.monthrange(prev_yr, prev_mo)[1]
                period_end = datetime(prev_yr, prev_mo, last_day, 23, 59, 59)

        # 查是否已存在
        existing = db.query(VATDeclaration).filter(
            VATDeclaration.account_id == cmd.account_id,
            VATDeclaration.period == cmd.period,
        ).first()
        if existing:
            raise BusinessError(
                code=ErrorCode.DUPLICATE_ENTRY,
                message=f"期间 {cmd.period} 的 VAT 已申报（ID={existing.id}），如需覆盖请使用 force 参数"
            )

        # 锁定快照：读取当前 VAT 数据
        agg = aggregate_vat_invoices(db, cmd.account_id, period_start, period_end)
        profile = build_profile(account, ref_date=period_start.date())
        carry_forward_l1 = compute_carry_forward(db, account, period_start)
        vat_result = policy_vat(
            profile=profile,
            total_revenue_l1=agg["output_total"],
            input_tax_l1=agg["input_tax_l1"],
            output_tax_l1=agg["output_tax_l1"],
            ordinary_revenue=agg["ordinary_revenue"],
            special_revenue=agg["special_revenue"],
            carry_forward_l1=carry_forward_l1,
        )

        declaration = VATDeclaration(
            account_id=cmd.account_id,
            period=cmd.period,
            taxpayer_type=taxpayer_type,
            total_revenue_l1=vat_result.total_revenue_l1.quantize(Q2),
            output_tax_l1=vat_result.tax_payable_gross.quantize(Q2),
            input_tax_l1=agg["input_tax_l1"].quantize(Q2),
            vat_payable_l1=vat_result.tax_payable.quantize(Q2),
            carry_forward_l1=carry_forward_l1.quantize(Q2),
            period_start=period_start.date(),
            period_end=period_end.date(),
            snapshot_at=datetime.now(),
        )
        db.add(declaration)
        db.flush()

        # 一般纳税人：自动执行 vat_transfer_out（幂等）
        if taxpayer_type != "small_scale" and vat_result.tax_payable > Q2:
            from models_finance import AccountMove as _AM
            ledger_id = get_or_create_ledger_id(db, cmd.account_id)
            existing_move = db.query(_AM).filter(
                _AM.ledger_id == ledger_id,
                _AM.source_model == "vat_transfer_out",
                _AM.source_id == period_hash(cmd.period, "vat_xfer"),
                _AM.is_reversal == False,
            ).first()

            if not existing_move:
                post_journal(db, cmd.account_id, "vat_transfer_out", {
                    "amount": vat_result.tax_payable,
                    "date": period_end,
                    "source_model": "vat_transfer_out",
                    "source_id": period_hash(cmd.period, "vat_xfer"),
                })

        log_op(db, cmd.account_id, "create", "vat_declaration", declaration.id,
             f"VAT 申报声明: 期间={cmd.period}, 应缴={vat_result.tax_payable}", operator=cmd.operator)
        db.flush()

        # 未认证进项发票提示：列出可抵扣但未认证的专票
        uncertified = []
        for inv in agg["in_invoices"]:
            if inv.invoice_type == "special" and inv.certification_status_l3 != "certified":
                uncertified.append({
                    "invoice_no": inv.invoice_no,
                    "issue_date": inv.issue_date_l1.strftime("%Y-%m-%d") if inv.issue_date_l1 else None,
                    "amount_without_tax": float(_d(inv.amount_without_tax_l1)),
                    "tax_amount": float(_d(inv.tax_amount_l1)),
                    "certification_status": inv.certification_status_l3,
                    "hint": "该专票尚未认证，认证后可在下期抵扣进项税额",
                })

        return {
            "id": declaration.id,
            "period": cmd.period,
            "vat_payable_l1": float(vat_result.tax_payable.quantize(Q2)),
            "total_revenue_l1": float(vat_result.total_revenue_l1.quantize(Q2)),
            "output_tax_l1": float(vat_result.tax_payable_gross.quantize(Q2)),
            "input_tax_l1": float(agg["input_tax_l1"].quantize(Q2)),
            "carry_forward_l1": float(carry_forward_l1.quantize(Q2)),
            "snapshot_at": declaration.snapshot_at.isoformat(),
            "uncertified_invoices": uncertified,
        }


# ── 附加税声明 ──

@dataclass
class DeclareSurcharge(Command):
    period: str = ""
    urban_construction_tax_l1: Decimal = Decimal("0")
    education_surcharge_l1: Decimal = Decimal("0")
    local_education_surcharge_l1: Decimal = Decimal("0")
    notes: str = ""


@register(DeclareSurcharge)
class DeclareSurchargeHandler(CommandHandler):
    def handle(self, cmd: DeclareSurcharge, db: Any) -> Any:
        import models
        from models_finance import AccountMove
        from utils.period import parse_period

        # 验证 VATDeclaration 存在
        vat_decl = db.query(VATDeclaration).filter(
            VATDeclaration.account_id == cmd.account_id,
            VATDeclaration.period == cmd.period,
        ).first()
        if not vat_decl:
            raise BusinessError(
                code=ErrorCode.VALIDATION_ERROR,
                message=f"期间 {cmd.period} 的 VAT 尚未申报，请先提交 VAT 申报"
            )

        # 查是否已存在（幂等）
        existing = db.query(SurchargeDeclaration).filter(
            SurchargeDeclaration.account_id == cmd.account_id,
            SurchargeDeclaration.period == cmd.period,
        ).first()

        total = cmd.urban_construction_tax_l1 + cmd.education_surcharge_l1 + cmd.local_education_surcharge_l1

        if existing:
            # 已有 → 冲红旧凭证 + 重建（BR-REV: 替代旧 delta 模式，避免凭证累计叠加）
            old_total = existing.total_l1
            delta = total - old_total
            if abs(delta) <= Q2:
                return {
                    "id": existing.id,
                    "period": cmd.period,
                    "total": float(total),
                    "posted": "no_change",
                }
            # 冲红原 tax_surcharge 凭证
            from finance_integration import reverse_journal
            reverse_journal(db, cmd.account_id, "tax_surcharge",
                            period_hash(cmd.period, "surcharge"), force=True)
            # 更新声明值
            existing.urban_construction_tax_l1 = cmd.urban_construction_tax_l1
            existing.education_surcharge_l1 = cmd.education_surcharge_l1
            existing.local_education_surcharge_l1 = cmd.local_education_surcharge_l1
            existing.total_l1 = total
            existing.notes = cmd.notes or existing.notes
            db.flush()
            # 重新过账（force=True 跳过幂等防御）
            _post_surcharge_journal(db, cmd.account_id, cmd.period, vat_decl.period_end,
                                     cmd.urban_construction_tax_l1, cmd.education_surcharge_l1, cmd.local_education_surcharge_l1)
            _cascade_fix(db, cmd.account_id, cmd.period)
            log_op(db, cmd.account_id, "update", "surcharge_declaration", existing.id,
                 f"附加税更新(冲红+重建): 期间={cmd.period}, 金额={total}", operator=cmd.operator)
            db.flush()
            return {
                "id": existing.id,
                "period": cmd.period,
                "total": float(total),
                "posted": "reverse_and_rebuild",
            }

        # 新建
        declaration = SurchargeDeclaration(
            account_id=cmd.account_id,
            period=cmd.period,
            vat_declaration_id=vat_decl.id,
            vat_payable_l1=vat_decl.vat_payable_l1,
            urban_construction_tax_l1=cmd.urban_construction_tax_l1,
            education_surcharge_l1=cmd.education_surcharge_l1,
            local_education_surcharge_l1=cmd.local_education_surcharge_l1,
            total_l1=total,
            notes=cmd.notes,
            status="posted",
        )
        db.add(declaration)
        db.flush()

        # 过账附加税分录
        _post_surcharge_journal(db, cmd.account_id, cmd.period, vat_decl.period_end,
                                 cmd.urban_construction_tax_l1, cmd.education_surcharge_l1, cmd.local_education_surcharge_l1)

        # 级联修正
        fix_result = _cascade_fix(db, cmd.account_id, cmd.period)

        log_op(db, cmd.account_id, "create", "surcharge_declaration", declaration.id,
             f"附加税声明: 期间={cmd.period}, 合计={total}, 级联修正={fix_result}", operator=cmd.operator)
        db.flush()

        return {
            "id": declaration.id,
            "period": cmd.period,
            "vat_payable_l1": float(vat_decl.vat_payable_l1),
            "urban_construction_tax_l1": float(cmd.urban_construction_tax_l1),
            "education_surcharge_l1": float(cmd.education_surcharge_l1),
            "local_education_surcharge_l1": float(cmd.local_education_surcharge_l1),
            "total": float(total),
            "posted": "new",
            "cascade": fix_result,
        }


def _post_surcharge_journal(db: Session, account_id: int, period: str,
                             period_end: datetime,
                             urban: Decimal, education: Decimal, local_education: Decimal):
    """过账附加税分录（dr 6403xx cr 2221xx）"""
    taxes = {}
    if urban > Q2:
        taxes["640302"] = urban
    if education > Q2:
        taxes["640303"] = education
    if local_education > Q2:
        taxes["640304"] = local_education
    if not taxes:
        return

    post_journal(db, account_id, "tax_surcharge", {
        "taxes": taxes,
        "date": period_end,
        "source_model": "tax_surcharge",
        "source_id": period_hash(period, "surcharge"),
    }, force=True)


def _cascade_fix(db: Session, account_id: int, period: str) -> dict:
    """级联修正：检测 period_close + income_tax 并重跑/调整

    对于季度 period（如 "2025-Q4"），转换为季度末月度 period（如 "2025-12"），
    因为 PeriodCloseEngine 和所得税 source_id 都使用月度 period 格式。
    附加税凭证日期 = 季度末月末日，所以只需重跑季度末月的 period_close。
    """
    from datetime import datetime
    from calendar import monthrange
    from models_finance import AccountMove

    # 季度 period → 月度 period（取季度末月）
    if "Q" in period:
        year = int(period[:4])
        q = int(period.split("-Q")[1])
        end_month = q * 3
        monthly_period = f"{year}-{end_month:02d}"
    else:
        monthly_period = period

    from utils.period import parse_period
    period_start, close_dt = parse_period(monthly_period)
    result = {"period_close_rerun": False, "income_tax_adjusted": 0}

    # ── 第 1 步：先调整所得税（必须在 period_close 重跑之前）──
    ledger_id = get_or_create_ledger_id(db, account_id)
    income_exists = db.query(AccountMove).filter(
        AccountMove.ledger_id == ledger_id,
        AccountMove.source_model.in_(["tax_income", "tax_income_reversal"]),
        AccountMove.date_l1 >= period_start.date(),
        AccountMove.date_l1 <= close_dt.date(),
    ).first()

    if income_exists:
        try:
            from engine_income_tax import IncomeTaxEngine
            r = IncomeTaxEngine(db).calculate(account_id, monthly_period)
            if abs(r.delta_l2) > Q2:
                if r.delta_l2 > Q2:
                    post_journal(db, account_id, "tax_income", {
                        "amount": r.delta_l2, "date": close_dt,
                        "source_model": "tax_income",
                        "source_id": period_hash(monthly_period, "income"),
                    }, force=True)
                else:
                    post_journal(db, account_id, "tax_income_reversal", {
                        "amount": abs(r.delta_l2), "date": close_dt,
                        "source_model": "tax_income_reversal",
                        "source_id": period_hash(monthly_period, "income_rev"),
                    }, force=True)
                result["income_tax_adjusted"] = float(r.delta_l2)
        except BusinessError:
            raise
        except Exception:
            logger.exception("_cascade_fix income_tax adjustment failed for period=%s", period)
            raise

    # ── 第 2 步：重跑 period_close（将调整后的 6701 余额结转到 4103）──
    close_exists = db.query(AccountMove).filter(
        AccountMove.ledger_id == ledger_id,
        AccountMove.source_model == "period_close",
        AccountMove.date_l1 >= period_start.date(),
        AccountMove.date_l1 <= close_dt.date(),
    ).first()

    if close_exists:
        try:
            from finance_orchestrator import FinanceOrchestrator
            FinanceOrchestrator(db, account_id).close_period(monthly_period, force=True)
            result["period_close_rerun"] = True
        except Exception:
            logger.exception("_cascade_fix period_close rerun failed for period=%s", period)

    return result