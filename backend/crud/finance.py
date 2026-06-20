"""财务：期初余额 + 资产负债表 + 利润表 + 现金流量 + 固定资产 + 无形资产

写操作已迁移至 commands 层（CreateOpeningBalance/UpdateOpeningBalance/CreateCashFlowTransaction 等）。
本模块保留查询、报表生成和少量仍被 router 直接调用的写操作。
"""

import logging
from datetime import datetime
from decimal import Decimal
from sqlalchemy.orm import Session
from sqlalchemy import func as sqlfunc
import models, schemas

from enums import OrderStatus, PaymentStatus, PaymentMethod, InvoiceDirection, FlowCategory
from .base import _log
from utils import _d, Q2
from errors import BusinessError, ErrorCode
from accounting_engine import AccountingEngine

_engine = AccountingEngine()

logger = logging.getLogger("inventory")


# ── 期初余额 ──

def get_opening_balance(db: Session, account_id: int, opening_balance_id: int):
    return db.query(models.OpeningBalance).filter(
        models.OpeningBalance.account_id == account_id,
        models.OpeningBalance.id == opening_balance_id
    ).first()


def get_opening_balance_by_date(db: Session, account_id: int, date: str):
    return db.query(models.OpeningBalance).filter(
        models.OpeningBalance.account_id == account_id,
        models.OpeningBalance.date == datetime.strptime(date, "%Y-%m-%d").date()
    ).first()


def list_opening_balances(db: Session, account_id: int):
    return db.query(models.OpeningBalance).filter(
        models.OpeningBalance.account_id == account_id
    ).order_by(models.OpeningBalance.date.desc()).all()


def delete_opening_balance(db: Session, account_id: int, opening_balance_id: int, operator: str = "user"):
    opening_balance = get_opening_balance(db, account_id, opening_balance_id)
    if not opening_balance:
        return False
    _log(db, account_id, "delete", "opening_balance", opening_balance_id, f"删除期初余额: {opening_balance.date}", operator=operator)
    db.delete(opening_balance)
    db.flush()
    return True


def get_latest_opening_balance(db: Session, account_id: int, date: str = None):
    query = db.query(models.OpeningBalance).filter(models.OpeningBalance.account_id == account_id)
    if date:
        query_date = datetime.strptime(date, "%Y-%m-%d").date()
        query = query.filter(models.OpeningBalance.date <= query_date)
    return query.order_by(models.OpeningBalance.date.desc()).first()


# ── 资产负债表 (会小企01表) ──

