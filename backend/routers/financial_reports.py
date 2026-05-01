from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from database import get_db
from account_dep import get_account_id
import schemas, crud

router = APIRouter()


@router.get("/balance-sheet")
def get_balance_sheet(
    date: str = Query(..., description="报表日期 (YYYY-MM-DD)"),
    account_id: int = Depends(get_account_id),
    db: Session = Depends(get_db)
):
    """生成资产负债表"""
    try:
        balance_sheet = crud.generate_balance_sheet(db, account_id, date)
        return balance_sheet
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"生成资产负债表失败: {str(e)}")


@router.get("/income-statement")
def get_income_statement(
    start_date: str = Query(..., description="开始日期 (YYYY-MM-DD)"),
    end_date: str = Query(..., description="结束日期 (YYYY-MM-DD)"),
    account_id: int = Depends(get_account_id),
    db: Session = Depends(get_db)
):
    """生成利润表"""
    try:
        income_statement = crud.generate_income_statement(db, account_id, start_date, end_date)
        return income_statement
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"生成利润表失败: {str(e)}")


@router.get("/financial-summary")
def get_financial_summary(
    date: str = Query(..., description="报表日期 (YYYY-MM-DD)"),
    account_id: int = Depends(get_account_id),
    db: Session = Depends(get_db)
):
    """获取财务汇总信息"""
    try:
        # 获取资产负债表
        balance_sheet = crud.generate_balance_sheet(db, account_id, date)
        
        # 获取期初余额信息
        opening_balance = crud.get_latest_opening_balance(db, account_id, date)
        
        return {
            "balance_sheet": balance_sheet,
            "opening_balance_exists": opening_balance is not None,
            "opening_balance_date": opening_balance.date.isoformat() if opening_balance else None
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取财务汇总失败: {str(e)}")