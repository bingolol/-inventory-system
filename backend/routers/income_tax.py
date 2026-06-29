# ⚠️ 注意：本路由当前仅包含只读操作（GET），不需要 uow 包裹。
# 如未来新增写操作（POST/PUT/DELETE），务必使用 `with unit_of_work(db):` 包裹。
#
# 企业所得税报表 — 税务口径（发票说话）
# 取消经营口径（订单说话），统一以发票为准，避免含税/不含税口径不一致

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, exists as sa_exists
from datetime import datetime
from decimal import Decimal
from typing import Optional

from database import get_db
from models import Account, Invoice, Expense
from schemas import IncomeTaxReport
from account_dep import get_account_id
from enums import InvoiceDirection
from utils import _d, Q2
from errors import BusinessError, ErrorCode
from accounting_engine import AccountingEngine

router = APIRouter()
_engine = AccountingEngine()


def _get_date_range(year: int, quarter: Optional[int]):
    """计算起止日期"""
    if quarter and 1 <= quarter <= 4:
        quarter_start_month = (quarter - 1) * 3 + 1
        start_date = datetime(year, quarter_start_month, 1)
        if quarter == 4:
            end_date = datetime(year + 1, 1, 1)
        else:
            end_date = datetime(year, quarter_start_month + 3, 1)
    else:
        start_date = datetime(year, 1, 1)
        end_date = datetime(year + 1, 1, 1)
    return start_date, end_date


def _calc_tax_caliber(db: Session, account_id: int, start_date: datetime, end_date: datetime):
    """税务口径计算（发票说话）"""
    # 收入 = 销项发票不含税金额
    invoice_revenue = _d(db.query(func.sum(Invoice.amount_without_tax)).filter(
        Invoice.account_id == account_id,
        Invoice.direction == InvoiceDirection.OUT,
        Invoice.issue_date >= start_date,
        Invoice.issue_date < end_date
    ).scalar())

    # 成本 = 进项发票不含税金额
    invoice_cost = _d(db.query(func.sum(Invoice.amount_without_tax)).filter(
        Invoice.account_id == account_id,
        Invoice.direction == InvoiceDirection.IN,
        Invoice.issue_date >= start_date,
        Invoice.issue_date < end_date
    ).scalar())

    # 有票费用
    invoiced_expenses = _d(db.query(func.sum(Expense.amount)).filter(
        Expense.account_id == account_id,
        Expense.expense_date >= start_date,
        Expense.expense_date < end_date,
        sa_exists().where(
            Invoice.account_id == account_id,
            Invoice.related_order_type == "expense",
            Invoice.related_order_id == Expense.id,
        )
    ).scalar())

    # 无票费用
    non_invoice_expenses = _d(db.query(func.sum(Expense.amount)).filter(
        Expense.account_id == account_id,
        Expense.expense_date >= start_date,
        Expense.expense_date < end_date,
        ~sa_exists().where(
            Invoice.account_id == account_id,
            Invoice.related_order_type == "expense",
            Invoice.related_order_id == Expense.id,
        )
    ).scalar())

    return {
        "revenue": invoice_revenue,
        "cost": invoice_cost,
        "expenses": invoiced_expenses,
        "non_invoice_expenses": non_invoice_expenses,
    }


@router.get("", response_model=IncomeTaxReport)
async def get_income_tax_report(
    year: int,
    quarter: Optional[int] = None,
    db: Session = Depends(get_db),
    account_id: int = Depends(get_account_id)
):
    """获取企业所得税报表（税务口径：发票说话）"""
    # 获取账本信息
    account = db.query(Account).filter(Account.id == account_id).first()
    if not account:
        raise BusinessError(code=ErrorCode.ORDER_NOT_FOUND, data={"order_type": "账本", "order_id": account_id})

    start_date, end_date = _get_date_range(year, quarter)

    # 税务口径（发票说话）
    data = _calc_tax_caliber(db, account_id, start_date, end_date)

    revenue = data["revenue"]
    cost = data["cost"]
    expenses = data["expenses"]
    non_invoice_expenses = data["non_invoice_expenses"]

    # 增值税减免加回收入（财税〔2008〕151号：减免的增值税需计入应纳税所得额）
    # 从总账 6301（营业外收入-税收减免）贷方发生额获取
    from models_finance import Ledger, LedgerAccount, AccountMove, AccountMoveLine
    from sqlalchemy import func as sqlfunc
    ledger = db.query(Ledger).filter(Ledger.code == account.code).first()
    if ledger:
        vat_exemption_income = _d(db.query(sqlfunc.sum(AccountMoveLine.credit)).join(
            LedgerAccount, AccountMoveLine.ledger_account_id == LedgerAccount.id
        ).join(AccountMove, AccountMoveLine.move_id == AccountMove.id).filter(
            LedgerAccount.ledger_id == ledger.id, LedgerAccount.code == "6301",
            AccountMove.date >= start_date, AccountMove.date <= end_date
        ).scalar())
    else:
        vat_exemption_income = Decimal('0')
    revenue += vat_exemption_income

    # 计算毛利润
    gross_profit = revenue - cost

    # 计算应纳税所得额
    taxable_income = gross_profit - expenses
    if taxable_income < 0:
        taxable_income = Decimal('0')

    # 使用 AccountingEngine 计算所得税
    # 所得税纳税人类型映射：VAT 口径 small_scale → 所得税口径 small_micro（小型微利企业优惠）
    # 小规模纳税人通常同时也是小型微利企业，适用 5% 实际税负（25%×20%）
    raw_type = account.taxpayer_type if account.taxpayer_type else "small_scale"
    taxpayer_type = "small_micro" if raw_type in ("small_scale", "small_micro") else "general"
    entity_type = account.type if account.type else "company"
    tax_result = _engine.calculate_income_tax(
        profit=taxable_income,
        taxpayer_type=taxpayer_type,
        entity_type=entity_type,
    )

    # 构建报表
    report = IncomeTaxReport(
        year=year,
        quarter=quarter,
        account_id=account_id,
        total_revenue=revenue.quantize(Q2),
        total_cost=cost.quantize(Q2),
        operating_expenses=expenses.quantize(Q2),
        gross_profit=gross_profit.quantize(Q2),
        taxable_income=taxable_income.quantize(Q2),
        tax_rate=tax_result.tax_rate,
        tax_amount=tax_result.tax_payable,
        invoice_revenue=revenue.quantize(Q2),
        invoice_cost=cost.quantize(Q2),
        invoiced_expenses=expenses.quantize(Q2),
        non_invoice_expenses=non_invoice_expenses.quantize(Q2),
    )

    return report