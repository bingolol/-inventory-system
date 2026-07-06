"""审计日志 — SQLAlchemy 事件监听器自动记录实体变更。

设计：
  - after_insert / before_delete：直接捕获当前状态
  - before_update / before_flush 配合：在 flush 前从 DB 查旧值，在 update 时写入审计
  - 审计上下文（account_id, operator）通过 session.info 传递

注意：
  在 flush 阶段（after_insert / after_flush / before_delete）不能使用 session.add()，
  否则触发 SAWarning: "Usage of the 'Session.add()' operation is not currently
  supported within the execution stage of the flush process"。
  解决方案：通过事件回调中的 connection 参数直接执行 INSERT。
"""
import json
from datetime import datetime, date
from decimal import Decimal
from sqlalchemy import event, insert
from sqlalchemy.orm import Session
from models import (
    AuditLog, SaleOrder, PurchaseOrder, Product, Expense, Invoice, FixedAsset,
    Account, Payment, Receipt,
)

# 受审计的实体列表
_AUDIT_ENTITIES = [
    SaleOrder, PurchaseOrder, Product, Expense, Invoice, FixedAsset,
    Account, Payment, Receipt,
]


def _to_dict(obj) -> dict:
    """ORM → JSON 兼容 dict"""
    if obj is None:
        return {}
    d = {}
    for col in obj.__table__.columns:
        v = getattr(obj, col.name)
        if isinstance(v, datetime):
            v = v.isoformat()
        elif isinstance(v, date):
            v = v.isoformat()
        elif isinstance(v, Decimal):
            v = float(v)
        elif v is not None and not isinstance(v, (int, float, str, bool, list, dict)):
            v = str(v)
        d[col.name] = v
    return d


def _ctx(db) -> dict:
    c = db.info.get("audit", {})
    return {"account_id": c.get("account_id"), "operator": c.get("operator", "system")}


def _write_via_conn(connection, db, action, entity_type, entity_id, before=None, after=None):
    """通过 connection 直接 INSERT 审计日志，避免 flush 阶段 session.add() 警告。"""
    ctx = _ctx(db)
    changed = [k for k in (before or {}) if before.get(k) != (after or {}).get(k)] if before and after else None
    account_id = ctx["account_id"] or (after or before or {}).get("account_id")
    connection.execute(insert(AuditLog.__table__).values(
        account_id=account_id,
        operator=ctx["operator"],
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        before_data=json.dumps(before, ensure_ascii=False) if before else None,
        after_data=json.dumps(after, ensure_ascii=False) if after else None,
        changed_fields=json.dumps(changed, ensure_ascii=False) if changed else None,
        created_at=datetime.now(),
    ))


# ── 公共入口 ───────────────────────────────────────────────

def set_audit_context(db: Session, account_id: int = None, operator: str = None):
    """请求入口调用：设置审计上下文。"""
    db.info.setdefault("audit", {}).update(
        account_id=account_id, operator=operator or "system",
    )


def register_listeners():
    """启动时调用：注册所有事件监听。"""

    for model in _AUDIT_ENTITIES:
        tbl = model.__tablename__

        @event.listens_for(model, 'after_insert')
        def on_insert(mapper, connection, target, _m=model, _t=tbl):
            try:
                db = Session.object_session(target)
                if db is None: return
                _write_via_conn(connection, db, "create", _t, target.id, after=_to_dict(target))
            except Exception:
                pass

        @event.listens_for(model, 'before_delete')
        def on_delete(mapper, connection, target, _m=model, _t=tbl):
            try:
                db = Session.object_session(target)
                if db is None: return
                _write_via_conn(connection, db, "delete", _t, target.id, before=_to_dict(target))
            except Exception:
                pass

    # before_update：在 UPDATE SQL 执行前触发，此时 DB 仍是旧值
    # 我们结合 before_flush 捕获待更新对象的 DB 快照
    @event.listens_for(Session, 'before_flush')
    def capture_old_values(session, flush_context, instances):
        """flush 前从数据库查询 dirty 对象的当前值（即将被覆盖）。"""
        olds = {}
        for obj in session.dirty:
            if not any(isinstance(obj, e) for e in _AUDIT_ENTITIES):
                continue
            # 重新查询 DB 获取即将被覆盖的值
            try:
                old = session.query(type(obj)).filter(type(obj).id == obj.id).with_for_update().first()
                if old:
                    olds[id(obj)] = _to_dict(old)
            except Exception:
                pass
        session.info["_audit_old"] = olds

    @event.listens_for(Session, 'after_flush')
    def write_update_logs(session, flush_context):
        """flush 后，对比新旧值写入审计。"""
        olds = session.info.pop("_audit_old", {})
        if not olds:
            return
        conn = session.connection()
        for obj in session.dirty:
            if id(obj) not in olds:
                continue
            if not any(isinstance(obj, e) for e in _AUDIT_ENTITIES):
                continue
            before = olds[id(obj)]
            after = _to_dict(obj)
            if before != after:
                _write_via_conn(conn, session, "update", type(obj).__tablename__, obj.id,
                               before=before, after=after)
