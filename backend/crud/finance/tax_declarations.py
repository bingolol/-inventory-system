"""税务申报：增值税/企业所得税/资产折旧明细"""

from datetime import datetime, timedelta
from decimal import Decimal
from sqlalchemy.orm import Session
from sqlalchemy import func as sqlfunc

import models
from enums import (InvoiceDirection, InvoiceType,
                   CertificationStatus, TaxpayerType)
from utils import _d, Q2
from utils.period import quarter_bounds
from errors import BusinessError, ErrorCode
from accounting_engine import AccountingEngine
from policy.entity_profile import build_profile
from policy.policy_engine import calculate_vat as policy_vat, calculate_income_tax as policy_income_tax
from models_finance import Ledger, LedgerAccount, AccountMove, AccountMoveLine
from lineage import reads, TIER_L1, TIER_L2, TIER_L3, TIER_L4

_engine = AccountingEngine()


def _quarter_range(year: int, quarter: int):
    return quarter_bounds(year, quarter)


def compute_carry_forward(db, account, start_date):
    """计算一般纳税人上期期末留抵税额。小规模纳税人返回 0。"""
    if not account or account.taxpayer_type_l3 != "general":
        return Decimal("0")
    prev_end = start_date - timedelta(seconds=1)
    ledger = db.query(Ledger).filter(Ledger.code == account.code).first()
    if not ledger:
        return Decimal("0")
    def _deb(code, cutoff):
        r = db.query(sqlfunc.coalesce(sqlfunc.sum(AccountMoveLine.debit_l2), 0)).join(
            LedgerAccount, AccountMoveLine.ledger_account_id == LedgerAccount.id
        ).join(AccountMove, AccountMoveLine.move_id == AccountMove.id).filter(
            LedgerAccount.ledger_id == ledger.id, LedgerAccount.code == code,
            AccountMove.date_l1 <= cutoff).scalar()
        return _d(r)
    def _crd(code, cutoff):
        r = db.query(sqlfunc.coalesce(sqlfunc.sum(AccountMoveLine.credit_l2), 0)).join(
            LedgerAccount, AccountMoveLine.ledger_account_id == LedgerAccount.id
        ).join(AccountMove, AccountMoveLine.move_id == AccountMove.id).filter(
            LedgerAccount.ledger_id == ledger.id, LedgerAccount.code == code,
            AccountMove.date_l1 <= cutoff).scalar()
        return _d(r)
    prev_input = _deb("222102", prev_end) - _crd("222102", prev_end)
    prev_output = _crd("222101", prev_end) - _deb("222101", prev_end)
    return max(prev_input - prev_output, Decimal("0")).quantize(Q2)


def compute_vat_prepaid(db, account_id, year, quarter):
    """汇总同年此前季度已预缴增值税（vat_transfer_out 累计）。"""
    _, prev_q_end_exclusive = _quarter_range(year, quarter)
    prev_q_end = prev_q_end_exclusive - timedelta(days=1)
    year_start = datetime(year, 1, 1)
    import models
    account = db.query(models.Account).filter(models.Account.id == account_id).first()
    if not account:
        return Decimal("0")
    ledger = db.query(Ledger).filter(Ledger.code == account.code).first()
    if not ledger:
        return Decimal("0")
    total = _d(db.query(sqlfunc.coalesce(sqlfunc.sum(AccountMoveLine.credit_l2), 0)).join(
        AccountMove, AccountMoveLine.move_id == AccountMove.id
    ).filter(
        AccountMove.ledger_id == ledger.id,
        AccountMove.source_model == "vat_transfer_out",
        AccountMove.date_l1 >= year_start,
        AccountMove.date_l1 <= prev_q_end,
    ).scalar())
    return total.quantize(Q2)


