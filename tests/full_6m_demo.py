"""
星辰科技 2025年上半年真实经营流程
一般纳税人 | 软件开发+硬件销售
期初: 银行存款 100,000 = 实收资本 100,000
每月: 采购→销售→出库→工资→房租→水电→收款→付款→月结→银行对账→税务核对
"""
import sys,os;sys.path.insert(0,os.path.join(os.path.dirname(__file__),"..","backend"))
import uuid,calendar
from datetime import datetime,date
from decimal import Decimal

from sqlalchemy import create_engine;from sqlalchemy.orm import sessionmaker
from database import Base;_rp=__import__('database')._request_write_perm;_rp.set(True)
import models,models_finance,models_bank
from models_finance import Ledger,LedgerAccount,AccountMove,AccountMoveLine

e=create_engine("sqlite:///:memory:");Base.metadata.create_all(bind=e)
S=sessionmaker(bind=e);db=S()

# ═══════════════════════════ 建账 ═══════════════════════════
acc=models.Account(name="星辰科技有限公司",code=f"XC{uuid.uuid4().hex[:4]}",taxpayer_type_l3="general")
db.add(acc);db.flush();aid=acc.id
from finance_integration import get_or_create_ledger_id;lid=get_or_create_ledger_id(db,aid)
bank=models.BankAccount(account_id=aid,bank_name="工商银行",account_number="6222021234567890",balance_l4=0)
supp=models.Supplier(account_id=aid,name="供应商A",contact="A",phone="13800000001")
cust=models.Customer(account_id=aid,name="客户B",contact="B",phone="13900000002")
db.add_all([bank,supp,cust]);db.flush();baid=bank.id

from engine_tax import TaxAccrualEngine;tax=TaxAccrualEngine(db)
from engine_tax_check import TaxCheckEngine
from engine_bank_reconcile import BankReconcileEngine

def J(db,lid,dt,drs,crs):
    m=AccountMove(ledger_id=lid,move_type="biz",date_l1=dt,state="posted");db.add(m);db.flush()
    for c,a in drs.items():
        ac=db.query(LedgerAccount).filter(LedgerAccount.ledger_id==lid,LedgerAccount.code==c).first()
        if ac and a:db.add(AccountMoveLine(move_id=m.id,ledger_account_id=ac.id,debit_l2=Decimal(str(a)),credit_l2=0,amount_residual_l2=Decimal(str(a))))
    for c,a in crs.items():
        ac=db.query(LedgerAccount).filter(LedgerAccount.ledger_id==lid,LedgerAccount.code==c).first()
        if ac and a:db.add(AccountMoveLine(move_id=m.id,ledger_account_id=ac.id,debit_l2=0,credit_l2=Decimal(str(a)),amount_residual_l2=Decimal(str(a))))
    db.flush()

def B(amt,dr,dt):
    t=models.BankTransaction(bank_account_id=baid,account_id=aid,amount_l2=amt,
        transaction_type="inflow" if dr=="in" else "outflow",transaction_date_l1=dt,balance_after_l4=Decimal(str(amt)) if dr=="in" else Decimal("0"))
    db.add(t);db.flush()
    if dr=="in": J(db,lid,dt,{"1002":amt},{"1122":amt})
    else:        J(db,lid,dt,{"2202":amt},{"1002":amt})
    db.flush();return t

# 期初
J(db,lid,datetime(2024,12,31,23,59,59),{"1002":100000},{"3001":100000});db.commit()

# ═══════════════════════════ 6个月经营 ═══════════════════════════
# (月, 采购含税,采购不含,进项, 销售含税,销售不含,销项,
#  采购付日,销售收日, 工资日,工资, 房租日,房租, 水电日,水电)

PLAN=[
("2025-01", 11300,10000,1300,  22600,20000,2600,  "01-05","01-08","01-10",8000,"01-01",3000,"01-15",600),
("2025-02", 16950,15000,1950,  33900,30000,3900,  "02-05","02-08","02-10",8500,"02-01",3000,"02-15",550),
("2025-03", 28250,25000,3250,  45200,40000,5200,  "03-05","03-08","03-10",9000,"03-01",3000,"03-15",700),
("2025-04", 22600,20000,2600,  56500,50000,6500,  "04-05","04-08","04-10",9000,"04-01",3000,"04-15",620),
("2025-05", 16950,15000,1950,  45200,40000,5200,  "05-05","05-08","05-10",9500,"05-01",3000,"05-15",680),
("2025-06", 28250,25000,3250,  67800,60000,7800,  "06-05","06-08","06-10",9500,"06-01",3000,"06-15",590),
]

print(f"星辰科技 | 一般纳税人 | 软件开发+硬件销售 | 期初 100,000")
print(f"{'月':<7}{'采购':>7}{'进项':>6}{'销售':>7}{'销项':>6}{'毛利':>7}{'工资':>6}{'房租':>5}{'水电':>5}{'VAT':>6}{'附加':>7}{'所得':>8}{'净利':>8}{'银行':>8}{'对账':>4}{'核对':>5}")
print("-"*115)

cum_rev,cum_cogs,cum_exp=0,0,0

