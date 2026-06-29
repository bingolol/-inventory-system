"""财务：期初余额 + 资产负债表 + 利润表 + 现金流量 + 固定资产 + 无形资产

写操作已迁移至 commands 层（CreateOpeningBalance/UpdateOpeningBalance/CreateCashFlowTransaction 等）。
本模块保留查询、报表生成和少量仍被 router 直接调用的写操作。
"""

import logging
from datetime import datetime, timedelta
from decimal import Decimal
from sqlalchemy.orm import Session
from sqlalchemy import func as sqlfunc
import models, schemas

from enums import (OrderStatus, PaymentStatus, PaymentMethod, InvoiceDirection,
                   InvoiceType, FlowCategory, CertificationStatus, TaxpayerType)
from .base import _log
from utils import _d, Q2
from errors import BusinessError, ErrorCode
from accounting_engine import AccountingEngine
from models_finance import Ledger, LedgerAccount, LedgerAccountBalance, AccountMove, AccountMoveLine

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


def _stock_moves_as_of(db: Session, account_id: int, query_end) -> list:
    """获取截至 query_end 的 StockMove。

    StockMove.move_date 是业务日期真相源（BR-21 强制采购/销售单必须传业务日期，
    InventoryEngine 写入 StockMove 时也会回填业务日期）。
    本函数不再支持 move_date 为 NULL 的兼容分支，所有 StockMove 必须有 move_date。
    """
    moves = db.query(models.StockMove).filter(
        models.StockMove.account_id == account_id,
        models.StockMove.move_date.isnot(None),
    ).all()

    result = []
    for m in moves:
        biz_date = m.move_date
        if biz_date is None:
            continue
        if hasattr(biz_date, "hour"):
            if biz_date <= query_end:
                result.append(m)
        else:
            biz_dt = datetime.combine(biz_date, datetime.min.time())
            if biz_dt <= query_end:
                result.append(m)
    return result



# ── 单一真相源：BS/IS共享的总账查询 ──

def _l(db, ledger, code, cutoff):
    """累计 (debit, credit) 截止cutoff"""
    if not ledger: return Decimal("0"), Decimal("0")
    d = _d(db.query(sqlfunc.coalesce(sqlfunc.sum(AccountMoveLine.debit),0)).join(
        LedgerAccount,AccountMoveLine.ledger_account_id==LedgerAccount.id
    ).join(AccountMove,AccountMoveLine.move_id==AccountMove.id).filter(
        LedgerAccount.ledger_id==ledger.id,LedgerAccount.code==code,
        AccountMove.date<=cutoff).scalar())
    c = _d(db.query(sqlfunc.coalesce(sqlfunc.sum(AccountMoveLine.credit),0)).join(
        LedgerAccount,AccountMoveLine.ledger_account_id==LedgerAccount.id
    ).join(AccountMove,AccountMoveLine.move_id==AccountMove.id).filter(
        LedgerAccount.ledger_id==ledger.id,LedgerAccount.code==code,
        AccountMove.date<=cutoff).scalar())
    return d,c

def _lp(db, ledger, code, start, end):
    """期间 (debit, credit) [start,end]"""
    if not ledger: return Decimal("0"),Decimal("0")
    d = _d(db.query(sqlfunc.coalesce(sqlfunc.sum(AccountMoveLine.debit),0)).join(
        LedgerAccount,AccountMoveLine.ledger_account_id==LedgerAccount.id
    ).join(AccountMove,AccountMoveLine.move_id==AccountMove.id).filter(
        LedgerAccount.ledger_id==ledger.id,LedgerAccount.code==code,
        AccountMove.date>=start,AccountMove.date<=end).scalar())
    c = _d(db.query(sqlfunc.coalesce(sqlfunc.sum(AccountMoveLine.credit),0)).join(
        LedgerAccount,AccountMoveLine.ledger_account_id==LedgerAccount.id
    ).join(AccountMove,AccountMoveLine.move_id==AccountMove.id).filter(
        LedgerAccount.ledger_id==ledger.id,LedgerAccount.code==code,
        AccountMove.date>=start,AccountMove.date<=end).scalar())
    return d,c

def _bal(db, ledger, code, cutoff):
    """asset/expense余额: 借-贷"""
    d,c=_l(db,ledger,code,cutoff); return d-c

def _crd(db, ledger, code, cutoff):
    """liability/equity/income余额: 贷-借"""
    d,c=_l(db,ledger,code,cutoff); return c-d

def _pdr(db, ledger, code, start, end):
    """期内借方"""
    d,_=_lp(db,ledger,code,start,end); return d

# ── 资产负债表 (会小企01表) ──

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
    total_current_liabilities = accounts_payable + salaries_payable + tax_payable
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


# ── 利润表 (会小企02表) ──

