import sys,os;sys.path.insert(0,'backend')
import uuid,tempfile
from datetime import datetime,date
from decimal import Decimal
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from database import Base,get_db,_request_write_perm
import models,models_finance
_request_write_perm.set(True)

db_path = os.path.join(tempfile.gettempdir(),f'db_{uuid.uuid4().hex}.db')
e=create_engine(f'sqlite:///{db_path}',connect_args={'check_same_thread':False})
Base.metadata.create_all(bind=e)
TS=sessionmaker(bind=e,autocommit=False,autoflush=False)
def _o():
    s=TS()
    try: yield s
    finally: s.close()

from main import app
app.dependency_overrides[get_db]=_o
from fastapi.testclient import TestClient
c=TestClient(app)

s=TS()
acc=models.Account(name='X',code=f'D{uuid.uuid4().hex[:4]}',taxpayer_type_l3='general')
s.add(acc);s.flush();aid=acc.id
from finance_integration import get_or_create_ledger_id;lid=get_or_create_ledger_id(s,aid)
ba=models.BankAccount(account_id=aid,bank_name='X',account_number='6222',balance_l4=3000)
s.add(ba);s.flush();baid=ba.id

from models_finance import LedgerAccount,AccountMove,AccountMoveLine,LedgerAccountBalance
ac=s.query(LedgerAccount).filter(LedgerAccount.ledger_id==lid,LedgerAccount.code=='1002').first()
m=AccountMove(ledger_id=lid,move_type='bank',date_l1=datetime(2024,12,31,23,59,59),state='posted')
s.add(m);s.flush()
s.add(AccountMoveLine(move_id=m.id,ledger_account_id=ac.id,debit_l2=3000,credit_l2=0,amount_residual_l2=3000))
bal=s.query(LedgerAccountBalance).filter(LedgerAccountBalance.ledger_account_id==ac.id).first()
if bal:bal.balance_l4=3000;bal.debit_total_l4=3000
tx=models.BankTransaction(bank_account_id=baid,account_id=aid,amount_l2=500,transaction_type='inflow',transaction_date_l1=date(2025,1,5),description='t500',balance_after_l4=500)
s.add(tx);s.commit();s.close()

h={'X-Account-ID':str(aid),'X-Operator':'user'}
r=c.post('/api/bank/statement',headers=h,json={'period_start':'2025-01-01','period_end':'2025-01-31','opening_balance':3000,'closing_balance':3500,'lines':[{'transaction_date':'2025-01-05','amount':500,'description':'收款'}]})
print('stmt:',r.status_code,r.json())
r=c.post('/api/bank/reconcile',headers=h,params={'period':'2025-01'})
print('rec:',r.status_code)
import json;print(json.dumps(r.json(),indent=2,default=str))
os.unlink(db_path)