@reads("Account.taxpayer_type_l3", tier=TIER_L3, source="policy")
@reads("Invoice.certification_status_l3", tier=TIER_L3, source="policy")
@reads("Invoice.amount_without_tax_l1", tier=TIER_L1, source="external")
@reads("Invoice.tax_amount_l1", tier=TIER_L1, source="external")
def aggregate_vat_invoices(db: Session, account_id: int, start_date: datetime, end_date_exclusive: datetime):
    """汇总一个增值税属期内的发票数据（销项 + 进项抵扣）—— 单一真相源。

    被 routers/tax.py（报表页）与 generate_vat_declaration（申报表）、
    engine_tax_check（税务核对）共用，避免双轨计算导致一般纳税人进项抵扣
    在某一路径遗漏（历史 bug：generate_vat_declaration 未传 input_tax_l1，
    造成一般纳税人应纳税额虚高、附加税虚高，并经 generate_income_tax_prepayment 传播至所得税）。

    日期边界：左闭右开 [start_date, end_date_exclusive)。
    进项抵扣规则：仅一般纳税人，且仅已认证的增值税专用发票可抵扣。

    架构约束（project_memory）：只允许开票订单录入，不存在无票收入兜底。
    所有提交给税务局的报表必须且仅从发票表取数。
    """
    account = db.query(models.Account).filter(models.Account.id == account_id).first()
    if not account:
        raise BusinessError(code=ErrorCode.ORDER_NOT_FOUND, data={"order_type": "账本", "order_id": account_id})

    out_invoices = db.query(models.Invoice).filter(
        models.Invoice.account_id == account_id,
        models.Invoice.direction == InvoiceDirection.OUT,
        models.Invoice.issue_date_l1 >= start_date,
        models.Invoice.issue_date_l1 < end_date_exclusive,
    ).all()

    output_total = Decimal('0')
    ordinary_revenue = Decimal('0')
    special_revenue = Decimal('0')
    output_tax_l1 = Decimal('0')
    for inv in out_invoices:
        rev = _d(inv.amount_without_tax_l1)
        output_total += rev
        output_tax_l1 += _d(inv.tax_amount_l1)
        # 按发票类型拆分：小规模普票可享受免税，专票不享受
        if inv.invoice_type == InvoiceType.SPECIAL:
            special_revenue += rev
        else:
            ordinary_revenue += rev

    input_total = Decimal('0')
    input_tax_l1 = Decimal('0')
    in_invoices = []
    if account.taxpayer_type_l3 == TaxpayerType.GENERAL:
        in_invoices = db.query(models.Invoice).filter(
            models.Invoice.account_id == account_id,
            models.Invoice.direction == InvoiceDirection.IN,
            models.Invoice.issue_date_l1 >= start_date,
            models.Invoice.issue_date_l1 < end_date_exclusive,
        ).all()
        for inv in in_invoices:
            # 进项抵扣：仅已认证的增值税专用发票
            if inv.invoice_type == InvoiceType.SPECIAL and inv.certification_status_l3 == CertificationStatus.CERTIFIED:
                input_total += _d(inv.amount_without_tax_l1)
                input_tax_l1 += _d(inv.tax_amount_l1)

    return {
        "account": account,
        "out_invoices": out_invoices,
        "in_invoices": in_invoices,
        "output_total": output_total,
        "ordinary_revenue": ordinary_revenue,
        "special_revenue": special_revenue,
        "output_tax_l1": output_tax_l1,
        "input_total": input_total,
        "input_tax_l1": input_tax_l1,
    }


@reads("Account.taxpayer_type_l3", tier=TIER_L3, source="policy")
@reads("Invoice.amount_without_tax_l1", tier=TIER_L1, source="external")
@reads("Invoice.tax_amount_l1", tier=TIER_L1, source="external")
def generate_vat_declaration(db: Session, account_id: int, year: int, quarter: int):
    """生成增值税纳税申报表"""
    start_date, end_date_exclusive = _quarter_range(year, quarter)

    agg = aggregate_vat_invoices(db, account_id, start_date, end_date_exclusive)
    account = agg["account"]

    profile = build_profile(account)
    carry_forward_l1 = compute_carry_forward(db, account, start_date)
    vat_result = policy_vat(
        profile=profile,
        total_revenue_l1=agg["output_total"],
        input_tax_l1=agg["input_tax_l1"],
        output_tax_l1=agg["output_tax_l1"],
        ordinary_revenue=agg["ordinary_revenue"],
        special_revenue=agg["special_revenue"],
        carry_forward_l1=carry_forward_l1,
    )

    # 已预缴税额（从之前的季度申报）
    tax_paid = compute_vat_prepaid(db, account_id, year, quarter)

    # 应补退税额
    tax_supplement = vat_result.tax_payable - tax_paid

    return {
        "year": year,
        "quarter": quarter,
        "period_start": start_date.strftime("%Y-%m-%d"),
        "period_end": (end_date_exclusive - timedelta(days=1)).strftime("%Y-%m-%d"),
        "total_revenue_l1": vat_result.total_revenue_l1.quantize(Q2),
        "input_tax_l1": agg["input_tax_l1"].quantize(Q2),
        "carry_forward_l1": carry_forward_l1.quantize(Q2),
        "tax_rate": vat_result.tax_rate,
        "tax_payable_gross": vat_result.tax_payable_gross,
        "tax_reduction": vat_result.tax_reduction,
        "tax_payable": vat_result.tax_payable,
        "tax_paid": tax_paid.quantize(Q2),
        "tax_supplement": tax_supplement.quantize(Q2),
        "reduction_item": vat_result.reduction_item,
        "reduction_amount": vat_result.reduction_amount,
        "invoice_list": agg["out_invoices"],
    }