def generate_income_statement(db: Session, account_id: int, start_date: str, end_date: str):
    """生成利润表"""
    start_dt = datetime.strptime(start_date, "%Y-%m-%d")
    end_dt = datetime.strptime(end_date, "%Y-%m-%d") + timedelta(days=1) - timedelta(seconds=1)

    # ── 利润表全从总账取数 ──
    account = db.query(models.Account).filter(models.Account.id == account_id).first()
    ledger_is = account and db.query(Ledger).filter(Ledger.code == account.code).first()

    # 营业收入 = 主营业务收入(6001) + 其他业务收入(6051)
    rev_d, rev_c = _lp(db, ledger_is, "6001", start_dt, end_dt)
    other_rev_d, other_rev_c = _lp(db, ledger_is, "6051", start_dt, end_dt)
    revenue = (rev_c - rev_d + other_rev_c - other_rev_d).quantize(Q2)
    cogs_d, cogs_c = _lp(db, ledger_is, "6401", start_dt, end_dt)
    cost_of_goods_sold = (cogs_d - cogs_c).quantize(Q2)
    administrative_expenses = _pdr(db, ledger_is, "6601", start_dt, end_dt).quantize(Q2)
    selling_expenses = _pdr(db, ledger_is, "6602", start_dt, end_dt).quantize(Q2)
    financial_expenses = _pdr(db, ledger_is, "6603", start_dt, end_dt).quantize(Q2)
    depr_d, depr_c = _lp(db, ledger_is, "1602", start_dt, end_dt)
    depreciation_expense = depr_c.quantize(Q2)
    total_operating_expenses = (selling_expenses + administrative_expenses + financial_expenses).quantize(Q2)

    # ── 营业毛利 ──
    gross_profit = revenue - cost_of_goods_sold

    # ── 营业利润 ──
    operating_profit = gross_profit - total_operating_expenses

    # ── 税金及附加 + 所得税 — 纯总账取数（月结后自动体现）──
    sur_d, sur_c = _lp(db, ledger_is, "6403", start_dt, end_dt)
    tax_surcharges = (sur_d - sur_c).quantize(Q2)
    total_operating_expenses = (total_operating_expenses + tax_surcharges).quantize(Q2)
    operating_profit = gross_profit - total_operating_expenses

    # ── 营业外收支 ──
    # 营业外收入 = 税收减免(6301) + 资产处置收益(6111)
    noi_d, noi_c = _lp(db, ledger_is, "6301", start_dt, end_dt)
    ado_d, ado_c = _lp(db, ledger_is, "6111", start_dt, end_dt)
    non_operating_income = (noi_c + ado_c).quantize(Q2)
    # 营业外支出 = 营业外支出(6701) + 资产处置损失(6711)
    noe_d, noe_c = _lp(db, ledger_is, "6701", start_dt, end_dt)
    adl_d, adl_c = _lp(db, ledger_is, "6711", start_dt, end_dt)
    non_operating_expense = (noe_d + adl_d).quantize(Q2)

    # ── 利润总额 ──
    gross_profit_total = operating_profit + non_operating_income - non_operating_expense

    # ── 所得税 = 期内 6801 净发生额 ──
    it_d, it_c = _lp(db, ledger_is, "6801", start_dt, end_dt)
    income_tax_expense = (it_d - it_c).quantize(Q2)

    # ── 净利润 ──
    net_profit = gross_profit_total - income_tax_expense

    # ── 公式交叉校验 ──
    # 校验1：营业毛利 = 营业收入 - 营业成本
    expected_gross_profit = revenue - cost_of_goods_sold
    if abs(gross_profit - expected_gross_profit) > Decimal('0.01'):
        raise BusinessError(
            code=ErrorCode.INCOME_STATEMENT_INVALID,
            message=f"利润表公式错误：营业毛利 {gross_profit} ≠ 营业收入 {revenue} - 营业成本 {cost_of_goods_sold}",
            data={"gross_profit": float(gross_profit), "revenue": float(revenue), "cost_of_goods_sold": float(cost_of_goods_sold)}
        )

    # 校验2：营业利润 = 营业毛利 - 营业费用
    expected_operating_profit = gross_profit - total_operating_expenses
    if abs(operating_profit - expected_operating_profit) > Decimal('0.01'):
        raise BusinessError(
            code=ErrorCode.INCOME_STATEMENT_INVALID,
            message=f"利润表公式错误：营业利润 {operating_profit} ≠ 营业毛利 {gross_profit} - 营业费用 {total_operating_expenses}",
            data={"operating_profit": float(operating_profit), "gross_profit": float(gross_profit), "total_operating_expenses": float(total_operating_expenses)}
        )

    # 校验3：利润总额 = 营业利润 + 营业外收入 - 营业外支出
    expected_gross_profit_total = operating_profit + non_operating_income - non_operating_expense
    if abs(gross_profit_total - expected_gross_profit_total) > Decimal('0.01'):
        raise BusinessError(
            code=ErrorCode.INCOME_STATEMENT_INVALID,
            message=f"利润表公式错误：利润总额 {gross_profit_total} ≠ 营业利润 {operating_profit} + 营业外收入 {non_operating_income} - 营业外支出 {non_operating_expense}",
            data={"gross_profit_total": float(gross_profit_total), "operating_profit": float(operating_profit), "non_operating_income": float(non_operating_income), "non_operating_expense": float(non_operating_expense)}
        )

    # 校验4：净利润 = 利润总额 - 所得税费用
    expected_net_profit = gross_profit_total - income_tax_expense
    if abs(net_profit - expected_net_profit) > Decimal('0.01'):
        raise BusinessError(
            code=ErrorCode.INCOME_STATEMENT_INVALID,
            message=f"利润表公式错误：净利润 {net_profit} ≠ 利润总额 {gross_profit_total} - 所得税费用 {income_tax_expense}",
            data={"net_profit": float(net_profit), "gross_profit_total": float(gross_profit_total), "income_tax_expense": float(income_tax_expense)}
        )

    return {
        "period": f"{start_date} 至 {end_date}",
        "revenue": revenue.quantize(Q2),
        "cost_of_goods_sold": cost_of_goods_sold.quantize(Q2),
        "gross_profit": gross_profit.quantize(Q2),
        "selling_expenses": selling_expenses.quantize(Q2),
        "administrative_expenses": administrative_expenses.quantize(Q2),
        "financial_expenses": financial_expenses.quantize(Q2),
        "tax_surcharges": tax_surcharges.quantize(Q2),
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
        start_dt = datetime.strptime(start_date, "%Y-%m-%d")
        q = q.filter(models.CashFlowTransaction.transaction_date >= start_dt)
    if end_date:
        end_dt = datetime.strptime(end_date, "%Y-%m-%d") + timedelta(days=1) - timedelta(seconds=1)
        q = q.filter(models.CashFlowTransaction.transaction_date <= end_dt)
    if flow_category:
        q = q.filter(models.CashFlowTransaction.flow_category == flow_category)
    total = q.count()
    items = q.order_by(models.CashFlowTransaction.transaction_date.desc()).offset(skip).limit(limit).all()
    return total, items


def generate_cash_flow_statement(db: Session, account_id: int, start_date: str, end_date: str):
    start_dt = datetime.strptime(start_date, "%Y-%m-%d")
    end_dt = datetime.strptime(end_date, "%Y-%m-%d") + timedelta(days=1) - timedelta(seconds=1)

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

    # ── 余额校验 ──
    # 校验：期末余额 = 期初余额 + 净现金流量
    expected_ending_balance = beginning_cash_balance + net_cash_flow
    if abs(ending_cash_balance - expected_ending_balance) > Decimal('0.01'):
        raise BusinessError(
            code=ErrorCode.CASH_FLOW_STATEMENT_INVALID,
            message=f"现金流量表公式错误：期末余额 {ending_cash_balance} ≠ 期初余额 {beginning_cash_balance} + 净现金流量 {net_cash_flow}",
            data={"ending_cash_balance": float(ending_cash_balance), "beginning_cash_balance": float(beginning_cash_balance), "net_cash_flow": float(net_cash_flow)}
        )

    # 校验：净现金流量 = 经营活动净额 + 投资活动净额 + 筹资活动净额
    expected_net_cash_flow = net_operating + net_investing + net_financing
    if abs(net_cash_flow - expected_net_cash_flow) > Decimal('0.01'):
        raise BusinessError(
            code=ErrorCode.CASH_FLOW_STATEMENT_INVALID,
            message=f"现金流量表公式错误：净现金流量 {net_cash_flow} ≠ 经营活动净额 {net_operating} + 投资活动净额 {net_investing} + 筹资活动净额 {net_financing}",
            data={"net_cash_flow": float(net_cash_flow), "net_operating": float(net_operating), "net_investing": float(net_investing), "net_financing": float(net_financing)}
        )

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
    """创建固定资产（含会计凭证：借:1601 贷:2202）"""
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
    from finance_integration import post_journal
    post_journal(db, account_id, "fixed_asset_purchase", {
        "asset_id": asset.id,
        "original_value": data.original_value,
        "date": data.start_date,
        "source_model": "fixed_asset",
        "source_id": asset.id,
    })
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
    from models_finance import Ledger, LedgerAccount, AccountMove, AccountMoveLine
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
    from crud.finance import generate_vat_declaration
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


# ── 付款 / 收款 查询 ──

def list_payments(db: Session, account_id: int, skip: int = 0, limit: int = 100):
    return db.query(models.Payment).filter(
        models.Payment.account_id == account_id
    ).order_by(models.Payment.payment_date.desc()).offset(skip).limit(limit).all()


def get_payment(db: Session, account_id: int, payment_id: int):
    return db.query(models.Payment).filter(
        models.Payment.account_id == account_id,
        models.Payment.id == payment_id
    ).first()


def list_receipts(db: Session, account_id: int, skip: int = 0, limit: int = 100):
    return db.query(models.Receipt).filter(
        models.Receipt.account_id == account_id
    ).order_by(models.Receipt.receipt_date.desc()).offset(skip).limit(limit).all()


def get_receipt(db: Session, account_id: int, receipt_id: int):
    return db.query(models.Receipt).filter(
        models.Receipt.account_id == account_id,
        models.Receipt.id == receipt_id
    ).first()