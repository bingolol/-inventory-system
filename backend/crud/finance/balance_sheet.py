"""资产负债表 (会小企01表)"""

from datetime import datetime, timedelta
from decimal import Decimal
from sqlalchemy.orm import Session
from sqlalchemy import func as sqlfunc

import models
from enums import OrderStatus, PaymentStatus, PaymentMethod
from utils import _d, Q2
from models_finance import Ledger

from .opening_balances import get_latest_opening_balance
from ._ledger_helpers import _l, _lp, _bal, _crd, _stock_moves_as_of

def generate_balance_sheet(db: Session, account_id: int, date: str):
    """生成资产负债表"""
    query_date = datetime.strptime(date, "%Y-%m-%d")
    query_end = query_date + timedelta(days=1) - timedelta(seconds=1)
    opening_balance = get_latest_opening_balance(db, account_id, date)

    if not opening_balance:
        opening_date = datetime(2000, 1, 1)
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
        opening_date = datetime.combine(opening_balance.date, datetime.min.time())
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
        models.SaleOrder.sale_date <= query_end,
        models.SaleOrder.status == OrderStatus.COMPLETED,
        models.SaleOrder.payment_status == PaymentStatus.PAID
    ).scalar())

    purchase_paid = _d(db.query(sqlfunc.sum(models.PurchaseOrder.total_price)).filter(
        models.PurchaseOrder.account_id == account_id,
        models.PurchaseOrder.purchase_date >= opening_date,
        models.PurchaseOrder.purchase_date <= query_end,
        models.PurchaseOrder.status == OrderStatus.COMPLETED,
        models.PurchaseOrder.payment_status == PaymentStatus.PAID,
        models.PurchaseOrder.payment_method == PaymentMethod.COMPANY
    ).scalar())

    expense_paid = _d(db.query(sqlfunc.sum(models.Expense.amount)).filter(
        models.Expense.account_id == account_id,
        models.Expense.expense_date >= opening_date,
        models.Expense.expense_date <= query_end,
        models.Expense.payment_method == PaymentMethod.COMPANY
    ).scalar())

    # 货币资金计算：单一真相源-从总账取数
    acct = db.query(models.Account).filter(models.Account.id == account_id).first()
    ledger = acct and db.query(Ledger).filter(Ledger.code == acct.code).first()

    L  = lambda code, cutoff=None: _l(db, ledger, code, cutoff or query_end)
    B  = lambda code, cutoff=None: _bal(db, ledger, code, cutoff or query_end)
    C  = lambda code, cutoff=None: _crd(db, ledger, code, cutoff or query_end)
    # 旧名兼容
    _balance = B
    _credit_balance = C

    cash_from_ledger = _balance("1001")
    bank_from_ledger = _balance("1002")

    if ledger and (cash_from_ledger != 0 or bank_from_ledger != 0):
        ending_cash = cash_from_ledger
        ending_bank = bank_from_ledger
    else:
        # 总账无数据时回退到银行账户表
        has_bank_accounts = db.query(models.BankAccount).filter(
            models.BankAccount.account_id == account_id
        ).first() is not None
        if has_bank_accounts:
            bank_balance = _d(db.query(sqlfunc.sum(models.BankAccount.balance)).filter(
                models.BankAccount.account_id == account_id
            ).scalar())
            ending_cash = Decimal('0')
            ending_bank = bank_balance
        else:
            total_payments = _d(db.query(sqlfunc.sum(models.Payment.amount)).filter(
                models.Payment.account_id == account_id,
                models.Payment.payment_date >= opening_date,
                models.Payment.payment_date <= query_end,
            ).scalar())
            total_receipts = _d(db.query(sqlfunc.sum(models.Receipt.amount)).filter(
                models.Receipt.account_id == account_id,
                models.Receipt.receipt_date >= opening_date,
                models.Receipt.receipt_date <= query_end,
            ).scalar())
            ending_cash = opening_cash - total_payments + total_receipts
            ending_bank = Decimal('0')

    # 应收账款 = 总账 1122
    accounts_receivable = _balance("1122").quantize(Q2)

    # BR-7: 库存真相源是 StockMove 流水，Inventory 表仅为缓存。
    # 按 query_end 截止日期过滤 StockMove（关联业务单据日期），聚合期末存货数量与价值。
    as_of_moves = _stock_moves_as_of(db, account_id, query_end)
    inv_agg = {}
    for m in as_of_moves:
        pid = m.product_id
        if pid not in inv_agg:
            inv_agg[pid] = {"qty": Decimal("0"), "value": Decimal("0")}
        qty = Decimal(str(m.quantity))
        inv_agg[pid]["qty"] += qty
        # StockMove.total_cost 存的是绝对值，方向由 quantity 正负表示
        if qty > 0:
            inv_agg[pid]["value"] += _d(m.total_cost)
        else:
            inv_agg[pid]["value"] -= _d(m.total_cost)
    inventory_value = Decimal('0')
    for pid, agg in inv_agg.items():
        if agg["qty"] > 0:
            inventory_value += agg["value"]

    # ── 非流动资产 ── 从总账取
    fixed_assets_original = _balance("1601").quantize(Q2)
    accumulated_depreciation = _credit_balance("1602").quantize(Q2)
    fixed_assets_net = fixed_assets_original - accumulated_depreciation

    # 无形资产
    intangible_assets_original = _balance("1701").quantize(Q2)
    accumulated_amortization = _credit_balance("1702").quantize(Q2)
    intangible_assets_net = intangible_assets_original - accumulated_amortization
    
    total_non_current_assets = fixed_assets_net + intangible_assets_net

    # ── 流动负债 ── 从总账
    accounts_payable = _credit_balance("2202").quantize(Q2)
    salaries_payable = _credit_balance("2211").quantize(Q2)  # 应付职工薪酬
    # 其他应付款 2241 — 个人垫付余额（含老板/员工替公司垫付形成的负债）
    other_payable = _credit_balance("2241").quantize(Q2)

    # ── 应交税费 — 纯总账取数（月结后自动体现）──
    # 一般纳税人：222101→222106→222107 月结后余额在 222107
    # 小规模纳税人：直接用 222103，不走转出未交增值税机制，余额即应交税金
    vat_payable = (_credit_balance("222107") + _credit_balance("222103")).quantize(Q2)
    surcharge_liability = _credit_balance("222104").quantize(Q2)
    income_tax_liability = _credit_balance("222105").quantize(Q2)
    tax_payable = (vat_payable + surcharge_liability + income_tax_liability).quantize(Q2)
    # 留抵 = 应交增值税借方余额（一般纳税人：222101+222102+222106，转出后剩余为留抵）
    vat_debit = (_balance("222101") + _balance("222102") + _balance("222106"))
    prepaid_tax = max(vat_debit, Decimal("0")).quantize(Q2)

    # ── 非流动负债 ──
    long_term_borrowings = opening_long_term_borrowings

    # ── 利润构成（全从总账取，月结后税金自动体现）──
    period_revenue = (_credit_balance("6001") + _credit_balance("6051")).quantize(Q2)
    period_cogs = _balance("6401").quantize(Q2)
    period_expenses = (_balance("6601") + _balance("6602") + _balance("6603")).quantize(Q2)
    dep_d, dep_c = _lp(db, ledger, "1602", opening_date, query_end)
    depreciation_expense = dep_c.quantize(Q2)  # 已包含在6601中，此处仅用于报表展示
    amortization_expense = Decimal("0")  # 摊销已包含在6601中，保留字段兼容前端
    surcharge_expense = _balance("6403").quantize(Q2)
    income_tax_expense = _balance("6801").quantize(Q2)
    # 营业外收支（6301/6701）+ 资产处置损益（6111/6711）
    non_operating_income = (_credit_balance("6301") + _credit_balance("6111")).quantize(Q2)
    non_operating_expense = (_balance("6701") + _balance("6711")).quantize(Q2)

    period_profit = (period_revenue - period_cogs - period_expenses
                     - surcharge_expense - income_tax_expense
                     + non_operating_income - non_operating_expense)

    paid_in_capital = _credit_balance("3001").quantize(Q2)
    retained_earnings = opening_retained_earnings + period_profit
    total_equity = paid_in_capital + retained_earnings

    # ── 汇总 ──
    total_current_assets = (ending_cash + ending_bank + accounts_receivable
                            + inventory_value + prepaid_tax
                            + _balance("1901").quantize(Q2))  # 待处理财产损溢
    total_assets = total_current_assets + total_non_current_assets
    total_non_current_liabilities = long_term_borrowings
    total_current_liabilities = accounts_payable + salaries_payable + tax_payable + other_payable
    total_liabilities = total_current_liabilities + total_non_current_liabilities

    diff = total_assets - (total_liabilities + total_equity)
    balanced = abs(diff) <= Decimal('0.01')

    return {
        "balanced": balanced,
        "diff": float(diff.quantize(Q2)),
        "date": date,
        # 资产
        "monetary_funds": (ending_cash + ending_bank).quantize(Q2),
        "accounts_receivable": accounts_receivable.quantize(Q2),
        "prepayments": prepaid_tax.quantize(Q2),
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
        "other_payable": other_payable.quantize(Q2),
        "tax_payable": tax_payable.quantize(Q2),
        "total_current_liabilities": total_current_liabilities.quantize(Q2),
        "long_term_borrowings": long_term_borrowings.quantize(Q2),
        "total_non_current_liabilities": total_non_current_liabilities.quantize(Q2),
        "total_liabilities": total_liabilities.quantize(Q2),
        "paid_in_capital": paid_in_capital.quantize(Q2),
        "retained_earnings": retained_earnings.quantize(Q2),
        "total_equity": total_equity.quantize(Q2),
        "total_liabilities_and_equity": (total_liabilities + total_equity).quantize(Q2),
        # 利润构成（用于调试）
        "period_revenue": period_revenue.quantize(Q2),
        "period_cogs": period_cogs.quantize(Q2),
        "period_expenses": period_expenses.quantize(Q2),
        "depreciation_expense": depreciation_expense.quantize(Q2),
        "amortization_expense": amortization_expense.quantize(Q2),
        "non_operating_income": non_operating_income.quantize(Q2),
        "non_operating_expense": non_operating_expense.quantize(Q2),
        "period_profit": period_profit.quantize(Q2),
    }
