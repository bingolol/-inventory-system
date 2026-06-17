"""财务：期初余额 + 资产负债表 + 利润表 + 现金流量 + 固定资产 + 无形资产（含事务包裹和金额精度）"""

import logging
from datetime import datetime
from decimal import Decimal
from sqlalchemy.orm import Session
from sqlalchemy import func as sqlfunc
import models, schemas

from enums import OrderStatus, PaymentStatus, PaymentMethod, InvoiceDirection, FlowCategory
from .base import _log
from utils import _d, Q2

logger = logging.getLogger("inventory")


# ── 期初余额 ──

def create_opening_balance(db: Session, account_id: int, data: schemas.OpeningBalanceCreate, operator: str = "user"):
    """创建期初余额"""
    existing = db.query(models.OpeningBalance).filter(
        models.OpeningBalance.account_id == account_id,
        models.OpeningBalance.date == datetime.strptime(data.date, "%Y-%m-%d").date()
    ).first()
    if existing:
        raise ValueError(f"该日期已存在期初余额: {data.date}")

    # 流动资产
    total_current_assets = _d(data.cash_balance) + _d(data.bank_balance) + _d(data.accounts_receivable) + _d(data.inventory_value)
    # 非流动资产
    fixed_assets_net = _d(data.fixed_assets_original) - _d(data.accumulated_depreciation)
    intangible_assets_net = _d(data.intangible_assets_original) - _d(data.accumulated_amortization)
    total_non_current_assets = fixed_assets_net + intangible_assets_net
    total_assets = total_current_assets + total_non_current_assets
    
    # 流动负债
    total_current_liabilities = _d(data.accounts_payable) + _d(data.tax_payable)
    # 非流动负债
    total_non_current_liabilities = _d(data.long_term_borrowings)
    total_liabilities = total_current_liabilities + total_non_current_liabilities
    
    # 权益
    total_equity = _d(data.paid_in_capital) + _d(data.retained_earnings)
    
    if abs(total_assets - (total_liabilities + total_equity)) > Decimal('0.01'):
        raise ValueError(f"资产负债表不平衡: 资产={total_assets}, 负债+权益={total_liabilities + total_equity}")

    opening_balance = models.OpeningBalance(
        account_id=account_id,
        date=datetime.strptime(data.date, "%Y-%m-%d").date(),
        cash_balance=data.cash_balance,
        bank_balance=data.bank_balance,
        accounts_receivable=data.accounts_receivable,
        inventory_value=data.inventory_value,
        fixed_assets_original=data.fixed_assets_original,
        accumulated_depreciation=data.accumulated_depreciation,
        intangible_assets_original=data.intangible_assets_original,
        accumulated_amortization=data.accumulated_amortization,
        accounts_payable=data.accounts_payable,
        tax_payable=data.tax_payable,
        long_term_borrowings=data.long_term_borrowings,
        paid_in_capital=data.paid_in_capital,
        retained_earnings=data.retained_earnings
    )
    db.add(opening_balance)
    db.flush()
    _log(db, account_id, "create", "opening_balance", opening_balance.id, f"创建期初余额: {data.date}", operator=operator)
    return opening_balance


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


