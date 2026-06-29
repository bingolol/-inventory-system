"""税务申报：增值税/企业所得税/资产折旧明细"""

from datetime import datetime, timedelta
from decimal import Decimal
from sqlalchemy.orm import Session
from sqlalchemy import func as sqlfunc

import models
from enums import (OrderStatus, InvoiceDirection, InvoiceType,
                   CertificationStatus, TaxpayerType)
from utils import _d, Q2
from errors import BusinessError, ErrorCode
from accounting_engine import AccountingEngine
from models_finance import Ledger, LedgerAccount, AccountMove, AccountMoveLine

_engine = AccountingEngine()

def _quarter_range(year: int, quarter: int):
    """返回季度 [start_date, end_date_exclusive)（左闭右开，覆盖属期最后一天全天）。

    统一使用左闭右开区间，避免 23:59:59 与 <next_start 两种写法在 DateTime 字段上
    产生边界漂移。返回的 end_date 为下一季度首日 00:00:00。
    """
    start_month = (quarter - 1) * 3 + 1
    start_date = datetime(year, start_month, 1)
    if quarter == 4:
        end_date = datetime(year + 1, 1, 1)
    else:
        end_date = datetime(year, quarter * 3 + 1, 1)
    return start_date, end_date


def aggregate_vat_invoices(db: Session, account_id: int, start_date: datetime, end_date_exclusive: datetime):
    """汇总一个增值税属期内的发票数据（销项 + 进项抵扣）—— 单一真相源。

    被 routers/tax.py（报表页）与 generate_vat_declaration（申报表）共用，
    避免双轨计算导致一般纳税人进项抵扣在某一路径遗漏（历史 bug：
    generate_vat_declaration 未传 input_tax，造成一般纳税人应纳税额虚高、
    附加税虚高，并经 generate_income_tax_prepayment 传播至所得税）。

    日期边界：左闭右开 [start_date, end_date_exclusive)。
    进项抵扣规则：仅一般纳税人，且仅已认证的增值税专用发票可抵扣。
    """
    account = db.query(models.Account).filter(models.Account.id == account_id).first()
    if not account:
        raise BusinessError(code=ErrorCode.ORDER_NOT_FOUND, data={"order_type": "账本", "order_id": account_id})

    out_invoices = db.query(models.Invoice).filter(
        models.Invoice.account_id == account_id,
        models.Invoice.direction == InvoiceDirection.OUT,
        models.Invoice.issue_date >= start_date,
        models.Invoice.issue_date < end_date_exclusive,
    ).all()

    output_total = Decimal('0')
    ordinary_revenue = Decimal('0')
    special_revenue = Decimal('0')
    output_tax = Decimal('0')
    for inv in out_invoices:
        rev = _d(inv.amount_without_tax)
        output_total += rev
        output_tax += _d(inv.tax_amount)
        # 按发票类型拆分：小规模普票可享受免税，专票不享受
        if inv.invoice_type == InvoiceType.SPECIAL:
            special_revenue += rev
        else:
            ordinary_revenue += rev

    input_total = Decimal('0')
    input_tax = Decimal('0')
    in_invoices = []
    if account.taxpayer_type == TaxpayerType.GENERAL:
        in_invoices = db.query(models.Invoice).filter(
            models.Invoice.account_id == account_id,
            models.Invoice.direction == InvoiceDirection.IN,
            models.Invoice.issue_date >= start_date,
            models.Invoice.issue_date < end_date_exclusive,
        ).all()
        for inv in in_invoices:
            # 进项抵扣：仅已认证的增值税专用发票
            if inv.invoice_type == InvoiceType.SPECIAL and inv.certification_status == CertificationStatus.CERTIFIED:
                input_total += _d(inv.amount_without_tax)
                input_tax += _d(inv.tax_amount)

    return {
        "account": account,
        "out_invoices": out_invoices,
        "in_invoices": in_invoices,
        "output_total": output_total,
        "ordinary_revenue": ordinary_revenue,
        "special_revenue": special_revenue,
        "output_tax": output_tax,
        "input_total": input_total,
        "input_tax": input_tax,
    }


