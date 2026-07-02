"""6月业务 + 银行对账 — 完整数据变化时间轴"""
import sys,os;sys.path.insert(0,os.path.join(os.path.dirname(__file__),"..","backend"))
import uuid,calendar
from datetime import datetime,date
from decimal import Decimal

from sqlalchemy import create_engine;from sqlalchemy.orm import sessionmaker
from database import Base;_request_write_perm=__import__('database')._request_write_perm
_request_write_perm.set(True)
import models,models_finance,models_bank

e=create_engine("sqlite:///:memory:")
Base.metadata.create_all(bind=e)
S=sessionmaker(bind=e)
db=S()

acc=models.Account(name="6M全流程",code=f"F6{uuid.uuid4().hex[:4]}",taxpayer_type_l3="general")
db.add(acc);db.flush();aid=acc.id;acc_code=acc.code
from finance_integration import get_or_create_ledger_id;lid=get_or_create_ledger_id(db,aid)
bank=models.BankAccount(account_id=aid,bank_name="工商银行",account_number="6222",balance_l4=0)
db.add(bank);db.flush();baid=bank.id
cust=models.Customer(account_id=aid,name="客户",contact="C",phone="13900000001")
db.add(cust);db.flush();cid=cust.id

from models_finance import LedgerAccount,AccountMove,AccountMoveLine,LedgerAccountBalance
ac=db.query(LedgerAccount).filter(LedgerAccount.ledger_id==lid,LedgerAccount.code=="1002").first()
m=AccountMove(ledger_id=lid,move_type="bank",date_l1=datetime(2024,12,31,23,59,59),state="posted")
db.add(m);db.flush()
db.add(AccountMoveLine(move_id=m.id,ledger_account_id=ac.id,debit_l2=10000,credit_l2=0,amount_residual_l2=10000))
bal=db.query(LedgerAccountBalance).filter(LedgerAccountBalance.ledger_account_id==ac.id).first()
if bal:bal.balance_l4=10000;bal.debit_total_l4=10000
db.commit()

def book_bal(period):
    y,m=int(period[:4]),int(period[5:7])
    _,ld=calendar.monthrange(y,m)
    return sum(Decimal(str(l.debit_l2))-Decimal(str(l.credit_l2)) for l in db.query(AccountMoveLine).join(AccountMove).filter(
        AccountMoveLine.ledger_account_id==ac.id,AccountMove.date<=datetime(y,m,ld,23,59,59)).all())

def post_tx(baid,aid,amt,dr,dt):
    tx=models.BankTransaction(bank_account_id=baid,account_id=aid,amount_l1=amt,
        transaction_type="inflow" if dr=="in" else "outflow",transaction_date_l1=dt,
        description=f"test{amt}",balance_after_l4=Decimal(str(amt)) if dr=="in" else Decimal("0"))
    db.add(tx);db.flush()
    ba=db.query(models.BankAccount).filter(models.BankAccount.id==baid).first()
    if ba:ba.balance_l4+=(Decimal(str(amt)) if dr=="in" else -Decimal(str(amt)))
    m2=AccountMove(ledger_id=lid,move_type="bank",date_l1=dt,state="posted")
    db.add(m2);db.flush()
    db2=Decimal(str(amt)) if dr=="in" else 0;cr2=0 if dr=="in" else Decimal(str(amt))
    db.add(AccountMoveLine(move_id=m2.id,ledger_account_id=ac.id,debit_l2=db2,credit_l2=cr2,amount_residual_l2=db2 or cr2))
    b=db.query(LedgerAccountBalance).filter(LedgerAccountBalance.ledger_account_id==ac.id).first()
    if b:b.balance_l4+=(db2-cr2);b.debit_total_l4+=db2;b.credit_total_l4+=cr2
    db.flush();return tx

from engine_bank_reconcile import BankReconcileEngine

MONTHS=[
    ("2025-01",500,"2025-01-06",200,"2025-01-11",15,"2025-01-15"),
    ("2025-02",800,"2025-02-07",300,"2025-02-12",15,"2025-02-15"),
    ("2025-03",600,"2025-03-05",250,"2025-03-10",15,"2025-03-15"),
    ("2025-04",900,"2025-04-06",400,"2025-04-11",15,"2025-04-15"),
    ("2025-05",700,"2025-05-07",350,"2025-05-12",15,"2025-05-15"),
    ("2025-06",1000,"2025-06-05",500,"2025-06-10",15,"2025-06-15"),
]

