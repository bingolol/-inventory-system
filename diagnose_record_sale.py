"""直接调用 FinanceEngine.record_sale，观察是否生成凭证"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "backend"))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "tests"))

import workspace
workspace.ensure_workspace()

from database import set_maintenance_mode, SessionLocal
set_maintenance_mode(True)

from decimal import Decimal
from models import Account, SaleOrder, SaleItem
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

# 直接创建销售单（不触发事件），然后手动调用 record_sale
db = SessionLocal()
try:
    from commands.orders import CreateOrder
    from commands.base import dispatch
    # 先创建一个测试用的销售单，但跳过事件处理：我们手动插入
    from datetime import datetime
    order = SaleOrder(
        account_id=1,
        order_no="TEST-DIAG-001",
        customer_id=cid,
        order_type="retail",
        payment_status="unpaid",
        has_invoice_l1=True,
        status="completed",
        total_price_l1=Decimal("202.00"),
        tax_amount_l1=Decimal("2.00"),
        sale_date_l1=datetime(2026, 6, 15),
    )
    db.add(order)
    db.flush()
    item = SaleItem(
        order_id=order.id,
        product_id=pid,
        quantity_l1=2,
        unit_price_l1=Decimal("100"),
        tax_rate_l1=Decimal("0.01"),
        total_price_l1=Decimal("200"),
        unit_cost_l2=Decimal("10"),
    )
    db.add(item)
    db.flush()
    db.refresh(order)
    print("manual order:", order.id, order.total_price_l1, order.tax_amount_l1)
    print("items:", len(order.items))

    # 调用 FinanceEngine.record_sale
    from engine_finance import FinanceEngine
    try:
        move = FinanceEngine(db, 1).record_sale(order)
        print("record_sale returned move:", move.id if move else None)
        db.commit()
    except Exception as e:
        print("record_sale exception:", type(e).__name__, e)
        import traceback
        traceback.print_exc()
        db.rollback()
finally:
    db.close()

# 查询凭证
db = SessionLocal()
try:
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
