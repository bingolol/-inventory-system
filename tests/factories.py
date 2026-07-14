"""Test data factories — 创建测试数据的辅助工具

用法:
  集成测试 (API):   factories.create_product(client, headers)
  单元测试 (DB):    factories.make_product(db, account_id)
"""
import uuid
from datetime import datetime, timedelta
from decimal import Decimal

from tests.helpers import get_entity_id, uniq


# ── DB-level factories (unit tests) ──

def ensure_default_account(db, account_id=1):
    """确保默认账本 Account + Ledger + LedgerAccount 存在（临时数据库 setup 后调用）"""
    import models
    import models_finance
    import models_bank
    from database import Base
    from models import Account
    from models_finance import Ledger, LedgerAccount, LedgerAccountBalance
    from finance_integration import CHART_OF_ACCOUNTS

    # 补救：确保表已创建（防止 create_all 在 models 导入前执行）
    Base.metadata.create_all(bind=db.get_bind())

    acc = db.query(Account).filter(Account.id == account_id).first()
    if not acc:
        acc = Account(id=account_id, name="测试账本", code="test",
                      type="company", taxpayer_type_l3="small_scale")
        db.add(acc)
        db.flush()
    ledger = db.query(Ledger).filter(Ledger.code == acc.code).first()
    if not ledger:
        ledger = Ledger(code=acc.code, name=acc.name, type=acc.type or "company",
                        taxpayer_type_l3=acc.taxpayer_type_l3 or "small_scale")
        db.add(ledger)
        db.flush()
        for code, name, atype in CHART_OF_ACCOUNTS:
            la = LedgerAccount(ledger_id=ledger.id, code=code, name=name,
                               account_type=atype, is_leaf=True, is_active=True)
            db.add(la)
            db.flush()
            db.add(LedgerAccountBalance(ledger_account_id=la.id, balance_l4=0,
                                        debit_total_l4=0, credit_total_l4=0))
    db.commit()
    return acc

def make_account(db, name="测试账本"):
    from models import Account
    tag = uuid.uuid4().hex[:8]
    acc = Account(name=name, code=f"TEST-{tag}", taxpayer_type_l3="small_scale")
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
        purchase_price_l3=purchase_price,
        sale_price_l3=sale_price,
        track_inventory_l3=track_inventory,
        category="测试",
    )
    db.add(p)
    db.flush()
    return p

def make_customer(db, account_id, name=None):
    tag = uuid.uuid4().hex[:8]
    from models import Customer
    p = Customer(
        account_id=account_id,
        name=name or f"客户-{tag}",
        contact="测试", phone=f"138{tag[:8]}",
    )
    db.add(p)
    db.flush()
    return p

def make_supplier(db, account_id, name=None):
    tag = uuid.uuid4().hex[:8]
    from models import Supplier
    p = Supplier(
        account_id=account_id,
        name=name or f"供应商-{tag}",
        contact="测试", phone=f"139{tag[:8]}",
    )
    db.add(p)
    db.flush()
    return p

def make_stock_move(db, product_id, qty, unit_cost, move_type="inbound", source_type="purchase", ref_id=None):
    from models import StockMove
    sm = StockMove(
        product_id=product_id, quantity_l1=qty, unit_cost_l2=unit_cost,
        move_type=move_type, source_type=source_type, reference_id=ref_id,
    )
    db.add(sm)
    db.flush()
    return sm

def make_bank_account(db, account_id, name=None, balance=Decimal("100000")):
    tag = uuid.uuid4().hex[:8]
    from models import BankAccount, BankTransaction
    from datetime import date
    ba = BankAccount(
        account_id=account_id,
        name=name or f"银行账户-{tag}",
        account_number=f"6222{tag[:12]}",
        balance_l4=balance,
    )
    db.add(ba)
    db.flush()
    if balance > 0:
        db.add(BankTransaction(
            account_id=account_id,
            bank_account_id=ba.id,
            transaction_type="inflow",
            amount_l2=balance,
            balance_after_l4=balance,
            transaction_date_l1=date.today(),
            description="期初余额",
            flow_category="operating",
        ))
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

def api_create_product_and_purchase(client, headers, product_id, qty=10, unit_price=10.00,
                                    tax_rate=0.13):
    """创建采购单并完成入库"""
    tag = uniq("PO")
    now_str = datetime.now().strftime("%Y-%m-%d")
    resp = client.post("/api/purchases", json={
        "order_no": f"PO-{tag}", "supplier_id": 1,
        "items": [{"product_id": product_id, "quantity": qty, "unit_price": unit_price, "tax_rate": tax_rate}],
        "business_date": now_str,
    }, headers=headers)
    assert resp.status_code in (200, 201), f"创建采购单失败: {resp.text}"
    purchase_id = get_entity_id(resp.json())

    # 入库
    resp = client.post(f"/api/purchases/{purchase_id}/receive", json={}, headers=headers)
    assert resp.status_code in (200, 201), f"采购入库失败: {resp.text}"
    return purchase_id

