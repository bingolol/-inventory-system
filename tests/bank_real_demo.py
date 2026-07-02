"""银行对账 — 真实业务流程演示"""
import sys,os;sys.path.insert(0,os.path.join(os.path.dirname(__file__),"..","backend"))
import json,uuid,tempfile
from datetime import datetime,date
from decimal import Decimal

_db_path=os.path.join(tempfile.gettempdir(),f"bank_{uuid.uuid4().hex}.db")
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from database import Base,get_db,_request_write_perm
_request_write_perm.set(True)
import models,models_finance,models_bank

engine=create_engine(f"sqlite:///{_db_path}",connect_args={"check_same_thread":False})
Base.metadata.create_all(bind=engine)
TS=sessionmaker(bind=engine,autocommit=False,autoflush=False)
def _o():
    s=TS()
    try:
        yield s
    finally:
        s.close()

from account_dep import get_account_id
from main import app
app.dependency_overrides[get_db]=_o
async def _fake():return 1
app.dependency_overrides[get_account_id]=_fake
from fastapi.testclient import TestClient
c=TestClient(app);H={"X-Account-ID":"1","X-Operator":"user"}

# ========= 1. 建账套 + 银行账户 + 期初 =========
s=TS()
acc=models.Account(name="真实业务",code=f"R{uuid.uuid4().hex[:4]}",taxpayer_type_l3="general")
s.add(acc);s.flush();aid=acc.id
from finance_integration import get_or_create_ledger_id;lid=get_or_create_ledger_id(s,aid)
supp=models.Supplier(account_id=aid,name="供应商A",contact="A",phone="13800000001")
cust=models.Customer(account_id=aid,name="客户B",contact="B",phone="13900000002")
prod=models.Product(account_id=aid,name="商品X",sku=f"SKU{uuid.uuid4().hex[:4]}",unit="个",
    purchase_price_l3=10,sale_price_l3=20,track_inventory_l3=False,category="测试")
bank=models.BankAccount(account_id=aid,bank_name="工商银行",account_number="6222021234567890",balance_l4=10000)
s.add_all([supp,cust,prod,bank]);s.flush()
ba_id=bank.id;cust_id=cust.id;prod_id=prod.id

from models_finance import LedgerAccount,AccountMove,AccountMoveLine,LedgerAccountBalance
ac=s.query(LedgerAccount).filter(LedgerAccount.ledger_id==lid,LedgerAccount.code=="1002").first()
m=AccountMove(ledger_id=lid,move_type="bank",date_l1=datetime(2024,12,31,23,59,59),state="posted")
s.add(m);s.flush()
s.add(AccountMoveLine(move_id=m.id,ledger_account_id=ac.id,debit_l2=10000,credit_l2=0,amount_residual_l2=10000))
bal=s.query(LedgerAccountBalance).filter(LedgerAccountBalance.ledger_account_id==ac.id).first()
if bal:bal.balance_l4=10000;bal.debit_total_l4=10000

sale=models.SaleOrder(account_id=aid,customer_id=cust_id,order_no=f"SO-{uuid.uuid4().hex[:4]}",
    total_price_l1=500,status="completed",payment_status="paid",sale_date_l1=date(2025,1,3))
s.add(sale);s.flush();s.add(models.SaleItem(order_id=sale.id,product_id=prod_id,quantity_l1=5,unit_price_l1=100,tax_rate_l1=0,total_price_l1=500))
sale_id=sale.id
s.commit();s.close()

# ========= 2. 真实业务 API: 收款 500 =========
r=c.post("/api/receipts",headers=H,json={
    "receipt_type":"sale","amount":500,"receipt_date":"2025-01-05T10:00:00",
    "receipt_method":"company","related_entity_type":"sale_order",
    "related_entity_id":sale_id,"bank_account_id":ba_id,"description":"客户B货款",
})
print(f"[收款API] {r.status_code}",json.dumps(r.json(),ensure_ascii=False,default=str)[:200] if r.status_code==200 else r.text[:200])

# ========= 3. 真实业务 API: 费用 200 =========
r=c.post("/api/expenses",headers=H,json={
    "amount":200,"expense_date":"2025-01-10","category":"办公用品",
    "functional_category":"管理费用","payment_method":"company",
    "bank_account_id":ba_id,"description":"办公用品",
})
print(f"[费用API] {r.status_code}",json.dumps(r.json(),ensure_ascii=False,default=str)[:200] if r.status_code==200 else r.text[:200])

# ========= 4. 查看系统流水 =========
s=TS()
txs=s.query(models.BankTransaction).filter(
    models.BankTransaction.account_id==aid,models.BankTransaction.bank_account_id==ba_id).all()
print(f"\n系统BankTransaction ({len(txs)}笔):")
for tx in txs:
    print(f"  #{tx.id} {tx.transaction_type} {tx.amount_l2} @ {tx.transaction_date_l1} bal_after={tx.balance_after_l4}")
s.close()

# ========= 5. 导入对账单 =========
r=c.post("/api/bank/statement",headers=H,json={
    "period_start":"2025-01-01","period_end":"2025-01-31",
    "opening_balance":10000,"closing_balance":10285,
    "lines":[
        {"transaction_date":"2025-01-06","amount":500,"description":"货款到账"},
        {"transaction_date":"2025-01-11","amount":-200,"description":"办公用品扣款"},
        {"transaction_date":"2025-01-15","amount":-15,"description":"账户管理费"},
    ],
})
print(f"\n[导入对账单] {r.status_code} stmt_id={r.json().get('id') if r.status_code==200 else r.text[:100]}")

# ========= 6. 执行对账 =========
r=c.post("/api/bank/reconcile",headers=H,params={"period":"2025-01"})
print(f"\n[对账结果] {r.status_code}")
if r.status_code==200:
    rec=r.json()
    print(f"  账面余额: {rec['book_balance']}")
    print(f"  对账单余额: {rec['statement_balance']}")
    print(f"  调节后账面: {rec['adjusted_book']}  调节后对账单: {rec['adjusted_statement']}")
    print(f"  平衡: {rec['balanced']}")

# ========= 7. 调节表明细 =========
r=c.get("/api/bank/reconciliation",headers=H,params={"period":"2025-01"})
print(f"\n[调节表明细] {r.status_code}")
if r.status_code==200:
    d=r.json()
    for it in d.get("items",[]):
        print(f"  [{it['item_type']}] dir={it['direction']} amt={it['amount']} resolved={it['resolved']} action={it['action']}")

try:import os as _os;_os.unlink(_db_path)
except:pass