def update_opening_balance(db: Session, account_id: int, opening_balance_id: int, data: schemas.OpeningBalanceUpdate, operator: str = "user"):
    opening_balance = get_opening_balance(db, account_id, opening_balance_id)
    if not opening_balance:
        return None
    changes = data.model_dump(exclude_unset=True)
    for key, value in changes.items():
        if key == "date" and value:
            value = datetime.strptime(value, "%Y-%m-%d").date()
        setattr(opening_balance, key, value)

    # 流动资产
    total_current_assets = _d(opening_balance.cash_balance) + _d(opening_balance.bank_balance) + _d(opening_balance.accounts_receivable) + _d(opening_balance.inventory_value)
    # 非流动资产
    fixed_assets_net = _d(opening_balance.fixed_assets_original) - _d(opening_balance.accumulated_depreciation)
    intangible_assets_net = _d(opening_balance.intangible_assets_original) - _d(opening_balance.accumulated_amortization)
    total_non_current_assets = fixed_assets_net + intangible_assets_net
    total_assets = total_current_assets + total_non_current_assets
    
    # 流动负债
    total_current_liabilities = _d(opening_balance.accounts_payable) + _d(opening_balance.tax_payable)
    # 非流动负债
    total_non_current_liabilities = _d(opening_balance.long_term_borrowings)
    total_liabilities = total_current_liabilities + total_non_current_liabilities
    
    # 权益
    total_equity = _d(opening_balance.paid_in_capital) + _d(opening_balance.retained_earnings)
    
    if abs(total_assets - (total_liabilities + total_equity)) > Decimal('0.01'):
        raise ValueError(f"资产负债表不平衡: 资产={total_assets}, 负债+权益={total_liabilities + total_equity}")

    db.flush()
    _log(db, account_id, "update", "opening_balance", opening_balance_id, f"更新期初余额: {opening_balance.date}", operator=operator)
    return opening_balance


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

    ending_cash = opening_cash + sales_received - purchase_paid - expense_paid
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
    
    fixed_assets_original = opening_fixed_assets_original
    accumulated_depreciation = opening_accumulated_depreciation
    
    for asset in fixed_assets:
        if asset.start_date and asset.start_date <= query_date:
            # 计算累计折旧
            months = (query_date.year - asset.start_date.year) * 12 + (query_date.month - asset.start_date.month)
            if months > 0:
                monthly_depreciation = _d(asset.original_value) * (1 - _d(asset.salvage_rate)) / asset.useful_life
                asset_depreciation = monthly_depreciation * min(months, asset.useful_life)
                accumulated_depreciation += asset_depreciation
    
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
        models.Expense.payment_method == "private_advance"
    ).scalar())

    accounts_payable = po_payable + expense_payable

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
        models.Invoice.certification_status == "certified"
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

    # 计算折旧费用
    depreciation_expense = Decimal('0')
    for asset in fixed_assets:
        if asset.start_date and asset.start_date <= query_date:
            months = (query_date.year - asset.start_date.year) * 12 + (query_date.month - asset.start_date.month)
            if 0 < months <= asset.useful_life:
                monthly_depreciation = _d(asset.original_value) * (1 - _d(asset.salvage_rate)) / asset.useful_life
                depreciation_expense += monthly_depreciation

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
        retained_earnings = total_assets - total_liabilities - paid_in_capital
        total_equity = paid_in_capital + retained_earnings

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

    # ── 所得税费用 ──
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

def create_cash_flow_transaction(db: Session, account_id: int, data: schemas.CashFlowTransactionCreate, operator: str = "user"):
    transaction = models.CashFlowTransaction(
        account_id=account_id,
        type=data.type,
        amount=data.amount,
        flow_category=data.flow_category,
        description=data.description,
        transaction_date=datetime.strptime(data.transaction_date, "%Y-%m-%d"),
        related_entity_type=data.related_entity_type,
        related_entity_id=data.related_entity_id
    )
    db.add(transaction)
    db.flush()
    _log(db, account_id, "create", "cash_flow", transaction.id, f"创建现金流水: {data.type} {data.amount}", operator=operator)
    return transaction


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


def update_cash_flow_transaction(db: Session, account_id: int, transaction_id: int, data: schemas.CashFlowTransactionUpdate, operator: str = "user"):
    transaction = db.query(models.CashFlowTransaction).filter(
        models.CashFlowTransaction.id == transaction_id,
        models.CashFlowTransaction.account_id == account_id
    ).first()
    if not transaction:
        return None
    update_data = data.model_dump(exclude_unset=True)
    if 'transaction_date' in update_data and update_data['transaction_date']:
        update_data['transaction_date'] = datetime.strptime(update_data['transaction_date'], "%Y-%m-%d")
    for key, value in update_data.items():
        setattr(transaction, key, value)
    db.flush()
    _log(db, account_id, "update", "cash_flow", transaction.id, f"更新现金流水", operator=operator)
    return transaction