def api_create_sale(client, headers, product_id, customer_id, qty=1, unit_price=20.00,
                    tax_rate=0.03, has_invoice=False, business_date=None, **extra):
    """创建销售单（发票驱动：通过 /api/invoices/quick 创建销项发票，自动生成销售单）

    架构改造后 POST /api/sales 已停用，所有销售单必须由发票驱动创建。
    has_invoice 参数已废弃（恒为 True）。
    unit_price 为不含税单价。
    """
    from decimal import Decimal as _D
    tag = uniq("SO")
    now_str = business_date or datetime.now().strftime("%Y-%m-%d")
    atw = _D(str(qty)) * _D(str(unit_price)) * (1 + _D(str(tax_rate)))
    awt = _D(str(qty)) * _D(str(unit_price))
    tax_amt = atw - awt
    payload = {
        "invoice_no": f"INV-OUT-{tag}", "direction": "out", "invoice_type": "ordinary",
        "amount_with_tax": str(atw.quantize(_D("0.01"))),
        "tax_rate": str(tax_rate), "tax_amount": str(tax_amt.quantize(_D("0.01"))),
        "counterparty_name": "测试客户", "seller_name": "本公司", "buyer_name": "测试客户",
        "issue_date": now_str, "sale_order_action": "auto_create",
        "items": [{"product_id": product_id, "quantity": qty, "unit_price": str(unit_price), "tax_rate": str(tax_rate)}],
    }
    payload.update(extra)
    resp = client.post("/api/invoices/quick", json=payload, headers=headers)
    assert resp.status_code in (200, 201), f"创建销售单(发票驱动)失败: {resp.text}"
    rj = resp.json()
    order_id = _extract_related_order_id(rj)
    return order_id, rj


def api_create_purchase(client, headers, product_id, supplier_id, qty=1, unit_price=10.00,
                        tax_rate=0.03, business_date=None, **extra):
    """创建采购单（发票驱动：通过 /api/invoices/quick 创建进项发票，自动生成采购单）

    架构改造后 POST /api/purchases 已停用，所有采购单必须由发票驱动创建。
    unit_price 为不含税单价。
    """
    from decimal import Decimal as _D
    tag = uniq("PO")
    now_str = business_date or datetime.now().strftime("%Y-%m-%d")
    atw = _D(str(qty)) * _D(str(unit_price)) * (1 + _D(str(tax_rate)))
    awt = _D(str(qty)) * _D(str(unit_price))
    tax_amt = atw - awt
    payload = {
        "invoice_no": f"INV-IN-{tag}", "direction": "in", "invoice_type": "ordinary",
        "amount_with_tax": str(atw.quantize(_D("0.01"))),
        "tax_rate": str(tax_rate), "tax_amount": str(tax_amt.quantize(_D("0.01"))),
        "counterparty_name": "测试供应商", "seller_name": "测试供应商", "buyer_name": "本公司",
        "issue_date": now_str, "purchase_order_action": "auto_create",
        "items": [{"product_id": product_id, "quantity": qty, "unit_price": str(unit_price), "tax_rate": str(tax_rate)}],
    }
    payload.update(extra)
    resp = client.post("/api/invoices/quick", json=payload, headers=headers)
    assert resp.status_code in (200, 201), f"创建采购单(发票驱动)失败: {resp.text}"
    rj = resp.json()
    order_id = _extract_related_order_id(rj)
    return order_id, rj


def _extract_related_order_id(resp_json):
    """从发票 API 响应中提取 related_order_id（兼容多种响应格式）"""
    # OperationResult 格式: {"data": {"related_order_id": ...}}
    data = resp_json
    if isinstance(data, dict) and "data" in data and isinstance(data["data"], dict):
        data = data["data"]
    # AI Gateway 格式: {"ok": true, "entity": {"data": {...}}}
    if isinstance(data, dict) and "entity" in data and isinstance(data["entity"], dict):
        data = data["entity"]
        if "data" in data and isinstance(data["data"], dict):
            data = data["data"]
    if isinstance(data, dict) and "related_order_id" in data:
        return data["related_order_id"]
    # fallback: get_entity_id
    return get_entity_id(resp_json)


def api_create_invoice_quick(client, headers, product_id, invoice_no=None, direction="in",
                             invoice_type="ordinary", amount_with_tax="113.00", tax_rate="0.03",
                             tax_amount=None, issue_date="2026-06-15", items=None, **extra):
    inv_no = invoice_no or uniq("INV")
    default_items = items or [
        {"product_id": product_id, "quantity": 1, "unit_price": "100.00", "tax_rate": tax_rate}
    ]
    if tax_amount is None and "tax_amount" not in extra:
        atw = Decimal(str(amount_with_tax))
        tr = Decimal(str(tax_rate))
        tax_amount = str(round2(atw - (atw / (Decimal("1") + tr))))
    payload = {
        "invoice_no": inv_no, "direction": direction, "invoice_type": invoice_type,
        "amount_with_tax": amount_with_tax, "tax_rate": tax_rate,
        "tax_amount": tax_amount,
        "counterparty_name": "测试往来方", "seller_name": "本公司", "buyer_name": "测试往来方",
        "issue_date": issue_date, "items": default_items,
    }
    payload.update(extra)
    resp = client.post("/api/invoices/quick", json=payload, headers=headers)
    assert resp.status_code in (200, 201), f"创建发票失败: {resp.text}"
    return get_entity_id(resp.json()), resp.json()