def generate_balance_sheet(db: Session, account_id: int, date: str):
    """生成资产负债表"""
    query_date = datetime.strptime(date, "%Y-%m-%d").date()
    opening_balance = get_latest_opening_balance(db, account_id, date)

    if not opening_balance:
        opening_date = datetime(2000, 1, 1).date()
        opening_cash = Decimal('0')
        opening_bank = Decimal('0')
        opening_retained_earnings = Decimal('0')
        opening_fixed_assets_original = Decimal('0')
        opening_accumulated_depreciation = Decimal('0')
        opening_intangible_assets_original = Decimal('0')
        opening_accumulated_amortization = Decimal('0')
        opening_accounts_payable = Decimal('0')
        opening_tax_payable = Decimal('0')
        opening_long_term_borrowings = Decimal('0')
        opening_paid_in_capital = Decimal('0')
    else:
        opening_date = opening_balance.date
        opening_cash = _d(opening_balance.cash_balance)
        opening_bank = _d(opening_balance.bank_balance)
        opening_retained_earnings = _d(opening_balance.retained_earnings)
        opening_fixed_assets_original = _d(opening_balance.fixed_assets_original)
        opening_accumulated_depreciation = _d(opening_balance.accumulated_depreciation)
        opening_intangible_assets_original = _d(opening_balance.intangible_assets_original)
        opening_accumulated_amortization = _d(opening_balance.accumulated_amortization)
        opening_accounts_payable = _d(opening_balance.accounts_payable)
        opening_tax_payable = _d(opening_balance.tax_payable)
        opening_long_term_borrowings = _d(opening_balance.long_term_borrowings)
        opening_paid_in_capital = _d(opening_balance.paid_in_capital)

    # ── 流动资产 ──
    sales_received = _d(db.query(sqlfunc.sum(models.SaleOrder.total_price)).filter(
        models.SaleOrder.account_id == account_id,
        models.SaleOrder.sale_date >= opening_date,
        models.SaleOrder.sale_date <= query_date,
        models.SaleOrder.status == OrderStatus.COMPLETED,
        models.SaleOrder.payment_status == PaymentStatus.PAID
    ).scalar())

    purchase_paid = _d(db.query(sqlfunc.sum(models.PurchaseOrder.total_price)).filter(
        models.PurchaseOrder.account_id == account_id,
        models.PurchaseOrder.purchase_date >= opening_date,
        models.PurchaseOrder.purchase_date <= query_date,
        models.PurchaseOrder.status == OrderStatus.COMPLETED,
        models.PurchaseOrder.payment_status == PaymentStatus.PAID,
        models.PurchaseOrder.payment_method == PaymentMethod.COMPANY
    ).scalar())

    expense_paid = _d(db.query(sqlfunc.sum(models.Expense.amount)).filter(
        models.Expense.account_id == account_id,
        models.Expense.expense_date >= opening_date,
        models.Expense.expense_date <= query_date,
        models.Expense.payment_method == PaymentMethod.COMPANY
    ).scalar())

    # 货币资金计算（权责发生制）
    # 优先使用银行账户余额（反映实际收支），否则用期初余额
    has_bank_accounts = db.query(models.BankAccount).filter(
        models.BankAccount.account_id == account_id
    ).first() is not None

    if has_bank_accounts:
        # 从银行账户表读取余额
        bank_balance = _d(db.query(sqlfunc.sum(models.BankAccount.balance)).filter(
            models.BankAccount.account_id == account_id
        ).scalar())
        ending_cash = Decimal('0')
        ending_bank = bank_balance
    else:
        # 没有银行账户时，使用期初余额
        ending_cash = opening_cash
        ending_bank = opening_bank

    accounts_receivable = _d(db.query(sqlfunc.sum(models.SaleOrder.total_price)).filter(
        models.SaleOrder.account_id == account_id,
        models.SaleOrder.sale_date >= opening_date,
        models.SaleOrder.sale_date <= query_date,
        models.SaleOrder.status == OrderStatus.COMPLETED,
        models.SaleOrder.payment_status == PaymentStatus.UNPAID
    ).scalar())

    inventory_value = Decimal('0')
    for inv in db.query(models.Inventory).filter(models.Inventory.account_id == account_id).all():
        if inv.product and inv.product.purchase_price:
            inventory_value += Decimal(str(inv.quantity)) * _d(inv.product.purchase_price)

    # ── 非流动资产 ──
    # 固定资产
    fixed_assets = db.query(models.FixedAsset).filter(
        models.FixedAsset.account_id == account_id,
        models.FixedAsset.status == "在用"
    ).all()
    
    # 固定资产原值 = 期初 + 期间新增
    fixed_assets_original = opening_fixed_assets_original
    accumulated_depreciation = opening_accumulated_depreciation
    
    for asset in fixed_assets:
        # 累加所有在用固定资产的原值
        fixed_assets_original += _d(asset.original_value)
        
        if asset.start_date and asset.start_date <= query_date:
            # 计算累计折旧（使用 AccountingEngine）
            months = (query_date.year - asset.start_date.year) * 12 + (query_date.month - asset.start_date.month)
            if months > 0:
                result = _engine.calculate_depreciation_straight_line(
                    original_value=_d(asset.original_value),
                    salvage_rate=_d(asset.salvage_rate),
                    useful_life=asset.useful_life,
                    months_used=months
                )
                accumulated_depreciation += result.accumulated_depreciation
    
    fixed_assets_net = fixed_assets_original - accumulated_depreciation
    
    # 无形资产
    intangible_assets = db.query(models.IntangibleAsset).filter(
        models.IntangibleAsset.account_id == account_id,
        models.IntangibleAsset.status == "使用中"
    ).all()
    
    intangible_assets_original = opening_intangible_assets_original
    accumulated_amortization = opening_accumulated_amortization
    
    for asset in intangible_assets:
        if asset.start_date and asset.start_date <= query_date:
            # 计算累计摊销
            months = (query_date.year - asset.start_date.year) * 12 + (query_date.month - asset.start_date.month)
            if months > 0:
                monthly_amortization = _d(asset.original_value) / asset.useful_life
                asset_amortization = monthly_amortization * min(months, asset.useful_life)
                accumulated_amortization += asset_amortization
    
    intangible_assets_net = intangible_assets_original - accumulated_amortization
    
    total_non_current_assets = fixed_assets_net + intangible_assets_net

    # ── 流动负债 ──
    po_payable = _d(db.query(sqlfunc.sum(models.PurchaseOrder.total_price)).filter(
        models.PurchaseOrder.account_id == account_id,
        models.PurchaseOrder.purchase_date >= opening_date,
        models.PurchaseOrder.purchase_date <= query_date,
        models.PurchaseOrder.status == OrderStatus.COMPLETED,
        models.PurchaseOrder.payment_status == PaymentStatus.UNPAID
    ).scalar())

    expense_payable = _d(db.query(sqlfunc.sum(models.Expense.amount)).filter(
        models.Expense.account_id == account_id,
        models.Expense.expense_date >= opening_date,
        models.Expense.expense_date <= query_date,
        models.Expense.payment_status == "unpaid"
    ).scalar())

    # 未付款的固定资产（从 FixedAsset 表查询）
    fixed_assets_payable = _d(db.query(sqlfunc.sum(models.FixedAsset.original_value)).filter(
        models.FixedAsset.account_id == account_id,
        models.FixedAsset.status == "在用",
    ).scalar())
    # 减去已付款的固定资产金额（通过 Payment 表查询）
    fixed_asset_paid = _d(db.query(sqlfunc.sum(models.Payment.amount)).filter(
        models.Payment.account_id == account_id,
        models.Payment.payment_type == "purchase",
        models.Payment.related_entity_type.in_(["invoice", "fixed_asset"]),
    ).scalar())
    fixed_asset_payable = max(fixed_assets_payable - fixed_asset_paid, Decimal('0'))

    # 存货价值（未通过采购单入库的部分，需要计入应付账款）
    # 注意：如果存货是通过采购单入库的，已经在 po_payable 中计算了
    # 这里只计算直接入库的存货（如测试数据）
    inventory_payable = Decimal('0')
    # 查询没有对应采购单的库存记录
    inventory_items = db.query(models.Inventory).filter(
        models.Inventory.account_id == account_id
    ).all()
    for inv_item in inventory_items:
        if inv_item.product and inv_item.product.purchase_price:
            inv_value = _d(inv_item.quantity) * _d(inv_item.product.purchase_price)
            # 检查是否已通过采购单入库
            po_items = db.query(models.PurchaseItem).filter(
                models.PurchaseItem.product_id == inv_item.product_id,
                models.PurchaseItem.order.has(account_id=account_id),
            ).all()
            po_quantity = sum(pi.quantity for pi in po_items)
            if inv_item.quantity > po_quantity:
                # 有未通过采购单入库的库存
                extra_quantity = inv_item.quantity - po_quantity
                inventory_payable += _d(extra_quantity) * _d(inv_item.product.purchase_price)

    accounts_payable = po_payable + expense_payable + fixed_asset_payable + inventory_payable

    out_invoices_tax = _d(db.query(sqlfunc.sum(models.Invoice.tax_amount)).filter(
        models.Invoice.account_id == account_id,
        models.Invoice.direction == InvoiceDirection.OUT,
        models.Invoice.issue_date >= opening_date,
        models.Invoice.issue_date <= query_date
    ).scalar())

    in_invoices_tax = _d(db.query(sqlfunc.sum(models.Invoice.tax_amount)).filter(
        models.Invoice.account_id == account_id,
        models.Invoice.direction == InvoiceDirection.IN,
        models.Invoice.issue_date >= opening_date,
        models.Invoice.issue_date <= query_date,
        models.Invoice.certification_status == "certified",
        models.Invoice.invoice_type == "special"
    ).scalar())

    tax_payable = max(out_invoices_tax - in_invoices_tax, Decimal('0'))

    # ── 非流动负债 ──
    long_term_borrowings = opening_long_term_borrowings

    # ── 汇总 ──
    total_current_assets = ending_cash + ending_bank + accounts_receivable + inventory_value
    total_assets = total_current_assets + total_non_current_assets
    
    total_current_liabilities = accounts_payable + tax_payable
    total_non_current_liabilities = long_term_borrowings
    total_liabilities = total_current_liabilities + total_non_current_liabilities

    # ── 所有者权益 ──
    period_revenue = _d(db.query(sqlfunc.sum(models.SaleOrder.total_price)).filter(
        models.SaleOrder.account_id == account_id,
        models.SaleOrder.sale_date >= opening_date,
        models.SaleOrder.sale_date <= query_date,
        models.SaleOrder.status == OrderStatus.COMPLETED
    ).scalar())

    period_cogs = Decimal('0')
    completed_sales = db.query(models.SaleOrder).filter(
        models.SaleOrder.account_id == account_id,
        models.SaleOrder.sale_date >= opening_date,
        models.SaleOrder.sale_date <= query_date,
        models.SaleOrder.status == OrderStatus.COMPLETED
    ).all()
    for order in completed_sales:
        for item in order.items:
            product = db.query(models.Product).filter(
                models.Product.id == item.product_id,
                models.Product.account_id == account_id,
            ).first()
            purchase_price = Decimal(str(product.purchase_price)) if product and product.purchase_price else Decimal('0')
            period_cogs += Decimal(str(item.quantity)) * purchase_price

    period_expenses = _d(db.query(sqlfunc.sum(models.Expense.amount)).filter(
        models.Expense.account_id == account_id,
        models.Expense.expense_date >= opening_date,
        models.Expense.expense_date <= query_date
    ).scalar())

    # 计算折旧费用（使用 AccountingEngine）
    depreciation_expense = Decimal('0')
    for asset in fixed_assets:
        if asset.start_date and asset.start_date <= query_date:
            months = (query_date.year - asset.start_date.year) * 12 + (query_date.month - asset.start_date.month)
            if 0 < months <= asset.useful_life:
                result = _engine.calculate_depreciation_straight_line(
                    original_value=_d(asset.original_value),
                    salvage_rate=_d(asset.salvage_rate),
                    useful_life=asset.useful_life,
                    months_used=months
                )
                depreciation_expense += result.accumulated_depreciation

    # 计算摊销费用
    amortization_expense = Decimal('0')
    for asset in intangible_assets:
        if asset.start_date and asset.start_date <= query_date:
            months = (query_date.year - asset.start_date.year) * 12 + (query_date.month - asset.start_date.month)
            if 0 < months <= asset.useful_life:
                monthly_amortization = _d(asset.original_value) / asset.useful_life
                amortization_expense += monthly_amortization

    period_profit = period_revenue - period_cogs - period_expenses - depreciation_expense - amortization_expense
    paid_in_capital = opening_paid_in_capital
    retained_earnings = opening_retained_earnings + period_profit
    total_equity = paid_in_capital + retained_earnings

    if abs(total_assets - (total_liabilities + total_equity)) > Decimal('0.01'):
        raise BusinessError(
            code=ErrorCode.BALANCE_SHEET_UNBALANCED,
            message=f"资产负债表不平衡: 资产={total_assets}, 负债+权益={total_liabilities + total_equity}",
            data={"assets": float(total_assets), "liabilities_equity": float(total_liabilities + total_equity)}
        )

    return {
        "date": date,
        # 资产
        "monetary_funds": (ending_cash + ending_bank).quantize(Q2),
        "accounts_receivable": accounts_receivable.quantize(Q2),
        "prepayments": Decimal('0').quantize(Q2),
        "inventory": inventory_value.quantize(Q2),
        "total_current_assets": total_current_assets.quantize(Q2),
        "fixed_assets_original": fixed_assets_original.quantize(Q2),
        "accumulated_depreciation": accumulated_depreciation.quantize(Q2),
        "fixed_assets_net": fixed_assets_net.quantize(Q2),
        "intangible_assets_original": intangible_assets_original.quantize(Q2),
        "accumulated_amortization": accumulated_amortization.quantize(Q2),
        "intangible_assets_net": intangible_assets_net.quantize(Q2),
        "total_non_current_assets": total_non_current_assets.quantize(Q2),
        "total_assets": total_assets.quantize(Q2),
        # 负债和所有者权益
        "accounts_payable": accounts_payable.quantize(Q2),
        "tax_payable": tax_payable.quantize(Q2),
        "total_current_liabilities": total_current_liabilities.quantize(Q2),
        "long_term_borrowings": long_term_borrowings.quantize(Q2),
        "total_non_current_liabilities": total_non_current_liabilities.quantize(Q2),
        "total_liabilities": total_liabilities.quantize(Q2),
        "paid_in_capital": paid_in_capital.quantize(Q2),
        "retained_earnings": retained_earnings.quantize(Q2),
        "total_equity": total_equity.quantize(Q2),
        "total_liabilities_and_equity": (total_liabilities + total_equity).quantize(Q2)
    }


