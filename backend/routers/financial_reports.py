from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from database import get_db
from account_dep import get_account_id
import schemas, crud, models

router = APIRouter()


@router.get("/balance-sheet")
def get_balance_sheet(
    date: str = Query(..., description="报表日期 (YYYY-MM-DD)"),
    account_id: int = Depends(get_account_id),
    db: Session = Depends(get_db)
):
    """生成资产负债表

    异常处理：不在路由层吞没异常。crud 层可能抛出 BusinessError（如日期格式非法）
    或 AccountingError（如科目余额不平衡），由 main.py 的全局 exception_handler
    统一映射为正确的 HTTP 状态码与错误码。原 try/except 会把这些异常统一包成
    INTERNAL_ERROR，掩盖真实错误类型并误导前端处理。
    """
    return crud.generate_balance_sheet(db, account_id, date)


@router.get("/income-statement")
def get_income_statement(
    start_date: str = Query(..., description="开始日期 (YYYY-MM-DD)"),
    end_date: str = Query(..., description="结束日期 (YYYY-MM-DD)"),
    account_id: int = Depends(get_account_id),
    db: Session = Depends(get_db)
):
    """生成利润表（异常交由全局 handler 处理，不在路由层吞没）"""
    return crud.generate_income_statement(db, account_id, start_date, end_date)


@router.get("/financial-summary")
def get_financial_summary(
    date: str = Query(..., description="报表日期 (YYYY-MM-DD)"),
    account_id: int = Depends(get_account_id),
    db: Session = Depends(get_db)
):
    """获取财务汇总信息（异常交由全局 handler 处理，不在路由层吞没）"""
    balance_sheet = crud.generate_balance_sheet(db, account_id, date)
    opening_balance = crud.get_latest_opening_balance(db, account_id, date)

    return {
        "balance_sheet": balance_sheet,
        "opening_balance_exists": opening_balance is not None,
        "opening_balance_date": opening_balance.date.isoformat() if opening_balance else None
    }


@router.get("/cwbb-xqykjzz")
def get_cwbb_xqykjzz(
    report_type: str = Query(..., description="报表类型: monthly / quarterly / annual"),
    date: str = Query(..., description="报表日期 (YYYY-MM-DD)"),
    account_id: int = Depends(get_account_id),
    db: Session = Depends(get_db)
):
    """小企业会计准则财务报表（会小企01/02/03表）模板数据聚合接口"""
    if report_type not in ("monthly", "quarterly", "annual"):
        from errors import BusinessError, ErrorCode
        raise BusinessError(code=ErrorCode.VALIDATION_ERROR, message="report_type 必须是 monthly / quarterly / annual")

    account = db.query(models.Account).filter(models.Account.id == account_id).first()
    return crud.generate_cwbb_xqykjzz(db, account_id, report_type, date, account)