print(f"{'月份':<8}{'操作':>8}{'金额':>8}{'日期':>12}{'账面余额':>10}{'对账余额':>10}{'匹配':>4}{'未达':>4}{'平衡':>6}")
print("-"*80)

for period,rev,rdt,exp,edt,fee,fdt in MONTHS:
    y,m=int(period[:4]),int(period[5:7])
    
    # 收款 → BankTransaction + 1002
    tx=post_tx(baid,aid,rev,"in",datetime.strptime(rdt+"T10:00:00","%Y-%m-%dT%H:%M:%S"))
    bb=float(book_bal(period))
    print(f"{period:<8}{'收款':>8}{rev:>8}{rdt:>12}{bb:>10.0f}{'':>10}{'':>4}{'':>4}{'':>6}")

    # 费用 → 不生成 BankTransaction (走应付,但会在对账单体现)
    print(f"{period:<8}{'费用':>8}{exp:>8}{edt:>12}{bb:>10.0f}{'':>10}{'':>4}{'':>4}{'':>6}")
    
    # 导入对账单
    stmt=models_bank.BankStatement(bank_account_id=baid,account_id=aid,
        period_start=date(y,m,1),period_end=date(y,m,28),
        opening_balance_l1=Decimal(str(bb)),closing_balance_l1=Decimal(str(bb+rev-exp-fee)))
    db.add(stmt);db.flush()
    db.add(models_bank.BankStatementLine(statement_id=stmt.id,transaction_date_l1=datetime.strptime(rdt,"%Y-%m-%d").date(),amount_l1=rev))
    db.add(models_bank.BankStatementLine(statement_id=stmt.id,transaction_date_l1=datetime.strptime(edt,"%Y-%m-%d").date(),amount_l1=-exp))
    db.add(models_bank.BankStatementLine(statement_id=stmt.id,transaction_date_l1=datetime.strptime(fdt,"%Y-%m-%d").date(),amount_l1=-fee,description="账户管理费"))
    db.commit()
    
    # 对账
    e2=BankReconcileEngine(db,aid,baid,period)
    rec=e2.create_reconciliation([])
    e2.run_matching()
    db.commit()
    
    items=db.query(models_bank.ReconciliationItem).filter(models_bank.ReconciliationItem.reconciliation_id==rec.id).all()
    matched=sum(1 for i in items if i.resolved)
    unmatched=sum(1 for i in items if not i.resolved)
    sb=float(rec.statement_balance)
    
    print(f"{period:<8}{'对账':>8}{'':>8}{'':>12}{bb:>10.0f}{sb:>10.0f}{matched:>4}{unmatched:>4}{str(rec.balanced):>6}")

    # 确认 (只有平衡时)
    if rec.balanced:
        e2.confirm(rec.id,"admin")
        print(f"{period:<8}{'确认':>8}{'':>8}{'':>12}{'':>10}{'':>10}{'':>4}{'':>4}{'confirmed':>6}")

print(f"\n{'='*70}")
print(f"  历史对账汇总")
print(f"{'='*70}")
for period,_,_,_,_,_,_ in MONTHS:
    y,m=int(period[:4]),int(period[5:7])
    rec=db.query(models_bank.BankReconciliation).filter(
        models_bank.BankReconciliation.bank_account_id==baid,
        models_bank.BankReconciliation.period==period).first()
    if rec:
        items=db.query(models_bank.ReconciliationItem).filter(
            models_bank.ReconciliationItem.reconciliation_id==rec.id).all()
        print(f"  {period}: book={rec.book_balance} stmt={rec.statement_balance} "
              f"adjBook={rec.adjusted_book} adjStmt={rec.adjusted_statement} "
              f"balanced={rec.balanced} status={rec.status}")
        for it in items:
            print(f"    [{it.item_type}] {it.direction} {it.amount} resolved={it.resolved} action={it.action}")

db.close()