# ── 利润表 (会小企02表) ──

def generate_income_statement(db: Session, account_id: int, start_date: str, end_date: str):
    """生成利润表"""
    start_dt = datetime.strptime(start_date, "%Y-%m-%d")
    end_dt = datetime.strptime(end_date, "%Y-%m-%d")

    # ── 营业收入 ──
    revenue = _d(db.query(sqlfunc.sum(models.SaleOrder.total_price)).filter(
        models.SaleOrder.account_id == account_id,
        models.SaleOrder.sale_date >= start_dt,
        models.SaleOrder.sale_date <= end_dt,
        models.SaleOrder.status == OrderStatus.COMPLETED
    ).scalar())

    # ── 营业成本 ──
    cost_of_goods_sold = Decimal('0')
    completed_sales = db.query(models.SaleOrder).filter(
        models.SaleOrder.account_id == account_id,
        models.SaleOrder.sale_date >= start_dt,
        models.SaleOrder.sale_date <= end_dt,
        models.SaleOrder.status == OrderStatus.COMPLETED
    ).all()
    for order in completed_sales:
        for item in order.items:
            product = db.query(models.Product).filter(
                models.Product.id == item.product_id,
                models.Product.account_id == account_id,
            ).first()
            purchase_price = Decimal(str(product.purchase_price)) if product and product.purchase_price else Decimal('0')
            cost_of_goods_sold += Decimal(str(item.quantity)) * purchase_price

    # ── 营业费用（按功能分类）──
    # 销售费用
    selling_expenses = _d(db.query(sqlfunc.sum(models.Expense.amount)).filter(
        models.Expense.account_id == account_id,
        models.Expense.expense_date >= start_dt,
        models.Expense.expense_date <= end_dt,
        models.Expense.functional_category == "销售费用"
    ).scalar())

    # 管理费用
    administrative_expenses = _d(db.query(sqlfunc.sum(models.Expense.amount)).filter(
        models.Expense.account_id == account_id,
        models.Expense.expense_date >= start_dt,
        models.Expense.expense_date <= end_dt,
        models.Expense.functional_category == "管理费用"
    ).scalar())

    # 财务费用
    financial_expenses = _d(db.query(sqlfunc.sum(models.Expense.amount)).filter(
        models.Expense.account_id == account_id,
        models.Expense.expense_date >= start_dt,
        models.Expense.expense_date <= end_dt,
        models.Expense.functional_category == "财务费用"
    ).scalar())

    total_operating_expenses = selling_expenses + administrative_expenses + financial_expenses

    # ── 营业毛利 ──
    gross_profit = revenue - cost_of_goods_sold

    # ── 营业利润 ──
    operating_profit = gross_profit - total_operating_expenses

    # ── 营业外收支 ──
    non_operating_income = Decimal('0')
    non_operating_expense = Decimal('0')

    # ── 利润总额 ──
    gross_profit_total = operating_profit + non_operating_income - non_operating_expense

    # ── 所得税费用（调用 AccountingEngine 计算）──
    from accounting_engine import AccountingEngine
    engine = AccountingEngine()
    if gross_profit_total > 0:
        tax_result = engine.calculate_income_tax(profit=gross_profit_total, taxpayer_type='small_micro')
        income_tax_expense = tax_result.actual_tax
    else:
        income_tax_expense = Decimal('0')

    # ── 净利润 ──
    net_profit = gross_profit_total - income_tax_expense

    return {
        "period": f"{start_date} 至 {end_date}",
        "revenue": revenue.quantize(Q2),
        "cost_of_goods_sold": cost_of_goods_sold.quantize(Q2),
        "gross_profit": gross_profit.quantize(Q2),
        "selling_expenses": selling_expenses.quantize(Q2),
        "administrative_expenses": administrative_expenses.quantize(Q2),
        "financial_expenses": financial_expenses.quantize(Q2),
        "total_operating_expenses": total_operating_expenses.quantize(Q2),
        "operating_profit": operating_profit.quantize(Q2),
        "non_operating_income": non_operating_income.quantize(Q2),
        "non_operating_expense": non_operating_expense.quantize(Q2),
        "gross_profit_total": gross_profit_total.quantize(Q2),
        "income_tax_expense": income_tax_expense.quantize(Q2),
        "net_profit": net_profit.quantize(Q2)
    }


