"""诊断 AS-04：销售单创建后是否生成凭证"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "backend"))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "tests"))

import workspace
workspace.ensure_workspace()

from database import set_maintenance_mode, SessionLocal
set_maintenance_mode(True)

from fastapi.testclient import TestClient
from main import app
from tests.factories import api_create_customer
from tests.helpers import make_headers
from models_finance import AccountMoveLine, LedgerAccount
from models import SaleOrder, Account

client = TestClient(app)
headers = make_headers()

# 确保 account 1 存在且为一般纳税人（与失败测试一致）
from finance_integration import CHART_OF_ACCOUNTS
db = SessionLocal()
try:
    acc = db.query(Account).filter(Account.id == 1).first()
    if not acc:
        acc = Account(id=1, name="测试账本", code="test", type="company", taxpayer_type_l3="general")
        db.add(acc)
        db.flush()
    acc.taxpayer_type_l3 = "general"
    from models_finance import Ledger, LedgerAccount, LedgerAccountBalance
    ledger = db.query(Ledger).filter(Ledger.code == acc.code).first()
    if not ledger:
        ledger = Ledger(code=acc.code, name=acc.name, type=acc.type or "company", taxpayer_type_l3=acc.taxpayer_type_l3 or "general")
        db.add(ledger)
        db.flush()
        for code, name, atype in CHART_OF_ACCOUNTS:
            la = LedgerAccount(ledger_id=ledger.id, code=code, name=name, account_type=atype, is_leaf=True, is_active=True)
            db.add(la)
            db.flush()
            db.add(LedgerAccountBalance(ledger_account_id=la.id, balance_l4=0, debit_total_l4=0, credit_total_l4=0))
    db.commit()
finally:
    db.close()

# 创建测试商品
from test_helpers import ensure_test_product
pid = ensure_test_product(1, min_stock=1000)

# 创建客户
cid, _ = api_create_customer(client, headers)

# 检查事件处理器是否注册
from events import get_handlers
print("sale_order.created handlers:", [h.name for h in get_handlers("sale_order.created")])

# 创建销售单
resp = client.post("/api/sales", json={
    "customer_id": cid,
    "has_invoice": True,
    "deduct_inventory": True,
    "payment_status": "unpaid",
    "business_date": "2026-06-15T10:00:00",
    "items": [{"product_id": pid, "quantity": 2, "unit_price": 100, "tax_rate": 0.01}],
}, headers=headers)
print("create sale status:", resp.status_code)
print("create sale body:", resp.text[:500])

if resp.status_code in (200, 201):
    order_id = resp.json()["data"]["id"]
    db = SessionLocal()
    try:
        order = db.query(SaleOrder).filter(SaleOrder.id == order_id).first()
        print("order total_price:", order.total_price_l1 if order else None)
        print("order items count:", len(order.items) if order else None)
        for it in order.items:
            print(f"  item: qty={it.quantity_l1}, unit_price={it.unit_price_l1}, total={it.total_price_l1}, unit_cost={it.unit_cost_l2}")
        la_6001 = db.query(LedgerAccount).filter(LedgerAccount.code == "6001").first()
        if la_6001:
            lines = db.query(AccountMoveLine).filter(
                AccountMoveLine.ledger_account_id == la_6001.id
            ).all()
            print("6001 move lines:", len(lines))
            for l in lines:
                print(f"  move_id={l.move_id}, credit={l.credit_l2}, debit={l.debit_l2}")
        else:
            print("6001 ledger account not found")
    finally:
        db.close()
else:
    print("sale creation failed")

set_maintenance_mode(False)
