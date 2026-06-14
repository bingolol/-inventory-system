# ⚠️ 注意：本路由当前仅包含只读操作（GET），不需要 uow 包裹。
# 如未来新增写操作（POST/PUT/DELETE），务必使用 `with unit_of_work(db):` 包裹。
#
# 企业所得税报表 — 税务口径（发票说话）
# 收入 = 销项发票(amount_without_tax)
# 成本 = 进项发票(amount_without_tax)
# 费用 = 有票费用(Expense.has_invoice=True)
# 与利润报表（经营口径）的关键区别：只认发票，不认订单

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import datetime
from decimal import Decimal
from typing import Optional

from database import get_db
from models import Account, Invoice, Expense
from schemas import IncomeTaxReport
from account_dep import get_account_id
from enums import InvoiceDirection
from utils import _d, Q2

router = APIRouter()


@router.get("", response_model=IncomeTaxReport)
async def get_income_tax_report(
    year: int,
    quarter: Optional[int] = None,
    db: Session = Depends(get_db),
    account_id: int = Depends(get_account_id)
):
    """获取企业所得税报表（税务口径：发票说话）

    支持按年度或按季度查询。
    税务口径 vs 经营口径：
    - 收入：销项发票不含税金额（非SaleOrder）
    - 成本：进项发票不含税金额（非PurchaseOrder）
    - 费用：仅有票费用可税前扣除（非全部Expense）
    """
    # 获取账本信息
    account = db.query(Account).filter(Account.id == account_id).first()
    if not account:
        raise HTTPException(status_code=404, detail="账本不存在")

    # 计算起止日期
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

    # ── 税务口径：收入 = 销项发票不含税金额 ──
    invoice_revenue = _d(db.query(func.sum(Invoice.amount_without_tax)).filter(
        Invoice.account_id == account_id,
        Invoice.direction == InvoiceDirection.OUT,
        Invoice.issue_date >= start_date,
        Invoice.issue_date < end_date
    ).scalar())

    # ── 税务口径：成本 = 进项发票不含税金额 ──
    invoice_cost = _d(db.query(func.sum(Invoice.amount_without_tax)).filter(
        Invoice.account_id == account_id,
        Invoice.direction == InvoiceDirection.IN,
        Invoice.issue_date >= start_date,
        Invoice.issue_date < end_date
    ).scalar())

    # ── 税务口径：费用 = 仅有票费用可税前扣除 ──
    invoiced_expenses = _d(db.query(func.sum(Expense.amount)).filter(
        Expense.account_id == account_id,
        Expense.expense_date >= start_date,
        Expense.expense_date < end_date,
        Expense.has_invoice == True
    ).scalar())

    # 无票费用（仅供参考，不可税前扣除）
    non_invoice_expenses = _d(db.query(func.sum(Expense.amount)).filter(
        Expense.account_id == account_id,
        Expense.expense_date >= start_date,
        Expense.expense_date < end_date,
        Expense.has_invoice == False
    ).scalar())

    # 计算毛利润
    gross_profit = invoice_revenue - invoice_cost

    # 计算应纳税所得额（仅扣减有票费用）
    taxable_income = gross_profit - invoiced_expenses
    if taxable_income < 0:
        taxable_income = Decimal('0')

    # 小微企业税率简化
    # 实际实现：先统一用 5%（tax_rate = 0.05），后续用户可配置
    tax_rate = Decimal('0.05')

    # 计算应纳企业所得税
    tax_amount = (taxable_income * tax_rate).quantize(Q2)

    # 构建报表
    report = IncomeTaxReport(
        year=year,
        quarter=quarter,
        account_id=account_id,
        total_revenue=invoice_revenue.quantize(Q2),
        total_cost=invoice_cost.quantize(Q2),
        operating_expenses=invoiced_expenses.quantize(Q2),
        gross_profit=gross_profit.quantize(Q2),
        taxable_income=taxable_income.quantize(Q2),
        tax_rate=tax_rate,
        tax_amount=tax_amount,
        invoice_revenue=invoice_revenue.quantize(Q2),
        invoice_cost=invoice_cost.quantize(Q2),
        invoiced_expenses=invoiced_expenses.quantize(Q2),
        non_invoice_expenses=non_invoice_expenses.quantize(Q2),
    )

    return report