# ── 企业所得税预缴申报表 (A类) ──

@reads("Invoice.amount_without_tax_l1", tier=TIER_L1, source="external")
@reads("Account.taxpayer_type_l3", tier=TIER_L3, source="policy")
@reads("AccountMoveLine.credit_l2", tier=TIER_L2, source="engine")
@reads("SaleItem.quantity_l1", tier=TIER_L1, source="external")
@reads("SaleItem.unit_cost_l2", tier=TIER_L2, source="engine")
@reads("Expense.amount_l1", tier=TIER_L1, source="external")
def generate_income_tax_prepayment(db: Session, account_id: int, year: int, quarter: int):
    """生成企业所得税预缴申报表（会计准则口径）"""
    # 确定季度日期范围（左闭右开，与 VAT 申报一致）
    start_date, end_date_exclusive = _quarter_range(year, quarter)
    end_date_str = (end_date_exclusive - timedelta(days=1)).strftime("%Y-%m-%d")

    # 会计准则口径：直接复用利润表，与 /api/income-tax-report 一致。
    from .income_statement import generate_income_statement
    is_data = generate_income_statement(
        db, account_id,
        start_date.strftime("%Y-%m-%d"),
        end_date_str
    )

    operating_revenue = _d(is_data.get("revenue", 0))
    operating_cost = _d(is_data.get("cost_of_goods_sold", 0))
    tax_and_surcharge = _d(is_data.get("tax_surcharges", 0))
    operating_expenses = _d(is_data.get("total_operating_expenses", 0)) - tax_and_surcharge
    gross_profit = _d(is_data.get("gross_profit_total", 0))  # 利润总额

    # 实际利润额（简化，不考虑纳税调整）
    actual_profit = gross_profit

    # 使用 policy_engine 计算企业所得税
    account = db.query(models.Account).filter(models.Account.id == account_id).first()
    profile = build_profile(account) if account else None
    if profile is None:
        from policy.entity_profile import EntityProfile
        profile = EntityProfile(vat_type="small_scale", income_type="small_micro", surcharge_halved_l3=True, effective_date=start_date.date())
    ledger = db.query(Ledger).filter(Ledger.code == account.code).first() if account else None
    tax_result = policy_income_tax(
        profile=profile,
        profit=actual_profit,
    )

    # 已预缴所得税额：汇总同年之前季度的 tax_income 计提
    year_start = datetime(year, 1, 1)
    prepaid_tax = Decimal('0')
    if ledger:
        prev_q_end = start_date - timedelta(days=1)
        prepaid = _d(db.query(sqlfunc.coalesce(sqlfunc.sum(AccountMoveLine.credit_l2), 0)).join(
            AccountMove, AccountMoveLine.move_id == AccountMove.id
        ).filter(
            AccountMove.ledger_id == ledger.id,
            AccountMove.source_model == "tax_income",
            AccountMove.date_l1 >= year_start,
            AccountMove.date_l1 <= prev_q_end,
        ).scalar())
        prepaid_rev = _d(db.query(sqlfunc.coalesce(sqlfunc.sum(AccountMoveLine.debit_l2), 0)).join(
            AccountMove, AccountMoveLine.move_id == AccountMove.id
        ).filter(
            AccountMove.ledger_id == ledger.id,
            AccountMove.source_model == "tax_income_reversal",
            AccountMove.date_l1 >= year_start,
            AccountMove.date_l1 <= prev_q_end,
        ).scalar())
        prepaid_tax = (prepaid - prepaid_rev).quantize(Q2)

    # 本期应补退所得税额
    tax_supplement = tax_result.actual_tax - prepaid_tax

    return {
        "year": year,
        "quarter": quarter,
        "period_start": start_date.strftime("%Y-%m-%d"),
        "period_end": end_date_str,
        "operating_revenue": operating_revenue.quantize(Q2),
        "operating_cost": operating_cost.quantize(Q2),
        "tax_and_surcharge": tax_and_surcharge.quantize(Q2),
        "operating_expenses": operating_expenses.quantize(Q2),
        "gross_profit": gross_profit.quantize(Q2),
        "special_business_income": Decimal('0').quantize(Q2),
        "tax_exempt_income": Decimal('0').quantize(Q2),
        "tax_deduction_income": Decimal('0').quantize(Q2),
        "additional_deduction": Decimal('0').quantize(Q2),
        "tax_reduction_income": Decimal('0').quantize(Q2),
        "actual_profit": tax_result.profit.quantize(Q2),
        "tax_rate": tax_result.tax_rate,
        "tax_payable": tax_result.tax_payable.quantize(Q2),
        "small_micro_discount": tax_result.reduction_amount.quantize(Q2),
        "actual_tax_payable": tax_result.actual_tax.quantize(Q2),
        "special_business_prepaid": Decimal('0').quantize(Q2),
        "prepaid_tax": prepaid_tax.quantize(Q2),
        "tax_supplement": tax_supplement.quantize(Q2)
    }


