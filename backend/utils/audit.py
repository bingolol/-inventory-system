"""审计日志自动化 — SQLAlchemy 事件监听器

通过 before_flush + after_flush 两阶段捕获所有数据变更：
  - before_flush: 收集变更对象（此时 INSERT 对象尚无 ID）
  - after_flush: 创建 AuditLog 记录（此时所有 ID 已生成）

操作上下文（operator / account_id）通过 contextvar 传入，
由 FastAPI 中间件 AuditContextMiddleware 在每个请求开始时设置。
"""

import logging
import contextvars
from datetime import datetime, date
from decimal import Decimal
from sqlalchemy import event, inspect
from sqlalchemy.orm import Session, ColumnProperty
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from models import AuditLog, AuditableMixin

logger = logging.getLogger("inventory")

# 操作上下文：由 AuditContextMiddleware 在每个请求开始时设置
audit_ctx: contextvars.ContextVar[dict] = contextvars.ContextVar("audit_ctx", default={})


def _serialize(obj):
    """将 ORM 对象转为可 JSON 序列化的字典"""
    result = {}
    for c in obj.__table__.columns:
        val = getattr(obj, c.name)
        if isinstance(val, Decimal):
            result[c.name] = float(val)
        elif isinstance(val, (datetime, date)):
            result[c.name] = val.isoformat()
        elif isinstance(val, bytes):
            result[c.name] = val.hex() if val else None
        else:
            result[c.name] = val
    return result


def _get_changes(obj):
    """计算 ORM 对象的变更字段，返回 {field: {old: ..., new: ...}}

    只跟踪 ColumnProperty（实际数据库列），跳过关系属性（RelationshipProperty），
    因为关系属性的值可能是 ORM 对象，无法 JSON 序列化。
    """
    insp = inspect(obj)
    exclude = getattr(obj, '__audit_exclude__', [])
    changes = {}
    for attr in insp.attrs:
        if not isinstance(attr, ColumnProperty):
            continue
        hist = attr.load_history()
        if hist.has_changes():
            field = attr.key
            if field in exclude:
                continue
            old = hist.unchanged[0] if hist.unchanged else None
            new = attr.value
            old_compat = _safe_value(old)
            new_compat = _safe_value(new)
            if old_compat != new_compat:
                changes[field] = {"old": old_compat, "new": new_compat}
    return changes


def _safe_value(val):
    """将值转为 JSON 安全类型"""
    if isinstance(val, Decimal):
        return float(val)
    if isinstance(val, (datetime, date)):
        return val.isoformat()
    if isinstance(val, bytes):
        return val.hex() if val else None
    return val


def _is_auditable(obj):
    """判断对象是否需要审计"""
    return isinstance(obj, AuditableMixin) and not isinstance(obj, AuditLog)


@event.listens_for(Session, 'before_flush')
def _before_flush_collect(session, context, instances):
    """Phase 1: 收集变更对象（此时 INSERT 对象尚无 ID）"""
    pendings = []

    for obj in session.new:
        if _is_auditable(obj):
            pendings.append({
                'action': 'INSERT',
                'obj': obj,
                'before': None,
                'after': _serialize(obj),
                'changes': None,
            })

    for obj in session.dirty:
        if _is_auditable(obj):
            changes = _get_changes(obj)
            if changes:
                pendings.append({
                    'action': 'UPDATE',
                    'obj': obj,
                    'before': {k: v['old'] for k, v in changes.items()},
                    'after': {k: v['new'] for k, v in changes.items()},
                    'changes': changes,
                })

    for obj in session.deleted:
        if _is_auditable(obj):
            pendings.append({
                'action': 'DELETE',
                'obj': obj,
                'before': _serialize(obj),
                'after': None,
                'changes': None,
            })

    if pendings:
        session.info['_pending_audit'] = pendings


@event.listens_for(Session, 'after_flush')
def _after_flush_create_logs(session, context):
    """Phase 2: 创建审计日志（此时所有 ID 已生成）"""
    pendings = session.info.pop('_pending_audit', None)
    if not pendings:
        return

    ctx = audit_ctx.get()
    operator = ctx.get('operator', 'system')
    account_id = ctx.get('account_id')

    logs = []
    for p in pendings:
        obj = p['obj']
        log = AuditLog(
            account_id=account_id,
            operator=operator,
            action=p['action'],
            entity_type=obj.__tablename__,
            entity_id=obj.id,
            before_data=p['before'],
            after_data=p['after'] if p['action'] != 'DELETE' else None,
            changed_fields=p['changes'] if p['action'] == 'UPDATE' else
                         (list(p['after'].keys()) if p['action'] == 'INSERT' and p['after'] else None),
        )
        logs.append(log)

    if logs:
        session.add_all(logs)


# ═══════════════════════════════════════════════════════════
# FastAPI 中间件：在每个请求开始时设置 audit_ctx
# ═══════════════════════════════════════════════════════════

class AuditContextMiddleware(BaseHTTPMiddleware):
    """在每个请求开始时，从请求头提取操作上下文并注入 audit_ctx。

    用法: app.add_middleware(AuditContextMiddleware)
    """

    async def dispatch(self, request: Request, call_next):
        operator = request.headers.get("X-Operator", "user")
        account_id = None
        raw_id = request.headers.get("X-Account-ID")
        if raw_id:
            account_id = int(raw_id)

        token = audit_ctx.set({"operator": operator, "account_id": account_id})
        try:
            response = await call_next(request)
            return response
        finally:
            audit_ctx.reset(token)