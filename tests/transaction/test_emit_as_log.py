"""方案 1.1 验证测试：Emit-as-Log 单一写入点

直接 dispatch 命令（绕过 HTTP 中间件），验证：
1. 每个写操作恰好产生 1 条 OperationLog（历史双写 bug 已修复）
2. operator 正确传播到日志
3. log_detail 携带业务上下文（商品数/总价等）

使用 transaction 临时 DB（普通 session，无 ORM 写守卫）。
"""
import pytest
from datetime import datetime
from decimal import Decimal
from commands.base import dispatch
from commands.orders import CreateOrder, CancelOrder, DeleteOrder
from models import OperationLog
from tests.factories import make_product, make_customer, make_supplier

import handlers  # noqa: F401  注册事件订阅者（emit → handler 写日志）


def _max_log_id(db):
    row = db.query(OperationLog).order_by(OperationLog.id.desc()).first()
    return row.id if row else 0


def _logs_since(db, since_id, entity_type, entity_id):
    return db.query(OperationLog).filter(
        OperationLog.id > since_id,
        OperationLog.entity_type == entity_type,
        OperationLog.entity_id == entity_id,
    ).order_by(OperationLog.id.asc()).all()


@pytest.mark.usefixtures("bootstrap_db")
class TestEmitAsLogSingleWrite:
    """每个写操作应恰好写 1 条 OperationLog（Emit-as-Log 单一写入点）"""

    def test_create_sale_exactly_one_log(self, db):
        """创建销售单 → 恰好 1 条日志，operator/detail 正确"""
        p = make_product(db, 1, track_inventory=False)
        c = make_customer(db, 1)
        db.flush()
        before = _max_log_id(db)

        order = dispatch(CreateOrder(order_type="sale", 
            account_id=1, operator="ai",
            customer_id=c.id, deduct_inventory=False,
            payment_status="unpaid", sale_date=datetime(2026,6,29,10,0,0),
            items=[{"product_id": p.id, "quantity": 2, "unit_price": 20, "tax_rate": Decimal("0.01")}],
        ), db)

        logs = _logs_since(db, before, "sale_order", order.id)
        assert len(logs) == 1, f"创建销售单应恰好 1 条日志（Emit-as-Log），实际 {len(logs)} 条: {[l.detail for l in logs]}"
        assert logs[0].operation == "create"
        assert logs[0].operator == "ai"
        assert "创建销售单" in logs[0].detail
        assert "1项商品" in logs[0].detail  # 业务上下文已携带（项数=行项数）
        assert "总价=40.00" in logs[0].detail  # 2×20=40

    def test_create_purchase_exactly_one_log(self, db):
        """创建采购单 → 恰好 1 条日志"""
        p = make_product(db, 1, track_inventory=False)
        s = make_supplier(db, 1)
        db.flush()
        before = _max_log_id(db)

        order = dispatch(CreateOrder(order_type="purchase", 
            account_id=1, operator="user",
            supplier_id=s.id, purchase_date=datetime(2026,6,29,10,0,0),
            items=[{"product_id": p.id, "quantity": 3, "unit_price": 10}],
        ), db)

        logs = _logs_since(db, before, "purchase_order", order.id)
        assert len(logs) == 1, f"创建采购单应恰好 1 条日志，实际 {len(logs)} 条: {[l.detail for l in logs]}"
        assert logs[0].operation == "create"
        assert logs[0].operator == "user"
        assert "创建采购单" in logs[0].detail

    def test_cancel_sale_exactly_one_log(self, db):
        """取消销售单 → 恰好 1 条日志，operation=update"""
        p = make_product(db, 1, track_inventory=False)
        c = make_customer(db, 1)
        db.flush()
        order = dispatch(CreateOrder(order_type="sale", 
            account_id=1, operator="ai",
            customer_id=c.id, deduct_inventory=False,
            payment_status="unpaid", sale_date=datetime(2026,6,29,10,0,0),
            items=[{"product_id": p.id, "quantity": 1, "unit_price": 10, "tax_rate": Decimal("0.01")}],
        ), db)
        before = _max_log_id(db)

        dispatch(CancelOrder(order_type="sale", account_id=1, operator="ai", order_id=order.id), db)

        logs = _logs_since(db, before, "sale_order", order.id)
        assert len(logs) == 1, f"取消销售单应恰好 1 条日志，实际 {len(logs)} 条: {[l.detail for l in logs]}"
        assert logs[0].operation == "update"
        assert "取消销售单" in logs[0].detail

    def test_delete_purchase_exactly_one_log(self, db):
        """删除采购单 → 恰好 1 条日志，operation=delete"""
        p = make_product(db, 1, track_inventory=False)
        s = make_supplier(db, 1)
        db.flush()
        order = dispatch(CreateOrder(order_type="purchase", 
            account_id=1, operator="user",
            supplier_id=s.id, purchase_date=datetime(2026,6,29,10,0,0),
            items=[{"product_id": p.id, "quantity": 1, "unit_price": 10}],
        ), db)
        before = _max_log_id(db)

        dispatch(DeleteOrder(order_type="purchase", account_id=1, operator="user", order_id=order.id), db)

        logs = _logs_since(db, before, "purchase_order", order.id)
        assert len(logs) == 1, f"删除采购单应恰好 1 条日志，实际 {len(logs)} 条: {[l.detail for l in logs]}"
        assert logs[0].operation == "delete"
        assert "删除采购单" in logs[0].detail