# ── 现金流量 ──

def list_cash_flow_transactions(db: Session, account_id: int, skip: int = 0, limit: int = 100,
                                 start_date: str = None, end_date: str = None, flow_category: str = None):
    q = db.query(models.CashFlowTransaction).filter(models.CashFlowTransaction.account_id == account_id)
    if start_date:
        q = q.filter(models.CashFlowTransaction.transaction_date >= start_date)
    if end_date:
        q = q.filter(models.CashFlowTransaction.transaction_date <= end_date + " 23:59:59")
    if flow_category:
        q = q.filter(models.CashFlowTransaction.flow_category == flow_category)
    total = q.count()
    items = q.order_by(models.CashFlowTransaction.transaction_date.desc()).offset(skip).limit(limit).all()
    return total, items


def generate_cash_flow_statement(db: Session, account_id: int, start_date: str, end_date: str):
    start_dt = datetime.strptime(start_date, "%Y-%m-%d")
    end_dt = datetime.strptime(end_date, "%Y-%m-%d")

    opening_balance = get_latest_opening_balance(db, account_id, start_date)
    beginning_cash_balance = (_d(opening_balance.cash_balance) + _d(opening_balance.bank_balance)) if opening_balance else Decimal('0')

    # ── 经营活动（只从银行流水读取，避免双重计算）──
    operating_inflows = Decimal('0')
    operating_outflows = Decimal('0')

    # 投资活动
    investing_inflows = Decimal('0')
    investing_outflows = Decimal('0')

    # 筹资活动
    financing_inflows = Decimal('0')
    financing_outflows = Decimal('0')

    # 手动录入的现金流水（用于投资/筹资活动）
    cash_transactions = db.query(models.CashFlowTransaction).filter(
        models.CashFlowTransaction.account_id == account_id,
        models.CashFlowTransaction.transaction_date >= start_dt,
        models.CashFlowTransaction.transaction_date <= end_dt
    ).all()

    for tx in cash_transactions:
        if tx.type == "inflow":
            if tx.flow_category == FlowCategory.INVESTING:
                investing_inflows += _d(tx.amount)
            elif tx.flow_category == FlowCategory.FINANCING:
                financing_inflows += _d(tx.amount)
        else:
            if tx.flow_category == FlowCategory.INVESTING:
                investing_outflows += _d(tx.amount)
            elif tx.flow_category == FlowCategory.FINANCING:
                financing_outflows += _d(tx.amount)

    # 从银行流水表读取数据（按 flow_category 分类）
    bank_transactions = db.query(models.BankTransaction).filter(
        models.BankTransaction.account_id == account_id,
        models.BankTransaction.transaction_date >= start_dt,
        models.BankTransaction.transaction_date <= end_dt
    ).all()

    for tx in bank_transactions:
        amount = _d(tx.amount)
        if tx.transaction_type == "inflow":
            if tx.flow_category == FlowCategory.INVESTING:
                investing_inflows += amount
            elif tx.flow_category == FlowCategory.FINANCING:
                financing_inflows += amount
            else:
                operating_inflows += amount
        else:
            if tx.flow_category == FlowCategory.INVESTING:
                investing_outflows += amount
            elif tx.flow_category == FlowCategory.FINANCING:
                financing_outflows += amount
            else:
                operating_outflows += amount

    net_operating = operating_inflows - operating_outflows
    net_investing = investing_inflows - investing_outflows
    net_financing = financing_inflows - financing_outflows
    net_cash_flow = net_operating + net_investing + net_financing
    ending_cash_balance = beginning_cash_balance + net_cash_flow

    return {
        "period": f"{start_date} 至 {end_date}",
        "operating_activities": {
            "inflows": operating_inflows.quantize(Q2),
            "outflows": operating_outflows.quantize(Q2),
            "net": net_operating.quantize(Q2)
        },
        "investing_activities": {
            "inflows": investing_inflows.quantize(Q2),
            "outflows": investing_outflows.quantize(Q2),
            "net": net_investing.quantize(Q2)
        },
        "financing_activities": {
            "inflows": financing_inflows.quantize(Q2),
            "outflows": financing_outflows.quantize(Q2),
            "net": net_financing.quantize(Q2)
        },
        "net_cash_flow": net_cash_flow.quantize(Q2),
        "beginning_cash_balance": beginning_cash_balance.quantize(Q2),
        "ending_cash_balance": ending_cash_balance.quantize(Q2)
    }


