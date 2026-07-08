import sys
sys.path.insert(0, r'C:\Users\Administrator\Desktop\inventory-system\backend')

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from models import Account, PurchaseOrder, Payment, BankTransaction, BankAccount

engine = create_engine('sqlite:///C:/Users/Administrator/Desktop/inventory-system/backend/inventory.db')
Session = sessionmaker(bind=engine)
db = Session()

aid = 1  # 巧游电子科技

print('=== 采购单付款状态 ===')
pos = db.query(PurchaseOrder).filter(PurchaseOrder.account_id == aid).order_by(PurchaseOrder.id).all()
for po in pos:
    supplier_name = po.supplier.name if po.supplier else '未知'
    print(f"ID={po.id}, 单号={po.order_no}, 供应商={supplier_name}, 金额={po.total_price_l1}, 状态={po.payment_status}")

print('\n=== 付款记录 ===')
payments = db.query(Payment).filter(Payment.account_id == aid).order_by(Payment.id).all()
for p in payments:
    bt = p.bank_transaction
    bt_info = f"银行流水ID={bt.id}, 金额={bt.amount_l2}" if bt else "无银行流水"
    print(f"ID={p.id}, 类型={p.payment_type}, 关联={p.related_entity_type}/{p.related_entity_id}, "
          f"金额={p.amount_l1}, 日期={p.payment_date_l1}, 方式={p.payment_method}, "
          f"银行账号={p.bank_account_id}, {bt_info}")

print('\n=== 银行账户余额 ===')
bas = db.query(BankAccount).filter(BankAccount.account_id == aid).all()
for ba in bas:
    print(f"ID={ba.id}, 银行={ba.bank_name}, 余额={ba.balance_l4}")

print('\n=== 最近银行流水 ===')
bts = db.query(BankTransaction).filter(BankTransaction.account_id == aid).order_by(BankTransaction.id.desc()).limit(10).all()
for bt in bts:
    print(f"ID={bt.id}, 类型={bt.transaction_type}, 金额={bt.amount_l2}, 日期={bt.transaction_date_l1}, "
          f"关联={bt.related_entity_type}/{bt.related_entity_id}, 描述={bt.description}")

db.close()
