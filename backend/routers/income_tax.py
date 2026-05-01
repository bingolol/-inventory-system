from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import datetime
from decimal import Decimal

from database import get_db
from models import Account, SaleOrder, PurchaseOrder, Expense
from schemas import IncomeTaxReport
from account_dep import get_account_id

Q2 = Decimal('0.01')

def _d(val):
    """安全转换为 Decimal"""
    if val is None:
        return Decimal('0')
    if isinstance(val, Decimal):
        return val
    return Decimal(str(val))

router = APIRouter()


@router.get("/", response_model=IncomeTaxReport)
async def get_income_tax_report(
    year: int,
    db: Session = Depends(get_db),
    account_id: int = Depends(get_account_id)
):
    """获取企业所得税年度报表"""
    # 获取账本信息
    account = db.query(Account).filter(Account.id == account_id).first()
    if not account:
        raise HTTPException(status_code=404, detail="账本不存在")
    
    # 计算年度起止日期
    start_date = datetime(year, 1, 1)
    end_date = datetime(year + 1, 1, 1)
    
    # 查询全年已完成销售订单（收入）
    total_revenue = _d(db.query(func.sum(SaleOrder.total_price)).filter(
        SaleOrder.account_id == account_id,
        SaleOrder.sale_date >= start_date,
        SaleOrder.sale_date < end_date,
        SaleOrder.status == "completed"
    ).scalar())
    
    # 查询全年已完成采购订单（成本）
    total_cost = _d(db.query(func.sum(PurchaseOrder.total_price)).filter(
        PurchaseOrder.account_id == account_id,
        PurchaseOrder.purchase_date >= start_date,
        PurchaseOrder.purchase_date < end_date,
        PurchaseOrder.status == "completed"
    ).scalar())
    
    # 查询全年费用
    operating_expenses = _d(db.query(func.sum(Expense.amount)).filter(
        Expense.account_id == account_id,
        Expense.expense_date >= start_date,
        Expense.expense_date < end_date
    ).scalar())
    
    # 计算毛利润
    gross_profit = total_revenue - total_cost
    
    # 计算应纳税所得额
    taxable_income = gross_profit - operating_expenses
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
        account_id=account_id,
        total_revenue=total_revenue.quantize(Q2),
        total_cost=total_cost.quantize(Q2),
        operating_expenses=operating_expenses.quantize(Q2),
        gross_profit=gross_profit.quantize(Q2),
        taxable_income=taxable_income.quantize(Q2),
        tax_rate=tax_rate,
        tax_amount=tax_amount
    )
    
    return report
