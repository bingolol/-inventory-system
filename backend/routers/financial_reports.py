from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from database import get_db
from account_dep import get_account_id
import crud, models

from datetime import datetime
from utils import end_of_day
from crud.finance._snapshot import LedgerSnapshot
from reports.engine import ReportEngine
from reports.reconcile import ReportReconciliation
from reports.definitions.balance_sheet import BALANCE_SHEET
from reports.definitions.income_statement import INCOME_STATEMENT

router = APIRouter()


def _extract_values_for_reconcile(result: dict) -> dict:
    """从 engine.execute 结果中提取 {key: float} 用于对账

    处理 trace=True（嵌套 {"value": ...}）和 trace=False（直接 float）两种格式。
    排除 _reconciliation 等元字段。
    """
    out = {}
    for k, v in result.items():
        if k.startswith("_"):
            continue
        if isinstance(v, dict) and "value" in v:
            out[k] = v["value"]
        elif isinstance(v, (int, float)):
            out[k] = v
    return out


@router.get("/balance-sheet")
def get_balance_sheet(
    date: str = Query(..., description="报表日期 (YYYY-MM-DD)"),
    trace: bool = Query(False, description="是否返回追溯链"),
    reconcile: bool = Query(False, description="是否返回双路径对账结果"),
    source_mode: str = Query("invoice", description="取数口径: invoice/ledger/both"),
    account_id: int = Depends(get_account_id),
    db: Session = Depends(get_db)
):
    """生成资产负债表"""
    qd = end_of_day(datetime.strptime(date, "%Y-%m-%d"))
    sn = LedgerSnapshot(db, account_id, bs_cutoff=qd)
    engine = ReportEngine()
    result = engine.execute(BALANCE_SHEET, sn, trace=trace, source_mode=source_mode)
    ta = result.get("total_assets", 0) if not trace else result["total_assets"]["value"]
    tle = result.get("total_liabilities_and_equity", 0) if not trace else result["total_liabilities_and_equity"]["value"]
    result["balanced"] = abs(float(ta) - float(tle)) < 0.01
    if reconcile:
        # 对账用 invoice 口径（避免 source_mode=both 导致 engine_values 嵌套）
        recon_values = _extract_values_for_reconcile(result)
        if source_mode != "invoice":
            recon_values = _extract_values_for_reconcile(engine.execute(BALANCE_SHEET, sn, source_mode="invoice"))
        recon = ReportReconciliation(db, sn, report_type="balance_sheet")
        result["_reconciliation"] = recon.reconcile(BALANCE_SHEET, recon_values, source_mode="invoice").to_dict()
    return result


@router.get("/income-statement")
def get_income_statement(
    start_date: str = Query(..., description="开始日期 (YYYY-MM-DD)"),
    end_date: str = Query(..., description="结束日期 (YYYY-MM-DD)"),
    trace: bool = Query(False, description="是否返回追溯链"),
    reconcile: bool = Query(False, description="是否返回双路径对账结果"),
    account_id: int = Depends(get_account_id),
    db: Session = Depends(get_db)
):
    """生成利润表"""
    sd = datetime.strptime(start_date, "%Y-%m-%d")
    ed = end_of_day(datetime.strptime(end_date, "%Y-%m-%d"))
    sn = LedgerSnapshot(db, account_id, bs_cutoff=ed, period_start=sd, period_end=ed)
    engine = ReportEngine()
    result = engine.execute(INCOME_STATEMENT, sn, trace=trace)
    if reconcile:
        recon_values = _extract_values_for_reconcile(result)
        recon = ReportReconciliation(db, sn, report_type="income_statement")
        result["_reconciliation"] = recon.reconcile(INCOME_STATEMENT, recon_values).to_dict()
    return result


@router.get("/financial-summary")
def get_financial_summary(
    date: str = Query(..., description="报表日期 (YYYY-MM-DD)"),
    account_id: int = Depends(get_account_id),
    db: Session = Depends(get_db)
):
    """获取财务汇总信息"""
    qd = end_of_day(datetime.strptime(date, "%Y-%m-%d"))
    sn = LedgerSnapshot(db, account_id, bs_cutoff=qd)
    engine = ReportEngine()
    balance_sheet = engine.execute(BALANCE_SHEET, sn)
    opening_balance = crud.get_latest_opening_balance(db, account_id, date)
    return {
        "balance_sheet": balance_sheet,
        "opening_balance_exists": opening_balance is not None,
        "opening_balance_date": opening_balance.date_l1.isoformat() if opening_balance else None
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