# ── 固定资产 ──

def create_fixed_asset(db: Session, account_id: int, data: schemas.FixedAssetCreate, operator: str = "user"):
    """创建固定资产"""
    asset = models.FixedAsset(
        account_id=account_id,
        asset_code=data.asset_code,
        name=data.name,
        category=data.category,
        original_value=data.original_value,
        salvage_rate=data.salvage_rate,
        useful_life=data.useful_life,
        depreciation_method=data.depreciation_method,
        start_date=datetime.strptime(data.start_date, "%Y-%m-%d").date(),
        accumulated_depreciation=data.accumulated_depreciation,
        status=data.status
    )
    db.add(asset)
    db.flush()
    _log(db, account_id, "create", "fixed_asset", asset.id, f"创建固定资产: {data.name}", operator=operator)
    return asset


def get_fixed_asset(db: Session, account_id: int, asset_id: int):
    return db.query(models.FixedAsset).filter(
        models.FixedAsset.account_id == account_id,
        models.FixedAsset.id == asset_id
    ).first()


def list_fixed_assets(db: Session, account_id: int, status: str = None):
    query = db.query(models.FixedAsset).filter(models.FixedAsset.account_id == account_id)
    if status:
        query = query.filter(models.FixedAsset.status == status)
    return query.order_by(models.FixedAsset.created_at.desc()).all()


