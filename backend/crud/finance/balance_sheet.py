"""资产负债表 (会小企01表)"""

from datetime import datetime, timedelta
from decimal import Decimal
from sqlalchemy.orm import Session
from sqlalchemy import func as sqlfunc

import models
from enums import OrderStatus, PaymentStatus, PaymentMethod
from utils import _d, Q2
from models_finance import Ledger
from lineage import reads, TIER_L1, TIER_L2

from .opening_balances import get_latest_opening_balance
from ._snapshot import LedgerSnapshot


@reads("OpeningBalance.cash_balance_l1", tier=TIER_L1, source="external")
@reads("OpeningBalance.bank_balance_l1", tier=TIER_L1, source="external")
@reads("OpeningBalance.retained_earnings_l1", tier=TIER_L1, source="external")
@reads("OpeningBalance.fixed_assets_original_l1", tier=TIER_L1, source="external")
@reads("OpeningBalance.accumulated_depreciation_l1", tier=TIER_L1, source="external")
@reads("OpeningBalance.intangible_assets_original_l1", tier=TIER_L1, source="external")
@reads("OpeningBalance.accumulated_amortization_l1", tier=TIER_L1, source="external")
@reads("OpeningBalance.accounts_payable_l1", tier=TIER_L1, source="external")
@reads("OpeningBalance.tax_payable_l1", tier=TIER_L1, source="external")
@reads("OpeningBalance.long_term_borrowings_l1", tier=TIER_L1, source="external")
@reads("OpeningBalance.paid_in_capital_l1", tier=TIER_L1, source="external")
@reads("SaleOrder.total_price_l1", tier=TIER_L1, source="external")
@reads("PurchaseOrder.total_price_l1", tier=TIER_L1, source="external")
@reads("Expense.amount_l1", tier=TIER_L1, source="external")
@reads("Payment.amount_l1", tier=TIER_L1, source="external")
@reads("Receipt.amount_l1", tier=TIER_L1, source="external")
@reads("StockMove.quantity_l1", tier=TIER_L1, source="external")
@reads("StockMove.total_cost_l2", tier=TIER_L2, source="engine")
@reads("AccountMoveLine.debit_l2", tier=TIER_L2, source="engine")
@reads("AccountMoveLine.credit_l2", tier=TIER_L2, source="engine")
@reads("BankTransaction.amount_l2", tier=TIER_L2, source="engine")
def generate_balance_sheet(db: Session, account_id: int, date: str):
    """生成资产负债表"""
    query_date = datetime.strptime(date, "%Y-%m-%d")
    query_end = query_date + timedelta(days=1) - timedelta(seconds=1)

    # ── 构造 snapshot：BS 只需要累计到截止日的数据 ──
    sn = LedgerSnapshot(db, account_id, bs_cutoff=query_end)

    opening_balance = sn.opening_balance

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
        opening_date = datetime.combine(opening_balance.date_l1, datetime.min.time())
        opening_cash = _d(opening_balance.cash_balance_l1)
        opening_bank = _d(opening_balance.bank_balance_l1)
        opening_retained_earnings = _d(opening_balance.retained_earnings_l1)
        opening_fixed_assets_original = _d(opening_balance.fixed_assets_original_l1)
        opening_accumulated_depreciation = _d(opening_balance.accumulated_depreciation_l1)
        opening_intangible_assets_original = _d(opening_balance.intangible_assets_original_l1)
        opening_accumulated_amortization = _d(opening_balance.accumulated_amortization_l1)
        opening_accounts_payable = _d(opening_balance.accounts_payable_l1)
        opening_tax_payable = _d(opening_balance.tax_payable_l1)
        opening_long_term_borrowings = _d(opening_balance.long_term_borrowings_l1)
        opening_paid_in_capital = _d(opening_balance.paid_in_capital_l1)

    # ── 流动资产 ──
    sales_received = _d(db.query(sqlfunc.sum(models.SaleOrder.total_price_l1)).filter(
        models.SaleOrder.account_id == account_id,
        models.SaleOrder.sale_date_l1 >= opening_date,
        models.SaleOrder.sale_date_l1 <= query_end,
        models.SaleOrder.status == OrderStatus.COMPLETED,
        models.SaleOrder.payment_status == PaymentStatus.PAID
    ).scalar())

    purchase_paid = _d(db.query(sqlfunc.sum(models.PurchaseOrder.total_price_l1)).filter(
        models.PurchaseOrder.account_id == account_id,
        models.PurchaseOrder.purchase_date_l1 >= opening_date,
        models.PurchaseOrder.purchase_date_l1 <= query_end,
        models.PurchaseOrder.status == OrderStatus.COMPLETED,
        models.PurchaseOrder.payment_status == PaymentStatus.PAID,
        models.PurchaseOrder.payment_method == PaymentMethod.COMPANY
    ).scalar())

    expense_paid = _d(db.query(sqlfunc.sum(models.Expense.amount_l1)).filter(
        models.Expense.account_id == account_id,
        models.Expense.expense_date_l1 >= opening_date,
        models.Expense.expense_date_l1 <= query_end,
        models.Expense.payment_method == PaymentMethod.COMPANY
    ).scalar())

    # 货币资金计算：单一真相源-从总账取数（通过 snapshot）
    cash_from_ledger = sn.bal("1001")
    bank_from_ledger = sn.bal("1002")

    if sn._ledger and (cash_from_ledger != 0 or bank_from_ledger != 0):
        ending_cash = cash_from_ledger
        ending_bank = bank_from_ledger
    else:
        # 总账无数据时从 BankTransaction（L2 真相源）计算银行余额
        has_bank_accounts = db.query(models.BankAccount).filter(
            models.BankAccount.account_id == account_id
        ).first() is not None
        if has_bank_accounts:
            from sqlalchemy import case as sqlcase
            tx_net = db.query(
                sqlfunc.sum(
                    sqlcase(
                        (models.BankTransaction.transaction_type == 'inflow', models.BankTransaction.amount_l2),
                        else_=-models.BankTransaction.amount_l2
                    )
                )
            ).filter(
                models.BankTransaction.account_id == account_id
            ).scalar()
            bank_balance = opening_bank + _d(tx_net) if tx_net else opening_bank
            ending_cash = Decimal('0')
            ending_bank = bank_balance
        else:
            total_payments = _d(db.query(sqlfunc.sum(models.Payment.amount_l1)).filter(
                models.Payment.account_id == account_id,
                models.Payment.payment_date_l1 >= opening_date,
                models.Payment.payment_date_l1 <= query_end,
            ).scalar())
            total_receipts = _d(db.query(sqlfunc.sum(models.Receipt.amount_l1)).filter(
                models.Receipt.account_id == account_id,
                models.Receipt.receipt_date_l1 >= opening_date,
                models.Receipt.receipt_date_l1 <= query_end,
            ).scalar())
            ending_cash = opening_cash - total_payments + total_receipts
            ending_bank = Decimal('0')

    # 应收账款 = 总账 1122
    accounts_receivable = sn.bal("1122").quantize(Q2)
    opening_accounts_receivable = _d(opening_balance.accounts_receivable_l1) if opening_balance else Decimal('0')
    if accounts_receivable == 0 and opening_accounts_receivable > 0:
        accounts_receivable = opening_accounts_receivable

    # BR-7: 库存真相源是 StockMove 流水
    as_of_moves = sn.stock_moves()
    inv_agg = {}
    for m in as_of_moves:
        pid = m.product_id
        if pid not in inv_agg:
            inv_agg[pid] = {"qty": Decimal("0"), "value": Decimal("0")}
        qty = Decimal(str(m.quantity_l1))
        cost = _d(m.total_cost_l2)
        value_delta = abs(cost) * (Decimal("1") if qty > 0 else Decimal("-1"))
        inv_agg[pid]["qty"] += qty
        inv_agg[pid]["value"] += value_delta
    inventory_value = Decimal('0')
    for pid, agg in inv_agg.items():
        if agg["qty"] > 0:
            inventory_value += agg["value"]
    opening_inventory_value = _d(opening_balance.inventory_value_l1) if opening_balance else Decimal('0')
    if inventory_value == 0 and opening_inventory_value > 0:
        inventory_value = opening_inventory_value

    prepayments = sn.bal("1123").quantize(Q2)

    # ── 非流动资产 ──
    fixed_assets_original = sn.bal("1601").quantize(Q2)
    accumulated_depreciation = sn.crd("1602").quantize(Q2)
    fixed_assets_net = fixed_assets_original - accumulated_depreciation

    intangible_assets_original = sn.bal("1701").quantize(Q2)
    accumulated_amortization = sn.crd("1702").quantize(Q2)
    intangible_assets_net = intangible_assets_original - accumulated_amortization

    total_non_current_assets = fixed_assets_net + intangible_assets_net

    # ── 流动负债 ──
    accounts_payable = sn.crd("2202").quantize(Q2)
    opening_accounts_payable = _d(opening_balance.accounts_payable_l1) if opening_balance else Decimal('0')
    if accounts_payable == 0 and opening_accounts_payable > 0:
        accounts_payable = opening_accounts_payable

    salaries_payable = sn.crd("2211").quantize(Q2)
    other_payable = sn.crd("2241").quantize(Q2)

    # ── 应交税费 ──
    vat_credit = (sn.crd("222101") + sn.crd("222107") + sn.crd("222103")).quantize(Q2)
    vat_debit_balance = (sn.bal("222102") + sn.bal("222106")).quantize(Q2)
    vat_net = vat_credit - vat_debit_balance
    if vat_net > 0:
        vat_payable = vat_net
        prepaid_tax = Decimal("0")
    else:
        vat_payable = Decimal("0")
        prepaid_tax = (-vat_net).quantize(Q2)

    surcharge_liability = (sn.crd("222104") + sn.crd("222110") + sn.crd("222111")
                           + sn.crd("222112") + sn.crd("222113") + sn.crd("222114")
                           + sn.crd("222115") + sn.crd("222116") + sn.crd("222117")
                           + sn.crd("222118") + sn.crd("222119") + sn.crd("222120")).quantize(Q2)
    income_tax_liability = sn.crd("222105").quantize(Q2)
    personal_income_tax_liability = sn.crd("222108").quantize(Q2)
    tax_payable = (vat_payable + surcharge_liability + income_tax_liability + personal_income_tax_liability).quantize(Q2)

    # ── 非流动负债 ──
    long_term_borrowings = sn.crd("2501").quantize(Q2)

    # ── 利润构成（用于报表附注展示）──
    op_open = opening_date
    op_end = query_end
    rev_d, rev_c = sn.pnl_dc("6001", op_open, op_end)
    other_rev_d, other_rev_c = sn.pnl_dc("6051", op_open, op_end)
    period_revenue = (rev_c - rev_d + other_rev_c - other_rev_d).quantize(Q2)
    cogs_d, cogs_c = sn.pnl_dc("6401", op_open, op_end)
    period_cogs = (cogs_d - cogs_c).quantize(Q2)
    _e1_d, _e1_c = sn.pnl_dc("6601", op_open, op_end)
    _e2_d, _e2_c = sn.pnl_dc("6602", op_open, op_end)
    _e3_d, _e3_c = sn.pnl_dc("6603", op_open, op_end)
    period_expenses = ((_e1_d - _e1_c) + (_e2_d - _e2_c) + (_e3_d - _e3_c)).quantize(Q2)
    dep_d, dep_c = sn.pnl_dc("1602", op_open, op_end)
    depreciation_expense = dep_c.quantize(Q2)
    amortization_expense = Decimal("0")
    surcharge_expense = Decimal("0")
    for sc in ["6403", "640301", "640302", "640303", "640304", "640305",
               "640306", "640307", "640308", "640309", "640310", "640311"]:
        sd, sc_v = sn.pnl_dc(sc, op_open, op_end)
        surcharge_expense += sd - sc_v
    surcharge_expense = surcharge_expense.quantize(Q2)
    it_d, it_c = sn.pnl_dc("6801", op_open, op_end)
    income_tax_expense = (it_d - it_c).quantize(Q2)
    noi_d, noi_c = sn.pnl_dc("6301", op_open, op_end)
    ado_d, ado_c = sn.pnl_dc("6111", op_open, op_end)
    non_operating_income = (noi_c + ado_c).quantize(Q2)
    noe_d, noe_c = sn.pnl_dc("6701", op_open, op_end)
    adl_d, adl_c = sn.pnl_dc("6711", op_open, op_end)
    non_operating_expense = (noe_d + adl_d).quantize(Q2)

    period_profit = (period_revenue - period_cogs - period_expenses
                     - surcharge_expense - income_tax_expense
                     + non_operating_income - non_operating_expense)

    paid_in_capital = sn.crd("3001").quantize(Q2)
    current_year_profit = sn.crd("4103").quantize(Q2)
    retained_earnings_prev = sn.crd("4104").quantize(Q2)
    retained_earnings = (opening_retained_earnings
                         + current_year_profit
                         + retained_earnings_prev).quantize(Q2)
    total_equity = (paid_in_capital + retained_earnings + period_profit).quantize(Q2)

    # ── 汇总 ──
    total_current_assets = (ending_cash + ending_bank + accounts_receivable
                            + prepayments + inventory_value + prepaid_tax
                            + sn.bal("1901").quantize(Q2))
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
        "prepayments": prepayments.quantize(Q2),
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
        "vat_payable": vat_payable.quantize(Q2),
        "surcharge_liability": surcharge_liability.quantize(Q2),
        "income_tax_liability": income_tax_liability.quantize(Q2),
        "personal_income_tax_liability": personal_income_tax_liability.quantize(Q2),
        "total_current_liabilities": total_current_liabilities.quantize(Q2),
        "salaries_payable": salaries_payable.quantize(Q2),
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
