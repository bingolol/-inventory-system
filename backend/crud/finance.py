"""财务：期初余额 + 资产负债表 + 利润表 + 现金流量（含事务包裹和金额精度）"""

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

    total_assets = _d(data.cash_balance) + _d(data.bank_balance) + _d(data.accounts_receivable) + _d(data.inventory_value)
    total_liabilities = _d(data.accounts_payable) + _d(data.tax_payable)
    total_equity = _d(data.retained_earnings)
    if abs(total_assets - (total_liabilities + total_equity)) > Decimal('0.01'):
        raise ValueError(f"资产负债表不平衡: 资产={total_assets}, 负债+权益={total_liabilities + total_equity}")

    opening_balance = models.OpeningBalance(
        account_id=account_id,
        date=datetime.strptime(data.date, "%Y-%m-%d").date(),
        cash_balance=data.cash_balance,
        bank_balance=data.bank_balance,
        accounts_receivable=data.accounts_receivable,
        inventory_value=data.inventory_value,
        accounts_payable=data.accounts_payable,
        tax_payable=data.tax_payable,
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

    total_assets = _d(opening_balance.cash_balance) + _d(opening_balance.bank_balance) + _d(opening_balance.accounts_receivable) + _d(opening_balance.inventory_value)
    total_liabilities = _d(opening_balance.accounts_payable) + _d(opening_balance.tax_payable)
    total_equity = _d(opening_balance.retained_earnings)
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


# ── 资产负债表 ──

def generate_balance_sheet(db: Session, account_id: int, date: str):
    query_date = datetime.strptime(date, "%Y-%m-%d").date()
    opening_balance = get_latest_opening_balance(db, account_id, date)

    if not opening_balance:
        opening_date = datetime(2000, 1, 1).date()
        opening_cash = Decimal('0')
        opening_bank = Decimal('0')
        opening_retained_earnings = Decimal('0')
    else:
        opening_date = opening_balance.date
        opening_cash = _d(opening_balance.cash_balance)
        opening_bank = _d(opening_balance.bank_balance)
        opening_retained_earnings = _d(opening_balance.retained_earnings)

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

    total_assets = ending_cash + ending_bank + accounts_receivable + inventory_value
    total_liabilities = accounts_payable + tax_payable

    cogs = _d(db.query(sqlfunc.sum(models.SaleItem.quantity * models.SaleItem.unit_price)).filter(
        models.SaleItem.order_id.in_(
            db.query(models.SaleOrder.id).filter(
                models.SaleOrder.account_id == account_id,
                models.SaleOrder.sale_date >= opening_date,
                models.SaleOrder.sale_date <= query_date,
                models.SaleOrder.status == OrderStatus.COMPLETED
            )
        )
    ).scalar())

    period_revenue = _d(db.query(sqlfunc.sum(models.SaleOrder.total_price)).filter(
        models.SaleOrder.account_id == account_id,
        models.SaleOrder.sale_date >= opening_date,
        models.SaleOrder.sale_date <= query_date,
        models.SaleOrder.status == OrderStatus.COMPLETED
    ).scalar())

    period_expenses = _d(db.query(sqlfunc.sum(models.Expense.amount)).filter(
        models.Expense.account_id == account_id,
        models.Expense.expense_date >= opening_date,
        models.Expense.expense_date <= query_date
    ).scalar())

    period_profit = period_revenue - cogs - period_expenses
    retained_earnings = opening_retained_earnings + period_profit
    total_equity = retained_earnings

    if total_assets != total_liabilities + total_equity:
        retained_earnings = total_assets - total_liabilities
        total_equity = retained_earnings

    return {
        "date": date,
        "assets": {
            "current_assets": {
                "cash": ending_cash.quantize(Q2),
                "bank": ending_bank.quantize(Q2),
                "accounts_receivable": accounts_receivable.quantize(Q2),
                "inventory": inventory_value.quantize(Q2)
            },
            "total_assets": total_assets.quantize(Q2)
        },
        "liabilities": {
            "current_liabilities": {
                "accounts_payable": accounts_payable.quantize(Q2),
                "tax_payable": tax_payable.quantize(Q2)
            },
            "total_liabilities": total_liabilities.quantize(Q2)
        },
        "equity": {
            "retained_earnings": retained_earnings.quantize(Q2),
            "total_equity": total_equity.quantize(Q2)
        }
    }


# ── 利润表（经营口径：实际经营说话）──
# 与企业所得税（税务口径）的关键区别：
# - 收入 = 销售单收入（而非销项发票）
# - 成本 = 销售成本 + 采购成本（而非进项发票）
# - 费用 = 全部费用（而非仅有票费用）

def generate_income_statement(db: Session, account_id: int, start_date: str, end_date: str):
    """损益表：收入=所有销售单，成本=所有采购单
    """
    start_dt = datetime.strptime(start_date, "%Y-%m-%d")
    end_dt = datetime.strptime(end_date, "%Y-%m-%d")

    # ── 收入：所有已完成销售单 ──
    sale_revenue = _d(db.query(sqlfunc.sum(models.SaleOrder.total_price)).filter(
        models.SaleOrder.account_id == account_id,
        models.SaleOrder.sale_date >= start_dt,
        models.SaleOrder.sale_date <= end_dt,
        models.SaleOrder.status == OrderStatus.COMPLETED
    ).scalar())

    total_revenue = sale_revenue

    # ── 销售成本（商品采购价）──
    sale_cogs = Decimal('0')
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
            sale_cogs += Decimal(str(item.quantity)) * purchase_price

    total_cogs = sale_cogs

    # ── 经营费用（全部，含无票费用）──
    operating_expenses = _d(db.query(sqlfunc.sum(models.Expense.amount)).filter(
        models.Expense.account_id == account_id,
        models.Expense.expense_date >= start_dt,
        models.Expense.expense_date <= end_dt
    ).scalar())

    gross_profit = total_revenue - total_cogs
    operating_profit = gross_profit - operating_expenses
    net_profit = operating_profit

    return {
        "period": f"{start_date} 至 {end_date}",
        "revenue": total_revenue.quantize(Q2),
        "sale_revenue": sale_revenue.quantize(Q2),
        "cost_of_goods_sold": total_cogs.quantize(Q2),
        "sale_cogs": sale_cogs.quantize(Q2),
        "gross_profit": gross_profit.quantize(Q2),
        "operating_expenses": operating_expenses.quantize(Q2),
        "operating_profit": operating_profit.quantize(Q2),
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