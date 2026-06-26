"""Test data factories — 创建测试数据的辅助工具

用法:
  集成测试 (API):   factories.create_product(client, headers)
  单元测试 (DB):    factories.make_product(db, account_id)
"""
import uuid
from datetime import datetime, timedelta
from decimal import Decimal

from helpers import get_entity_id, uniq


# ── DB-level factories (unit tests) ──

def make_account(db, name="测试账本"):
    from models import Account
    tag = uuid.uuid4().hex[:8]
    acc = Account(name=name, code=f"TEST-{tag}", enable_vat_deduction=False)
    db.add(acc)
    db.flush()
    return acc

def make_ledger(db, name="测试账本", type="company"):
    from models_finance import Ledger
    tag = uuid.uuid4().hex[:8]
    l = Ledger(name=name, type=type, code=f"ledger-{tag}")
    db.add(l)
    db.flush()
    return l

def make_ledger_account(db, ledger, code=None, name=None, account_type="asset"):
    from models_finance import LedgerAccount
    tag = uuid.uuid4().hex[:8]
    la = LedgerAccount(
        ledger_id=ledger.id, code=code or f"1{tag[:4]}",
        name=name or f"科目-{tag}", type=account_type,
    )
    db.add(la)
    db.flush()
    return la

def make_product(db, account_id, name=None, track_inventory=True, purchase_price=Decimal("10"), sale_price=Decimal("20")):
    from models import Product
    tag = uuid.uuid4().hex[:8]
    p = Product(
        account_id=account_id,
        name=name or f"商品-{tag}",
        sku=f"SKU-{tag}",
        unit="个",
        purchase_price=purchase_price,
        sale_price=sale_price,
        track_inventory=track_inventory,
        category="测试",
    )
    db.add(p)
    db.flush()
    return p

def make_customer(db, account_id, name=None):
    tag = uuid.uuid4().hex[:8]
    from models import Partner
    p = Partner(
        account_id=account_id,
        name=name or f"客户-{tag}", partner_type="customer",
        contact="测试", phone=f"138{tag[:8]}",
    )
    db.add(p)
    db.flush()
    return p

def make_supplier(db, account_id, name=None):
    tag = uuid.uuid4().hex[:8]
    from models import Partner
    p = Partner(
        account_id=account_id,
        name=name or f"供应商-{tag}", partner_type="supplier",
        contact="测试", phone=f"139{tag[:8]}",
    )
    db.add(p)
    db.flush()
    return p

def make_stock_move(db, product_id, qty, unit_cost, move_type="inbound", source_type="purchase", ref_id=None):
    from models import StockMove
    sm = StockMove(
        product_id=product_id, quantity=qty, unit_cost=unit_cost,
        move_type=move_type, source_type=source_type, reference_id=ref_id,
    )
    db.add(sm)
    db.flush()
    return sm

def make_bank_account(db, account_id, name=None, balance=Decimal("100000")):
    tag = uuid.uuid4().hex[:8]
    from models import BankAccount
    ba = BankAccount(
        account_id=account_id,
        name=name or f"银行账户-{tag}",
        account_number=f"6222{tag[:12]}",
        balance=balance,
    )
    db.add(ba)
    db.flush()
    return ba


# ── API-level factories (integration / e2e tests) ──

def api_create_product(client, headers, **overrides):
    """通过 API 创建商品，返回 (id, json)"""
    tag = uniq("F")
    payload = {
        "name": f"工厂商品-{tag}", "sku": f"SKU-{tag}",
        "unit": "个", "purchase_price": 10.00, "sale_price": 20.00,
        "track_inventory": True, "category": "测试",
    }
    payload.update(overrides)
    resp = client.post("/api/products", json=payload, headers=headers)
    assert resp.status_code in (200, 201), f"创建商品失败: {resp.text}"
    return get_entity_id(resp.json()), resp.json()

def api_create_customer(client, headers, **overrides):
    tag = uniq("FC")
    payload = {
        "name": f"工厂客户-{tag}", "contact": "测试", "phone": f"138{tag[:8]}",
    }
    payload.update(overrides)
    resp = client.post("/api/customers", json=payload, headers=headers)
    assert resp.status_code in (200, 201), f"创建客户失败: {resp.text}"
    return get_entity_id(resp.json()), resp.json()

def api_create_supplier(client, headers, **overrides):
    tag = uniq("FS")
    payload = {
        "name": f"工厂供应商-{tag}", "contact": "测试", "phone": f"139{tag[:8]}",
    }
    payload.update(overrides)
    resp = client.post("/api/suppliers", json=payload, headers=headers)
    assert resp.status_code in (200, 201), f"创建供应商失败: {resp.text}"
    return get_entity_id(resp.json()), resp.json()

def api_create_product_and_purchase(client, headers, product_id, qty=10, unit_price=10.00):
    """创建采购单并完成入库"""
    tag = uniq("PO")
    resp = client.post("/api/purchases", json={
        "order_no": f"PO-{tag}", "supplier_id": 1,
        "items": [{"product_id": product_id, "quantity": qty, "unit_price": unit_price}],
        "order_date": datetime.now().strftime("%Y-%m-%d"),
    }, headers=headers)
    assert resp.status_code in (200, 201), f"创建采购单失败: {resp.text}"
    purchase_id = get_entity_id(resp.json())

    # 入库
    resp = client.post(f"/api/purchases/{purchase_id}/receive", json={}, headers=headers)
    assert resp.status_code in (200, 201), f"采购入库失败: {resp.text}"
    return purchase_id

def api_create_sale(client, headers, product_id, customer_id, qty=1, unit_price=20.00, has_invoice=False):
    tag = uniq("SO")
    resp = client.post("/api/sales", json={
        "order_no": f"SO-{tag}", "customer_id": customer_id,
        "items": [{"product_id": product_id, "quantity": qty, "unit_price": unit_price}],
        "order_date": datetime.now().strftime("%Y-%m-%d"),
        "has_invoice": has_invoice,
    }, headers=headers)
    assert resp.status_code in (200, 201), f"创建销售单失败: {resp.text}"
    return get_entity_id(resp.json()), resp.json()
