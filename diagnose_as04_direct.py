"""直接调用 CreateOrder，观察事件处理与凭证生成"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "backend"))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "tests"))

import workspace
workspace.ensure_workspace()

from database import set_maintenance_mode, SessionLocal
set_maintenance_mode(True)

from decimal import Decimal
from models import Account, SaleOrder
from models_finance import AccountMoveLine, LedgerAccount
from finance_integration import CHART_OF_ACCOUNTS

# 初始化 account/ledger/accounts
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
        ledger = Ledger(code=acc.code, name=acc.name, type=acc.type or "company", taxpayer_type_l3=acc.taxpayer_type_l3)
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

# 初始化商品库存
from test_helpers import ensure_test_product
pid = ensure_test_product(1, min_stock=1000)

# 创建客户
from fastapi.testclient import TestClient
from main import app
from tests.factories import api_create_customer
from tests.helpers import make_headers
client = TestClient(app)
headers = make_headers()
cid, _ = api_create_customer(client, headers)

# 检查事件处理器注册
from events import get_handlers
print("sale_order.created handlers:", [h.name for h in get_handlers("sale_order.created")])

# 直接调用 CreateOrder
db = SessionLocal()
try:
    from commands.orders import CreateOrder
    from commands.base import dispatch
    cmd = CreateOrder(
        order_type="sale",
        account_id=1,
        operator="user",
        customer_id=cid,
        business_date="2026-06-15T10:00:00",
        items=[{"product_id": pid, "quantity_l1": 2, "unit_price_l1": 100, "tax_rate_l1": 0.01}],
        has_invoice=True,
        deduct_inventory=True,
        payment_status="unpaid",
    )
    try:
        order = dispatch(cmd, db)
        print("order created:", order.id, order.total_price_l1, order.tax_amount_l1)
        db.commit()
    except Exception as e:
        print("dispatch exception:", type(e).__name__, e)
        db.rollback()
        raise
finally:
    db.close()

# 查询凭证
db = SessionLocal()
try:
    order = db.query(SaleOrder).order_by(SaleOrder.id.desc()).first()
    print("latest order:", order.id if order else None)
    la_6001 = db.query(LedgerAccount).filter(LedgerAccount.code == "6001").first()
    if la_6001:
        lines = db.query(AccountMoveLine).filter(
            AccountMoveLine.ledger_account_id == la_6001.id
        ).all()
        print("6001 move lines:", len(lines))
        for l in lines:
            print(f"  move_id={l.move_id}, credit={l.credit_l2}, debit={l.debit_l2}")
    else:
        print("6001 not found")
finally:
    db.close()

set_maintenance_mode(False)