def delete_cash_flow_transaction(db: Session, account_id: int, transaction_id: int, operator: str = "user"):
    transaction = db.query(models.CashFlowTransaction).filter(
        models.CashFlowTransaction.id == transaction_id,
        models.CashFlowTransaction.account_id == account_id
    ).first()
    if not transaction:
        return False
    _log(db, account_id, "delete", "cash_flow", transaction.id, f"删除现金流水: {transaction.type} {transaction.amount}", operator=operator)
    db.delete(transaction)
    db.flush()
    return True


def generate_cash_flow_statement(db: Session, account_id: int, start_date: str, end_date: str):
    start_dt = datetime.strptime(start_date, "%Y-%m-%d")
    end_dt = datetime.strptime(end_date, "%Y-%m-%d")

    opening_balance = get_latest_opening_balance(db, account_id, start_date)
    beginning_cash_balance = (_d(opening_balance.cash_balance) + _d(opening_balance.bank_balance)) if opening_balance else Decimal('0')

    # 经营活动
    operating_inflows = Decimal('0')
    operating_outflows = Decimal('0')

    sales_receipts = _d(db.query(sqlfunc.sum(models.SaleOrder.total_price)).filter(
        models.SaleOrder.account_id == account_id,
        models.SaleOrder.sale_date >= start_dt,
        models.SaleOrder.sale_date <= end_dt,
        models.SaleOrder.status == OrderStatus.COMPLETED,
        models.SaleOrder.payment_status == PaymentStatus.PAID
    ).scalar())
    operating_inflows += sales_receipts

    purchase_paid = _d(db.query(sqlfunc.sum(models.PurchaseOrder.total_price)).filter(
        models.PurchaseOrder.account_id == account_id,
        models.PurchaseOrder.purchase_date >= start_dt,
        models.PurchaseOrder.purchase_date <= end_dt,
        models.PurchaseOrder.status == OrderStatus.COMPLETED,
        models.PurchaseOrder.payment_status == PaymentStatus.PAID,
        models.PurchaseOrder.payment_method == PaymentMethod.COMPANY
    ).scalar())
    operating_outflows += purchase_paid

    expense_paid = _d(db.query(sqlfunc.sum(models.Expense.amount)).filter(
        models.Expense.account_id == account_id,
        models.Expense.expense_date >= start_dt,
        models.Expense.expense_date <= end_dt,
        models.Expense.payment_method == PaymentMethod.COMPANY
    ).scalar())
    operating_outflows += expense_paid

    # 投资活动
    investing_inflows = Decimal('0')
    investing_outflows = Decimal('0')

    # 筹资活动
    financing_inflows = Decimal('0')
    financing_outflows = Decimal('0')

    # 手动录入的现金流水
    cash_transactions = db.query(models.CashFlowTransaction).filter(
        models.CashFlowTransaction.account_id == account_id,
        models.CashFlowTransaction.transaction_date >= start_dt,
        models.CashFlowTransaction.transaction_date <= end_dt
    ).all()

    for tx in cash_transactions:
        if tx.type == "inflow":
            if tx.flow_category == FlowCategory.OPERATING:
                operating_inflows += _d(tx.amount)
            elif tx.flow_category == FlowCategory.INVESTING:
                investing_inflows += _d(tx.amount)
            elif tx.flow_category == FlowCategory.FINANCING:
                financing_inflows += _d(tx.amount)
        else:
            if tx.flow_category == FlowCategory.OPERATING:
                operating_outflows += _d(tx.amount)
            elif tx.flow_category == FlowCategory.INVESTING:
                investing_outflows += _d(tx.amount)
            elif tx.flow_category == FlowCategory.FINANCING:
                financing_outflows += _d(tx.amount)

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


# ── 增值税纳税申报表 (小规模纳税人) ──