def generate_vat_declaration(db: Session, account_id: int, year: int, quarter: int):
    """生成增值税纳税申报表"""
    start_date, end_date_exclusive = _quarter_range(year, quarter)

    agg = aggregate_vat_invoices(db, account_id, start_date, end_date_exclusive)
    account = agg["account"]
    taxpayer_type = account.taxpayer_type if account else "small_scale"

    # 使用 AccountingEngine 计算增值税（单一真相源：传入销项+进项，避免硬编码估算）
    vat_result = _engine.calculate_vat(
        total_revenue=agg["output_total"],
        taxpayer_type=taxpayer_type,
        input_tax=agg["input_tax"],
        output_tax=agg["output_tax"],
        ordinary_revenue=agg["ordinary_revenue"],
        special_revenue=agg["special_revenue"],
    )

    # 已预缴税额（从之前的季度申报）
    tax_paid = Decimal('0')

    # 应补退税额
    tax_supplement = vat_result.tax_payable - tax_paid

    return {
        "year": year,
        "quarter": quarter,
        "period_start": start_date.strftime("%Y-%m-%d"),
        "period_end": (end_date_exclusive - timedelta(days=1)).strftime("%Y-%m-%d"),
        "total_revenue": vat_result.total_revenue.quantize(Q2),
        "tax_rate": vat_result.tax_rate,
        "tax_payable_gross": vat_result.tax_payable_gross,
        "tax_reduction": vat_result.tax_reduction,
        "tax_payable": vat_result.tax_payable,
        "tax_paid": tax_paid.quantize(Q2),
        "tax_supplement": tax_supplement.quantize(Q2),
        "surcharge_education": vat_result.surcharge_education,
        "surcharge_local_education": vat_result.surcharge_local_education,
        "surcharge_urban_construction": vat_result.surcharge_urban_construction,
        "surcharge_total": vat_result.surcharge_total,
        "reduction_item": vat_result.reduction_item,
        "reduction_amount": vat_result.reduction_amount,
        "invoice_list": agg["out_invoices"]
    }


# ── 企业所得税预缴申报表 (A类) ──

