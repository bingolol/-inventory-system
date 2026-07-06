"""税务声明 Command — 增值税/附加税申报声明的命令

VATDeclaration: 用户提交时锁定 VAT 快照（L1 外部输入）
SurchargeDeclaration: 用户录入实际附加税（L1 外部输入），录入即过账 + 级联修正
"""

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Any, Optional

from sqlalchemy.orm import Session

from .base import Command, CommandHandler, register
from crud.base import log_op
from models_finance import VATDeclaration, SurchargeDeclaration
from finance_integration import post_journal
from errors import BusinessError, ErrorCode
from utils import _d, Q2
from utils.period import period_hash


def _get_quarter_end(month: int) -> int:
    """返回季度末月份"""
    return ((month - 1) // 3 + 1) * 3


# ── VAT 声明 ──

@dataclass
class DeclareVAT(Command):
    period: str = ""
    taxpayer_type: str = "small_scale"


@register(DeclareVAT)
class DeclareVATHandler(CommandHandler):
    def handle(self, cmd: DeclareVAT, db: Any) -> Any:
        import models
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
        taxpayer_type = cmd.taxpayer_type or account.taxpayer_type_l3 or "small_scale"
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
        profile = build_profile(account)
        carry_forward = compute_carry_forward(db, account, period_start)
        vat_result = policy_vat(
            profile=profile,
            total_revenue=agg["output_total"],
            input_tax=agg["input_tax"],
            output_tax=agg["output_tax"],
            ordinary_revenue=agg["ordinary_revenue"],
            special_revenue=agg["special_revenue"],
            carry_forward=carry_forward,
        )

        declaration = VATDeclaration(
            account_id=cmd.account_id,
            period=cmd.period,
            taxpayer_type=taxpayer_type,
            total_revenue=vat_result.total_revenue.quantize(Q2),
            output_tax=vat_result.tax_payable_gross.quantize(Q2),
            input_tax=agg["input_tax"].quantize(Q2),
            vat_payable=vat_result.tax_payable.quantize(Q2),
            carry_forward=carry_forward.quantize(Q2),
            period_start=period_start.date(),
            period_end=period_end.date(),
            snapshot_at=datetime.now(),
        )
        db.add(declaration)
        db.flush()

        # 一般纳税人：自动执行 vat_transfer_out（幂等）
        if taxpayer_type != "small_scale" and vat_result.tax_payable > Q2:
            sn_list = list(agg.get("out_invoices", []) or [])
            move_exists = False
            try:
                existing_move = db.query(type(db.registry._class_registry.get("AccountMove", None))).filter(
                    type(db.registry._class_registry.get("AccountMove", None)).source_model == "vat_transfer_out",
                    type(db.registry._class_registry.get("AccountMove", None)).source_id == period_hash(cmd.period, "vat_xfer"),
                ).first() if "AccountMove" in db.registry._class_registry else None
                move_exists = existing_move is not None
            except Exception:
                pass

            if not move_exists:
                try:
                    post_journal(db, cmd.account_id, "vat_transfer_out", {
                        "amount": vat_result.tax_payable,
                        "date": period_end,
                        "source_model": "vat_transfer_out",
                        "source_id": period_hash(cmd.period, "vat_xfer"),
                    })
                except Exception as e:
                    pass

        log_op(db, cmd.account_id, "create", "vat_declaration", declaration.id,
             f"VAT 申报声明: 期间={cmd.period}, 应缴={vat_result.tax_payable}", operator=cmd.operator)
        db.flush()

        return {
            "id": declaration.id,
            "period": cmd.period,
            "vat_payable": float(vat_result.tax_payable.quantize(Q2)),
            "total_revenue": float(vat_result.total_revenue.quantize(Q2)),
            "output_tax": float(vat_result.tax_payable_gross.quantize(Q2)),
            "input_tax": float(agg["input_tax"].quantize(Q2)),
            "carry_forward": float(carry_forward.quantize(Q2)),
            "snapshot_at": declaration.snapshot_at.isoformat(),
        }


# ── 附加税声明 ──

@dataclass
class DeclareSurcharge(Command):
    period: str = ""
    urban_construction_tax: Decimal = Decimal("0")
    education_surcharge: Decimal = Decimal("0")
    local_education_surcharge: Decimal = Decimal("0")
    notes: str = ""


@register(DeclareSurcharge)
class DeclareSurchargeHandler(CommandHandler):
    def handle(self, cmd: DeclareSurcharge, db: Any) -> Any:
        import models
        from models_finance import AccountMove
        from engine_period_close import PeriodCloseEngine
        from crud.finance._snapshot import LedgerSnapshot
        from crud.finance._profit import compute_cumulative_profit
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

        total = cmd.urban_construction_tax + cmd.education_surcharge + cmd.local_education_surcharge

        if existing:
            # 已有 → 计算 delta 过账差额
            old_total = existing.total
            delta = total - old_total
            if abs(delta) <= Q2:
                return {
                    "id": existing.id,
                    "period": cmd.period,
                    "total": float(total),
                    "posted": "no_change",
                }
            # 更新声明值
            existing.urban_construction_tax = cmd.urban_construction_tax
            existing.education_surcharge = cmd.education_surcharge
            existing.local_education_surcharge = cmd.local_education_surcharge
            existing.total = total
            existing.notes = cmd.notes or existing.notes
            db.flush()
            _post_surcharge_journal(db, cmd.account_id, cmd.period, vat_decl.period_end,
                                     cmd.urban_construction_tax, cmd.education_surcharge, cmd.local_education_surcharge)
            _cascade_fix(db, cmd.account_id, cmd.period)
            log_op(db, cmd.account_id, "update", "surcharge_declaration", existing.id,
                 f"附加税更新: 期间={cmd.period}, 金额={total}", operator=cmd.operator)
            db.flush()
            return {
                "id": existing.id,
                "period": cmd.period,
                "total": float(total),
                "posted": "delta",
            }

        # 新建
        declaration = SurchargeDeclaration(
            account_id=cmd.account_id,
            period=cmd.period,
            vat_declaration_id=vat_decl.id,
            vat_payable=vat_decl.vat_payable,
            urban_construction_tax=cmd.urban_construction_tax,
            education_surcharge=cmd.education_surcharge,
            local_education_surcharge=cmd.local_education_surcharge,
            total=total,
            notes=cmd.notes,
            status="posted",
        )
        db.add(declaration)
        db.flush()

        # 过账附加税分录
        _post_surcharge_journal(db, cmd.account_id, cmd.period, vat_decl.period_end,
                                 cmd.urban_construction_tax, cmd.education_surcharge, cmd.local_education_surcharge)

        # 级联修正
        fix_result = _cascade_fix(db, cmd.account_id, cmd.period)

        log_op(db, cmd.account_id, "create", "surcharge_declaration", declaration.id,
             f"附加税声明: 期间={cmd.period}, 合计={total}, 级联修正={fix_result}", operator=cmd.operator)
        db.flush()

        return {
            "id": declaration.id,
            "period": cmd.period,
            "vat_payable": float(vat_decl.vat_payable),
            "urban_construction_tax": float(cmd.urban_construction_tax),
            "education_surcharge": float(cmd.education_surcharge),
            "local_education_surcharge": float(cmd.local_education_surcharge),
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
    print(f"  [CASCADE] _cascade_fix called: period={period}")
    from datetime import datetime
    from calendar import monthrange
    from models_finance import AccountMove
    from crud.finance._snapshot import LedgerSnapshot
    from crud.finance._profit import compute_cumulative_profit
    from engine_period_close import PeriodCloseEngine

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
    print(f"  [CASCADE] monthly_period={monthly_period} start={period_start} close={close_dt}")
    result = {"period_close_rerun": False, "income_tax_adjusted": 0}

    # 检查 period_close 是否已执行（用月度 period 查询和重跑）
    close_exists = db.query(AccountMove).filter(
        AccountMove.source_model == "period_close",
        AccountMove.date_l1 >= period_start.date(),
        AccountMove.date_l1 <= close_dt.date(),
    ).first()

    if close_exists:
        try:
            engine = PeriodCloseEngine(db)
            engine.execute(account_id, monthly_period, force=True)
            result["period_close_rerun"] = True
        except Exception as e:
            print(f"  [CASCADE ERROR] period_close rerun failed: {e}")

    # 检查 income_tax 是否已执行
    income_exists = db.query(AccountMove).filter(
        AccountMove.source_model.in_(["tax_income", "tax_income_reversal"]),
        AccountMove.date_l1 >= period_start.date(),
        AccountMove.date_l1 <= close_dt.date(),
    ).first()

    if income_exists:
        try:
            from policy.entity_profile import build_profile, resolve_taxpayer_type_by_date, refine_small_micro
            from policy.policy_engine import calculate_income_tax as policy_income_tax
            from policy.income_tax_facts import load_income_tax_facts
            import models
            account = db.query(models.Account).filter(models.Account.id == account_id).first()

            sn = LedgerSnapshot(db, account_id, bs_cutoff=close_dt,
                                period_start=period_start, period_end=close_dt)
            year_start = datetime(period_start.year, 1, 1, 0, 0, 0)
            cumulative_profit = compute_cumulative_profit(sn, year_start, close_dt)

            # 与 engine_tax.py 保持一致：解析历史纳税人类型 + 小微企业判定
            vat_type_ov = resolve_taxpayer_type_by_date(account, db, period_start.date()) if account else None
            profile = build_profile(account, period_start.date(), vat_type_override=vat_type_ov,
                                    surcharge_halved=account.surcharge_halved if account else None) if account else None
            if profile and profile.income_type == "general":
                income_facts_data = load_income_tax_facts(period_start.date())
                profile = refine_small_micro(profile, cumulative_profit, income_facts_data.small_micro_threshold)

            import logging
            logging.getLogger("inventory").info(
                f"_cascade_fix {period}: monthly={monthly_period}, "
                f"profit={cumulative_profit}, profile.income_type={profile.income_type if profile else None}, "
                f"vat_type_ov={vat_type_ov}"
            )
            print(f"  [DEBUG _cascade_fix] period={period} monthly={monthly_period} "
                  f"profit={cumulative_profit} income_type={profile.income_type if profile else None} "
                  f"vat_ov={vat_type_ov} target_tax={target_tax if 'target_tax' in dir() else '?'}")

            if profile and profile.income_type != "personal":
                income_result = policy_income_tax(
                    profile=profile, profit=cumulative_profit,
                )
                target_tax = income_result.tax_payable
                ytd_debit, ytd_credit, _ = sn.trace_per_dc("222105", year_start, close_dt)
                posted_tax = (ytd_credit - ytd_debit).quantize(Q2)
                delta = target_tax - posted_tax

                if abs(delta) > Q2:
                    if delta > Q2:
                        post_journal(db, account_id, "tax_income", {
                            "amount": delta, "date": close_dt,
                            "source_model": "tax_income",
                            "source_id": period_hash(monthly_period, "income"),
                        }, force=True)
                    else:
                        post_journal(db, account_id, "tax_income_reversal", {
                            "amount": abs(delta), "date": close_dt,
                            "source_model": "tax_income_reversal",
                            "source_id": period_hash(monthly_period, "income_rev"),
                        }, force=True)
                    result["income_tax_adjusted"] = float(delta)
        except Exception as e:
            print(f"  [CASCADE ERROR] income_tax adjustment failed: {e}")
            import traceback
            traceback.print_exc()

    return result