for period,pt,pu,iv,st,su,ov,pdt,sdt,wdt,wage,rdt,rent,udt,util in PLAN:
    y,m=int(period[:4]),int(period[5:7]);mid=datetime(y,m,15)
    
    # 业务流程
    J(db,lid,mid,{"1405":pu,"222102":iv},{"2202":pt})            # 采购入库
    J(db,lid,mid,{"1122":st},{"6001":su,"222101":ov})            # 销售
    J(db,lid,mid,{"6401":pu},{"1405":pu})                         # 出库COGS
    J(db,lid,mid,{"6601":wage},{"2202":wage})                     # 工资
    J(db,lid,mid,{"6601":rent},{"2202":rent})                     # 房租
    J(db,lid,mid,{"6601":util},{"2202":util})                     # 水电
    
    # 银行收付
    B(su+ov,"in", datetime(y,m,int(sdt.split("-")[1])))           # 收销售款
    B(pt,   "out",datetime(y,m,int(pdt.split("-")[1])))           # 付采购款
    B(wage, "out",datetime(y,m,int(wdt.split("-")[1])))           # 付工资
    B(rent, "out",datetime(y,m,int(rdt.split("-")[1])))           # 付房租
    B(util, "out",datetime(y,m,int(udt.split("-")[1])))           # 付水电
    db.commit()
    
    # 月结
    r=tax.execute(aid,period)
    sur=round(r["curr_vat"]*0.12,2)
    it_delta=round(r["target_income_tax"]-r["posted_income_tax"],2)
    
    # 银行对账 (银行扣 15 管理费)
    bb=sum(Decimal(str(l.debit_l2))-Decimal(str(l.credit_l2)) for l in db.query(AccountMoveLine).join(AccountMove).filter(
        AccountMoveLine.ledger_account_id==db.query(LedgerAccount).filter(LedgerAccount.ledger_id==lid,LedgerAccount.code=="1002").first().id,
        AccountMove.date_l1<=datetime(y,m,28,23,59,59)).all())
    stmt=models_bank.BankStatement(bank_account_id=baid,account_id=aid,
        period_start=date(y,m,1),period_end=date(y,m,28),opening_balance_l1=float(bb-su-ov+pt+wage+rent+util),closing_balance_l1=float(bb-15))
    db.add(stmt);db.flush()
    db.add(models_bank.BankStatementLine(statement_id=stmt.id,transaction_date_l1=datetime(y,m,int(sdt.split("-")[1])).date(),amount_l1=su+ov,description=f"{period}销售回款"))
    db.add(models_bank.BankStatementLine(statement_id=stmt.id,transaction_date_l1=datetime(y,m,int(pdt.split("-")[1])).date(),amount_l1=-pt,description=f"{period}采购付款"))
    db.add(models_bank.BankStatementLine(statement_id=stmt.id,transaction_date_l1=datetime(y,m,int(wdt.split("-")[1])).date(),amount_l1=-wage,description=f"{period}工资"))
    db.add(models_bank.BankStatementLine(statement_id=stmt.id,transaction_date_l1=datetime(y,m,int(rdt.split("-")[1])).date(),amount_l1=-rent,description=f"{period}房租"))
    db.add(models_bank.BankStatementLine(statement_id=stmt.id,transaction_date_l1=datetime(y,m,int(udt.split("-")[1])).date(),amount_l1=-util,description=f"{period}水电"))
    db.add(models_bank.BankStatementLine(statement_id=stmt.id,transaction_date_l1=datetime(y,m,15).date(),amount_l1=-15,description="账户管理费"))
    db.commit()
    be=BankReconcileEngine(db,aid,baid,period);rec=be.create_reconciliation([]);be.run_matching()
    items=db.query(models_bank.ReconciliationItem).filter(models_bank.ReconciliationItem.reconciliation_id==rec.id).all()
    um=sum(1 for i in items if not i.resolved)
    db.commit()
    
    # 税务核对 (累计值)
    from engine_tax import _crd;ledg=db.query(Ledger).filter(Ledger.code==acc.code).first()
    cum_vat=float(_crd(db,ledg,"222107",datetime(y,m,28,23,59,59)))
    gp=round(float(Decimal(str(su))-Decimal(str(pu))-Decimal(str(wage))-Decimal(str(rent))-Decimal(str(util))-Decimal(str(sur))),2)
    ch=TaxCheckEngine(db,aid).execute(period,{
        "sales":su,"output_vat":ov,"input_vat":iv,"unpaid_vat":cum_vat,
        "income_tax":it_delta,"surcharge":sur,"vat_payable":r["curr_vat"],"gross_profit":gp,
    })
    
    # 累计汇总
    cum_rev+=su;cum_cogs+=pu;cum_exp+=wage+rent+util
    tc="PASS" if ch["all_passed"] else f"{len(ch['warnings'])}warn"
    net=su-pu-wage-rent-util-sur-it_delta
    print(f"{period:<7}{pt:>7}{iv:>6}{st:>7}{ov:>6}{su-pu:>7}{wage:>6}{rent:>5}{util:>5}{r['curr_vat']:>6.0f} {sur:>6.2f}{it_delta:>8.2f}{net:>8.2f}{float(bb):>8.0f}{um:>4} {tc:>5}")

# ═══════════════════════════ 期末报表 ═══════════════════════════
from crud.finance import generate_balance_sheet,generate_income_statement
bs=generate_balance_sheet(db,aid,"2025-06-30")
ist=generate_income_statement(db,aid,"2025-01-01","2025-06-30")
print(f"\n═════ 期末 BS (2025-06-30) ═════")
print(f"资产: 货币{bs['monetary_funds']} 应收{bs['accounts_receivable']} 预付{bs['prepayments']} 总计{bs['total_assets']}")
print(f"负债: 应付{bs['accounts_payable']} 应交{bs['tax_payable']} 总计{bs['total_liabilities']}")
print(f"权益: 实收{bs['paid_in_capital']} 未分配{bs['retained_earnings']} 总计{bs['total_equity']}")
print(f"平衡: {bs['balanced']}  diff={bs['diff']}")
print(f"\n═════ 期末 IS (全年) ═════")
print(f"收入{ist['revenue']} 成本{ist['cost_of_goods_sold']} 费用{ist['administrative_expenses']} 附加{ist['tax_surcharges']} 所得{ist['income_tax_expense']} 净利{ist['net_profit']}")
db.close()
