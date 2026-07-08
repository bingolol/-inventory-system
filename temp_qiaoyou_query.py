import sys
sys.path.insert(0, r'C:\Users\Administrator\Desktop\inventory-system\backend')

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from models import Account, PurchaseOrder, Supplier, Invoice, Product

engine = create_engine('sqlite:///C:/Users/Administrator/Desktop/inventory-system/backend/inventory.db')
Session = sessionmaker(bind=engine)
db = Session()

# 1. 查找巧游电子科技账套
accounts = db.query(Account).filter(Account.name.like('%巧游%')).all()
print('=== 匹配账套 ===')
for a in accounts:
    print(f"ID={a.id}, 名称={a.name}, 纳税人={a.taxpayer_type_l3}")

if not accounts:
    print('未找到巧游账套')
    db.close()
    sys.exit(0)

aid = accounts[0].id
print(f'\n使用账套 ID: {aid}')

# 2. 查询未付款采购订单
print('\n=== 未付款采购订单 ===')
pos = db.query(PurchaseOrder).filter(
    PurchaseOrder.account_id == aid,
    PurchaseOrder.payment_status == 'unpaid'
).all()
for po in pos:
    supplier_name = po.supplier.name if po.supplier else '未知'
    print(f"ID={po.id}, 单号={po.order_no}, 供应商={supplier_name}, "
          f"金额={po.total_price_l1}, 状态={po.payment_status}, 日期={po.purchase_date_l1}")

# 3. 查询所有进项发票
print('\n=== 进项发票 ===')
invoices = db.query(Invoice).filter(
    Invoice.account_id == aid,
    Invoice.direction == 'in'
).all()
for inv in invoices:
    print(f"ID={inv.id}, 发票号={inv.invoice_no}, 销售方={inv.counterparty_name}, "
          f"含税={inv.amount_with_tax_l1}, 未税={inv.amount_without_tax_l1}, "
          f"税额={inv.tax_amount_l1}, 日期={inv.issue_date_l1}, "
          f"关联类型={inv.related_order_type}, 关联ID={inv.related_order_id}")

db.close()
