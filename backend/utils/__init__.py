from decimal import Decimal
from datetime import datetime, date
from typing import Optional, Type, Any
from sqlalchemy.orm import Session
from sqlalchemy import ColumnElement

from errors import BusinessError, ErrorCode

Q2 = Decimal('0.01')


def _d(val):
    """安全转换为 Decimal"""
    if val is None:
        return Decimal('0')
    if isinstance(val, Decimal):
        return val
    return Decimal(str(val))


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
    "Product": (ErrorCode.PRODUCT_NOT_FOUND, {}),
    "Customer": (ErrorCode.CUSTOMER_NOT_FOUND, {}),
    "Invoice": (ErrorCode.INVOICE_NOT_FOUND, {}),
    "PersonalTransaction": (ErrorCode.ORDER_NOT_FOUND, {"order_type": "个人流水记录"}),
}

DELETED_CHECK_MODELS = {"SaleOrder", "PurchaseOrder"}


def get_or_404(db: Session, model: Type, id: int, account_id: int,
               extra_filters: Optional[list] = None) -> Any:
    """查询实体，不存在则抛 BusinessError (404)"""
    q = db.query(model).filter(
        model.id == id,
        model.account_id == account_id,
    )
    model_name = model.__name__
    if model_name in DELETED_CHECK_MODELS:
        q = q.filter(model.is_deleted == False)
    if extra_filters:
        for f in extra_filters:
            q = q.filter(f)
    obj = q.first()
    if not obj:
        error_code, error_data = ENTITY_ERROR_CODES.get(
            model_name, (ErrorCode.ORDER_NOT_FOUND, {})
        )
        error_data = {**error_data, "order_id": id}
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


# ── OperationResult 工厂 ──

from operation_result import OperationResult, OperationType, EntityType


def op_create(entity_type: EntityType, entity_id: int, entity_no: str,
              entity_label: str, data: dict, changes: Optional[dict] = None) -> dict:
    return OperationResult(
        operation=OperationType.CREATE,
        entity_type=entity_type,
        entity_id=entity_id,
        summary=f"{entity_label} {entity_no} 创建成功",
        ai_hint=f"{entity_label}已创建。",
        data=data,
        changes=changes or {},
    ).to_dict()


def op_update(entity_type: EntityType, entity_id: int, entity_no: str,
              entity_label: str, data: dict, changes: Optional[dict] = None) -> dict:
    return OperationResult(
        operation=OperationType.UPDATE,
        entity_type=entity_type,
        entity_id=entity_id,
        summary=f"{entity_label} {entity_no} 更新成功",
        ai_hint=f"{entity_label}已更新。",
        data=data,
        changes=changes or {},
    ).to_dict()


def op_delete(entity_type: EntityType, entity_id: int, entity_no: str,
              entity_label: str) -> dict:
    return OperationResult(
        operation=OperationType.DELETE,
        entity_type=entity_type,
        entity_id=entity_id,
        summary=f"{entity_label} {entity_no} 删除成功",
        ai_hint=f"{entity_label}已删除。",
    ).to_dict()
