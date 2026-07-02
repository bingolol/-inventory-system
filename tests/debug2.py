import sys,os
sys.path.insert(0,'backend')
import tempfile,uuid,models,models_finance,models_bank
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from database import Base,get_db,_request_write_perm
from datetime import datetime,date
from decimal import Decimal

_request_write_perm.set(True)
db_path=os.path.join(tempfile.gettempdir(),f'a{uuid.uuid4().hex}.db')
e=create_engine(f'sqlite:///{db_path}',connect_args={'check_same_thread':False})

print("Tables before create_all:",sorted(Base.metadata.tables.keys()))
Base.metadata.create_all(bind=e)

TS=sessionmaker(bind=e,autocommit=False,autoflush=False)
def _o():
    s=TS()
    try:yield s
    finally:s.close()

from main import app
app.dependency_overrides[get_db]=_o
app.dependency_overrides[__import__('account_dep').get_account_id]=lambda:1
from fastapi.testclient import TestClient
c=TestClient(app)

s=TS()
acc=models.Account(name='X',code=f'A{uuid.uuid4().hex[:4]}',taxpayer_type_l3='general')
s.add(acc);s.flush();aid=acc.id
from finance_integration import get_or_create_ledger_id
get_or_create_ledger_id(s,aid)
ba=models.BankAccount(account_id=aid,bank_name='X',account_number='6222',balance_l4=0)
s.add(ba);s.flush();baid=ba.id
s.commit();s.close()

h={'X-Account-ID':'1','X-Operator':'user'}
r=c.post('/api/bank/statement',headers=h,json={
    'period_start':'2025-01-01','period_end':'2025-01-31',
    'opening_balance':3000,'closing_balance':3500,
    'lines':[{'transaction_date':'2025-01-05','amount':500,'description':'收款'}]
})
print('stmt:',r.status_code)
if r.status_code==200:
    stmt_id=r.json()['id']
    r=c.post('/api/bank/reconcile',headers=h,params={'period':'2025-01'})
    print('rec:',r.status_code, r.json() if r.status_code==200 else r.text[:200])

os.unlink(db_path)