# ── 资产加速折旧明细表 (A201020) ──

@reads("FixedAsset.salvage_rate_l3", tier=TIER_L3, source="policy")
@reads("FixedAsset.useful_life_l3", tier=TIER_L3, source="policy")
@reads("FixedAsset.depreciation_method_l3", tier=TIER_L3, source="policy")
@reads("FixedAsset.original_value_l1", tier=TIER_L1, source="external")
@reads("FixedAssetDepreciation.accumulated_after_l2", tier=TIER_L2, source="engine")
def generate_asset_depreciation_detail(db: Session, account_id: int, year: int, quarter: int):
    """生成资产加速折旧明细表"""
    # 确定季度日期范围（统一用 _quarter_range 左闭右开，与其他税务函数一致）
    start_date, end_date_exclusive = _quarter_range(year, quarter)
    end_date = end_date_exclusive - timedelta(days=1)

    # 固定资产明细
    assets = []
    total_original_value = Decimal('0')
    total_depreciation = Decimal('0')
    total_accumulated = Decimal('0')

    fixed_assets = db.query(models.FixedAsset).filter(
        models.FixedAsset.account_id == account_id,
        models.FixedAsset.status == "在用"
    ).all()

    for asset in fixed_assets:
        if asset.start_date_l1 and asset.start_date_l1 <= end_date.date():
            # 计算本期折旧（使用 AccountingEngine）
            months = (end_date.year - asset.start_date_l1.year) * 12 + (end_date.month - asset.start_date_l1.month)
            if 0 < months <= asset.useful_life_l3:
                result = _engine.calculate_depreciation_straight_line(
                    original_value=_d(asset.original_value_l1),
                    salvage_rate=_d(asset.salvage_rate_l3),
                    useful_life=asset.useful_life_l3,
                    months_used=months
                )
                period_depreciation = result.monthly_depreciation
                accumulated = result.accumulated_depreciation
            else:
                period_depreciation = Decimal('0')
                last_dep = db.query(sqlfunc.max(models.FixedAssetDepreciation.accumulated_after_l2)).filter(
                    models.FixedAssetDepreciation.asset_id == asset.id,
                    models.FixedAssetDepreciation.account_id == account_id
                ).scalar()
                accumulated = _d(last_dep) if last_dep else Decimal('0')

            assets.append({
                "name": asset.name,
                "category": asset.category or "固定资产",
                "original_value": _d(asset.original_value_l1).quantize(Q2),
                "depreciation_method": asset.depreciation_method_l3,
                "useful_life": asset.useful_life_l3,
                "period_depreciation": period_depreciation.quantize(Q2),
                "accumulated_depreciation": accumulated.quantize(Q2)
            })

            total_original_value += _d(asset.original_value_l1)
            total_depreciation += period_depreciation
            total_accumulated += accumulated

    return {
        "year": year,
        "quarter": quarter,
        "account_id": account_id,
        "assets": assets,
        "total_original_value": total_original_value.quantize(Q2),
        "total_depreciation": total_depreciation.quantize(Q2),
        "total_accumulated": total_accumulated.quantize(Q2)
    }