def update_fixed_asset(db: Session, account_id: int, asset_id: int, data: schemas.FixedAssetUpdate, operator: str = "user"):
    asset = get_fixed_asset(db, account_id, asset_id)
    if not asset:
        return None
    changes = data.model_dump(exclude_unset=True)
    for key, value in changes.items():
        if key == "start_date" and value:
            value = datetime.strptime(value, "%Y-%m-%d").date()
        setattr(asset, key, value)
    db.flush()
    _log(db, account_id, "update", "fixed_asset", asset_id, f"更新固定资产: {asset.name}", operator=operator)
    return asset


def delete_fixed_asset(db: Session, account_id: int, asset_id: int, operator: str = "user"):
    asset = get_fixed_asset(db, account_id, asset_id)
    if not asset:
        return False

    # 清空关联发票的引用
    invoices = db.query(models.Invoice).filter(
        models.Invoice.related_order_id == asset_id,
        models.Invoice.related_order_type == "fixed_asset",
        models.Invoice.account_id == account_id,
    ).all()
    for inv in invoices:
        inv.related_order_id = None
        inv.related_order_type = None

    _log(db, account_id, "delete", "fixed_asset", asset_id, f"删除固定资产: {asset.name}", operator=operator)
    db.delete(asset)
    db.flush()
    return True