def generate_income_tax_prepayment(db: Session, account_id: int, year: int, quarter: int):
    """生成企业所得税预缴申报表"""
    # 确定季度日期范围（左闭右开，与 VAT 申报一致）
    start_date, end_date_exclusive = _quarter_range(year, quarter)

    # 营业收入 = 销项发票不含税金额（发票说话，取消经营口径的含税订单收入）
    operating_revenue = _d(db.query(sqlfunc.sum(models.Invoice.amount_without_tax)).filter(
        models.Invoice.account_id == account_id,
        models.Invoice.direction == InvoiceDirection.OUT,
        models.Invoice.issue_date >= start_date,
        models.Invoice.issue_date < end_date_exclusive
    ).scalar())

    # 增值税减免加回收入（财税〔2008〕151号：减免的增值税需计入应纳税所得额）
    # 从总账 6301（营业外收入-税收减免）贷方发生额获取
    ledger = db.query(Ledger).filter(Ledger.code == (db.query(models.Account).filter(
        models.Account.id == account_id).first().code if db.query(models.Account).filter(
        models.Account.id == account_id).first() else "")).first()
    if ledger:
        vat_exemption_income = _d(db.query(sqlfunc.sum(AccountMoveLine.credit)).join(
            LedgerAccount, AccountMoveLine.ledger_account_id == LedgerAccount.id
        ).join(AccountMove, AccountMoveLine.move_id == AccountMove.id).filter(
            LedgerAccount.ledger_id == ledger.id, LedgerAccount.code == "6301",
            AccountMove.date >= start_date, AccountMove.date < end_date_exclusive
        ).scalar())
    else:
        vat_exemption_income = Decimal('0')
    operating_revenue += vat_exemption_income

    # 营业成本 = Σ(SaleItem.quantity × SaleItem.unit_cost)（移动加权平均出库成本，单一真相源）
    operating_cost = Decimal('0')
    completed_sales = db.query(models.SaleOrder).filter(
        models.SaleOrder.account_id == account_id,
        models.SaleOrder.sale_date >= start_date,
        models.SaleOrder.sale_date < end_date_exclusive,
        models.SaleOrder.status == OrderStatus.COMPLETED
    ).all()
    for order in completed_sales:
        for item in order.items:
            # 单一真相源：读 SaleItem.unit_cost（出库时锁定的加权平均成本），
            # 禁止用 Product.purchase_price（主数据静态字段，不反映实际采购成本）
            unit_cost = Decimal(str(item.unit_cost)) if item.unit_cost else Decimal('0')
            operating_cost += Decimal(str(item.quantity)) * unit_cost

    # 营业费用
    operating_expenses = _d(db.query(sqlfunc.sum(models.Expense.amount)).filter(
        models.Expense.account_id == account_id,
        models.Expense.expense_date >= start_date,
        models.Expense.expense_date < end_date_exclusive
    ).scalar())

    # 税金及附加（增值税附加税）
    # 从增值税申报表获取附加税金额（quarter 已是入参，无需从日期反推）
    vat_data = generate_vat_declaration(db, account_id, year, quarter)
    tax_and_surcharge = vat_data['surcharge_total']

    # 利润总额 = 营业收入 - 营业成本 - 税金及附加 - 营业费用
    gross_profit = operating_revenue - operating_cost - tax_and_surcharge - operating_expenses

    # 实际利润额（简化，不考虑纳税调整）
    actual_profit = gross_profit

    # 使用 AccountingEngine 计算企业所得税
    # 单一真相源：从账本读取纳税人类型和主体类型，禁止硬编码
    # 所得税纳税人类型映射：VAT 口径 small_scale → 所得税口径 small_micro（5%实际税负：25%×20%）
    account = db.query(models.Account).filter(models.Account.id == account_id).first()
    raw_type = account.taxpayer_type if account and account.taxpayer_type else "small_scale"
    income_tax_type = "small_micro" if raw_type in ("small_scale", "small_micro") else "general"
    entity_type = account.type if account and account.type else "company"
    tax_result = _engine.calculate_income_tax(
        profit=actual_profit,
        taxpayer_type=income_tax_type,
        entity_type=entity_type,
    )

    # 已预缴所得税额
    prepaid_tax = Decimal('0')

    # 本期应补退所得税额
    tax_supplement = tax_result.actual_tax - prepaid_tax

    return {
        "year": year,
        "quarter": quarter,
        "period_start": start_date.strftime("%Y-%m-%d"),
        "period_end": (end_date_exclusive - timedelta(days=1)).strftime("%Y-%m-%d"),
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
        if asset.start_date and asset.start_date <= end_date.date():
            # 计算本期折旧（使用 AccountingEngine）
            months = (end_date.year - asset.start_date.year) * 12 + (end_date.month - asset.start_date.month)
            if 0 < months <= asset.useful_life:
                result = _engine.calculate_depreciation_straight_line(
                    original_value=_d(asset.original_value),
                    salvage_rate=_d(asset.salvage_rate),
                    useful_life=asset.useful_life,
                    months_used=months
                )
                period_depreciation = result.monthly_depreciation
                accumulated = result.accumulated_depreciation
            else:
                period_depreciation = Decimal('0')
                accumulated = _d(asset.accumulated_depreciation)

            assets.append({
                "name": asset.name,
                "category": asset.category or "固定资产",
                "original_value": _d(asset.original_value).quantize(Q2),
                "depreciation_method": asset.depreciation_method,
                "useful_life": asset.useful_life,
                "period_depreciation": period_depreciation.quantize(Q2),
                "accumulated_depreciation": accumulated.quantize(Q2)
            })

            total_original_value += _d(asset.original_value)
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