def generate_vat_declaration(db: Session, account_id: int, year: int, quarter: int):
    """生成增值税纳税申报表"""
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

    # 小规模纳税人征收率3%，减按1%征收
    # 本期应纳税额 = 不含税销售额 × 征收率(3%)
    tax_rate = Decimal('0.03')
    tax_payable_gross = total_revenue * tax_rate

    # 减免税额 = 应纳税额 × 2/3（减按1%征收，减免2/3）
    tax_reduction = tax_payable_gross * Decimal('2') / Decimal('3')

    # 应纳税额合计 = 应纳税额 - 减免税额 = 不含税销售额 × 1%
    tax_payable = total_revenue * Decimal('0.01')

    # 已预缴税额（从之前的季度申报）
    tax_paid = Decimal('0')

    # 应补退税额
    tax_supplement = tax_payable - tax_paid

    # 附加税费（2023-2027年小微企业50%减征优惠）
    # 教育费附加：增值税×3%（月销售额≤10万免征）
    # 地方教育附加：增值税×2%（月销售额≤10万免征）
    # 城市维护建设税：增值税×7%（市区，50%减征）
    monthly_revenue = total_revenue / 3
    if monthly_revenue <= Decimal('100000'):
        surcharge_education = Decimal('0')
        surcharge_local_education = Decimal('0')
    else:
        surcharge_education = tax_payable * Decimal('0.03') * Decimal('0.5')
        surcharge_local_education = tax_payable * Decimal('0.02') * Decimal('0.5')
    
    surcharge_stamp = tax_payable * Decimal('0.07') * Decimal('0.5')
    surcharge_total = surcharge_education + surcharge_local_education + surcharge_stamp

    return {
        "year": year,
        "quarter": quarter,
        "period_start": start_date.strftime("%Y-%m-%d"),
        "period_end": end_date.strftime("%Y-%m-%d"),
        "total_revenue": total_revenue.quantize(Q2),
        "tax_rate": tax_rate,
        "tax_payable_gross": tax_payable_gross.quantize(Q2),
        "tax_reduction": tax_reduction.quantize(Q2),
        "tax_payable": tax_payable.quantize(Q2),
        "tax_paid": tax_paid.quantize(Q2),
        "tax_supplement": tax_supplement.quantize(Q2),
        "surcharge_education": surcharge_education.quantize(Q2),
        "surcharge_local_education": surcharge_local_education.quantize(Q2),
        "surcharge_stamp": surcharge_stamp.quantize(Q2),
        "surcharge_total": surcharge_total.quantize(Q2),
        "reduction_item": "小微企业免征增值税" if monthly_revenue <= Decimal('100000') else "小规模纳税人增值税减征",
        "reduction_amount": tax_reduction.quantize(Q2),
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

    # 应纳所得税额（法定税率25%）
    tax_rate = Decimal('0.25')
    tax_payable = actual_profit * tax_rate

    # 小型微利企业减免所得税额
    # 应纳税所得额≤100万：减免80%（实际税率5%）
    # 100万<应纳税所得额≤300万：减免60%（实际税率10%）
    if actual_profit <= Decimal('1000000'):
        small_micro_discount = tax_payable * Decimal('0.80')
    elif actual_profit <= Decimal('3000000'):
        small_micro_discount = tax_payable * Decimal('0.60')
    else:
        small_micro_discount = Decimal('0')

    # 已预缴所得税额
    prepaid_tax = Decimal('0')

    # 本期应补退所得税额
    actual_tax_payable = tax_payable - small_micro_discount
    tax_supplement = actual_tax_payable - prepaid_tax

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
        "actual_profit": actual_profit.quantize(Q2),
        "tax_rate": tax_rate,
        "tax_payable": tax_payable.quantize(Q2),
        "small_micro_discount": small_micro_discount.quantize(Q2),
        "actual_tax_payable": actual_tax_payable.quantize(Q2),
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
            # 计算本期折旧
            months = (end_date.year - asset.start_date.year) * 12 + (end_date.month - asset.start_date.month)
            if 0 < months <= asset.useful_life:
                monthly_depreciation = _d(asset.original_value) * (1 - _d(asset.salvage_rate)) / asset.useful_life
                period_depreciation = monthly_depreciation
                accumulated = monthly_depreciation * min(months, asset.useful_life)
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