# ── 无形资产 ──

def create_intangible_asset(db: Session, account_id: int, data: schemas.IntangibleAssetCreate, operator: str = "user"):
    """创建无形资产"""
    asset = models.IntangibleAsset(
        account_id=account_id,
        asset_code=data.asset_code,
        name=data.name,
        category=data.category,
        original_value=data.original_value,
        useful_life=data.useful_life,
        start_date=datetime.strptime(data.start_date, "%Y-%m-%d").date(),
        accumulated_amortization=data.accumulated_amortization,
        status=data.status
    )
    db.add(asset)
    db.flush()
    _log(db, account_id, "create", "intangible_asset", asset.id, f"创建无形资产: {data.name}", operator=operator)
    return asset


def get_intangible_asset(db: Session, account_id: int, asset_id: int):
    return db.query(models.IntangibleAsset).filter(
        models.IntangibleAsset.account_id == account_id,
        models.IntangibleAsset.id == asset_id
    ).first()


def list_intangible_assets(db: Session, account_id: int, status: str = None):
    query = db.query(models.IntangibleAsset).filter(models.IntangibleAsset.account_id == account_id)
    if status:
        query = query.filter(models.IntangibleAsset.status == status)
    return query.order_by(models.IntangibleAsset.created_at.desc()).all()


def update_intangible_asset(db: Session, account_id: int, asset_id: int, data: schemas.IntangibleAssetUpdate, operator: str = "user"):
    asset = get_intangible_asset(db, account_id, asset_id)
    if not asset:
        return None
    changes = data.model_dump(exclude_unset=True)
    for key, value in changes.items():
        if key == "start_date" and value:
            value = datetime.strptime(value, "%Y-%m-%d").date()
        setattr(asset, key, value)
    db.flush()
    _log(db, account_id, "update", "intangible_asset", asset_id, f"更新无形资产: {asset.name}", operator=operator)
    return asset


def delete_intangible_asset(db: Session, account_id: int, asset_id: int, operator: str = "user"):
    asset = get_intangible_asset(db, account_id, asset_id)
    if not asset:
        return False
    _log(db, account_id, "delete", "intangible_asset", asset_id, f"删除无形资产: {asset.name}", operator=operator)
    db.delete(asset)
    db.flush()
    return True


# ── 增值税纳税申报表 ──

def generate_vat_declaration(db: Session, account_id: int, year: int, quarter: int):
    """生成增值税纳税申报表"""
    # 获取账本的纳税人类型
    account = db.query(models.Account).filter(models.Account.id == account_id).first()
    taxpayer_type = account.taxpayer_type if account else "small_scale"

    # 确定季度日期范围
    if quarter == 1:
        start_date = datetime(year, 1, 1)
        end_date = datetime(year, 3, 31)
    elif quarter == 2:
        start_date = datetime(year, 4, 1)
        end_date = datetime(year, 6, 30)
    elif quarter == 3:
        start_date = datetime(year, 7, 1)
        end_date = datetime(year, 9, 30)
    else:
        start_date = datetime(year, 10, 1)
        end_date = datetime(year, 12, 31)

    # 销项发票
    output_invoices = db.query(models.Invoice).filter(
        models.Invoice.account_id == account_id,
        models.Invoice.direction == InvoiceDirection.OUT,
        models.Invoice.issue_date >= start_date,
        models.Invoice.issue_date <= end_date
    ).all()

    total_revenue = Decimal('0')
    for inv in output_invoices:
        total_revenue += _d(inv.amount_without_tax)

    # 使用 AccountingEngine 计算增值税
    vat_result = _engine.calculate_vat(
        total_revenue=total_revenue,
        taxpayer_type=taxpayer_type
    )

    # 已预缴税额（从之前的季度申报）
    tax_paid = Decimal('0')

    # 应补退税额
    tax_supplement = vat_result.tax_payable - tax_paid

    return {
        "year": year,
        "quarter": quarter,
        "period_start": start_date.strftime("%Y-%m-%d"),
        "period_end": end_date.strftime("%Y-%m-%d"),
        "total_revenue": vat_result.total_revenue.quantize(Q2),
        "tax_rate": vat_result.tax_rate,
        "tax_payable_gross": vat_result.tax_payable_gross,
        "tax_reduction": vat_result.tax_reduction,
        "tax_payable": vat_result.tax_payable,
        "tax_paid": tax_paid.quantize(Q2),
        "tax_supplement": tax_supplement.quantize(Q2),
        "surcharge_education": vat_result.surcharge_education,
        "surcharge_local_education": vat_result.surcharge_local_education,
        "surcharge_stamp": vat_result.surcharge_stamp,
        "surcharge_total": vat_result.surcharge_total,
        "reduction_item": vat_result.reduction_item,
        "reduction_amount": vat_result.reduction_amount,
        "invoice_list": output_invoices
    }


