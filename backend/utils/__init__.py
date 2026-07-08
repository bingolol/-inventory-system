from decimal import Decimal
from datetime import datetime, date
from typing import Optional, Type, Any
from sqlalchemy.orm import Session
from sqlalchemy import ColumnElement

from errors import BusinessError, ErrorCode

Q2 = Decimal('0.01')
ZERO = Decimal('0')


def to_decimal(val):
    """安全转换为 Decimal，None → 0"""
    if val is None:
        return Decimal('0')
    if isinstance(val, Decimal):
        return val
    return Decimal(str(val))


_d = to_decimal  # 历史别名，新代码请用 to_decimal


def end_of_day(dt: datetime) -> datetime:
    """返回当日 23:59:59，用于截止时间查询"""
    return dt.replace(hour=23, minute=59, second=59, microsecond=0)


def get_quarter_date_range(year: int, quarter: int) -> tuple:
    """返回季度起止日期（半开区间 [start, end)）"""
    start = datetime(year, (quarter - 1) * 3 + 1, 1)
    if quarter == 4:
        end = datetime(year + 1, 1, 1)
    else:
        end = datetime(year, quarter * 3 + 1, 1)
    return start, end


# ── 实体查询 ──

ENTITY_ERROR_CODES = {
    "SaleOrder": (ErrorCode.ORDER_NOT_FOUND, {"order_type": "销售单"}),
    "PurchaseOrder": (ErrorCode.ORDER_NOT_FOUND, {"order_type": "采购单"}),
    "Expense": (ErrorCode.EXPENSE_NOT_FOUND, {}),
    "FixedAsset": (ErrorCode.FIXED_ASSET_NOT_FOUND, {}),
    "IntangibleAsset": (ErrorCode.ORDER_NOT_FOUND, {"order_type": "无形资产"}),
    "Product": (ErrorCode.PRODUCT_NOT_FOUND, {}),
    "Customer": (ErrorCode.CUSTOMER_NOT_FOUND, {}),
    "Supplier": (ErrorCode.CUSTOMER_NOT_FOUND, {}),
    "Invoice": (ErrorCode.INVOICE_NOT_FOUND, {}),
    "PersonalTransaction": (ErrorCode.ORDER_NOT_FOUND, {"order_type": "个人流水记录"}),
    "PersonalAdvance": (ErrorCode.ORDER_NOT_FOUND, {"order_type": "垫付单"}),
    "PersonalAdvanceRepayment": (ErrorCode.ORDER_NOT_FOUND, {"order_type": "偿还记录"}),
    "CashFlowTransaction": (ErrorCode.CASH_FLOW_NOT_FOUND, {}),
    "BankStatement": (ErrorCode.ORDER_NOT_FOUND, {"order_type": "对账单"}),
    "OpeningBalance": (ErrorCode.ORDER_NOT_FOUND, {"order_type": "期初余额"}),
    "Payment": (ErrorCode.ORDER_NOT_FOUND, {"order_type": "付款记录"}),
    "Receipt": (ErrorCode.ORDER_NOT_FOUND, {"order_type": "收款记录"}),
}


def get_or_404(db: Session, model: Type, id: int, account_id: int,
               extra_filters: Optional[list] = None) -> Any:
    """查询实体，不存在则抛 BusinessError (404)"""
    q = db.query(model).filter(
        model.id == id,
        model.account_id == account_id,
    )
    model_name = model.__name__
    if hasattr(model, 'is_deleted'):
        q = q.filter(model.is_deleted == False)
    if extra_filters:
        for f in extra_filters:
            q = q.filter(f)
    obj = q.first()
    if not obj:
        error_code, error_data = ENTITY_ERROR_CODES.get(
            model_name, (ErrorCode.ORDER_NOT_FOUND, {})
        )
        error_data = {**error_data, "id": id}
        raise BusinessError(code=error_code, data=error_data)
    return obj


# ── 日期操作 ──

DATE_FMT = "%Y-%m-%d"
DATETIME_END_FMT = "%Y-%m-%d %H:%M:%S"


def parse_date(s: str) -> datetime:
    """解析 'YYYY-MM-DD' → datetime"""
    return datetime.strptime(s, DATE_FMT)


def parse_date_end(s: str) -> datetime:
    """解析 'YYYY-MM-DD' → 当日 23:59:59 用于范围查询"""
    return datetime.strptime(s + " 23:59:59", DATETIME_END_FMT)


def fmt_date(d: Optional[date]) -> Optional[str]:
    """date/datetime → ISO date 字符串，None 返回 None"""
    if d is None:
        return None
    if isinstance(d, datetime):
        return d.date().isoformat()
    return d.isoformat()


def fmt_datetime(dt: Optional[datetime]) -> Optional[str]:
    """datetime → ISO 字符串，None 返回 None"""
    return dt.isoformat() if dt else None


def parse_date_to_date(s: str) -> date:
    """解析 'YYYY-MM-DD' → date 对象"""
    return datetime.strptime(s, DATE_FMT).date()