# ── 企业所得税预缴申报表 (A类) ──

def generate_income_tax_prepayment(db: Session, account_id: int, year: int, quarter: int):
    """生成企业所得税预缴申报表"""
    # 确定季度日期范围
    if quarter == 1:
        start_date = datetime(year, 1, 1)
        end_date = datetime(year, 3, 31)
    elif quarter == 2:
        start_date = datetime(year, 1, 1)
        end_date = datetime(year, 6, 30)
    elif quarter == 3:
        start_date = datetime(year, 1, 1)
        end_date = datetime(year, 9, 30)
    else:
        start_date = datetime(year, 1, 1)
        end_date = datetime(year, 12, 31)

    # 营业收入
    operating_revenue = _d(db.query(sqlfunc.sum(models.SaleOrder.total_price)).filter(
        models.SaleOrder.account_id == account_id,
        models.SaleOrder.sale_date >= start_date,
        models.SaleOrder.sale_date <= end_date,
        models.SaleOrder.status == OrderStatus.COMPLETED
    ).scalar())

    # 营业成本
    operating_cost = Decimal('0')
    completed_sales = db.query(models.SaleOrder).filter(
        models.SaleOrder.account_id == account_id,
        models.SaleOrder.sale_date >= start_date,
        models.SaleOrder.sale_date <= end_date,
        models.SaleOrder.status == OrderStatus.COMPLETED
    ).all()
    for order in completed_sales:
        for item in order.items:
            product = db.query(models.Product).filter(
                models.Product.id == item.product_id,
                models.Product.account_id == account_id,
            ).first()
            purchase_price = Decimal(str(product.purchase_price)) if product and product.purchase_price else Decimal('0')
            operating_cost += Decimal(str(item.quantity)) * purchase_price

    # 营业费用
    operating_expenses = _d(db.query(sqlfunc.sum(models.Expense.amount)).filter(
        models.Expense.account_id == account_id,
        models.Expense.expense_date >= start_date,
        models.Expense.expense_date <= end_date
    ).scalar())

    # 税金及附加（增值税附加税）
    # 从增值税申报表获取附加税金额
    from crud.finance import generate_vat_declaration
    quarter_num = 1 if end_date.month <= 3 else (2 if end_date.month <= 6 else (3 if end_date.month <= 9 else 4))
    vat_data = generate_vat_declaration(db, account_id, year, quarter_num)
    tax_and_surcharge = vat_data['surcharge_total']

    # 利润总额 = 营业收入 - 营业成本 - 税金及附加 - 营业费用
    gross_profit = operating_revenue - operating_cost - tax_and_surcharge - operating_expenses

    # 实际利润额（简化，不考虑纳税调整）
    actual_profit = gross_profit

    # 使用 AccountingEngine 计算企业所得税
    tax_result = _engine.calculate_income_tax(
        profit=actual_profit,
        taxpayer_type='small_micro'
    )

    # 已预缴所得税额
    prepaid_tax = Decimal('0')

    # 本期应补退所得税额
    tax_supplement = tax_result.actual_tax - prepaid_tax

    return {
        "year": year,
        "quarter": quarter,
        "period_start": start_date.strftime("%Y-%m-%d"),
        "period_end": end_date.strftime("%Y-%m-%d"),
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
    # 确定季度日期范围
    if quarter == 1:
        start_date = datetime(year, 1, 1)
        end_date = datetime(year, 3, 31)
    elif quarter == 2:
        start_date = datetime(year, 4, 1)
        end_date = datetime(year, 6, 30)
    elif quarter == 3:
        start_date = datetime(year, 7, 1)
        end_date = datetime(year, 9, 30)
    else:
        start_date = datetime(year, 10, 1)
        end_date = datetime(year, 12, 31)

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