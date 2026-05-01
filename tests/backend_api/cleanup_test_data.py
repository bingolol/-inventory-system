import sys
sys.path.insert(0, r'C:\Users\Administrator\Desktop\inventory-system\backend')
from database import SessionLocal
from models import PersonalTransaction

session = SessionLocal()

# 删除 id=39,40（测试污染数据）
rows = session.query(PersonalTransaction).filter(PersonalTransaction.id.in_([39, 40])).all()
for r in rows:
    session.delete(r)
session.commit()

print(f'已删除 {len(rows)} 条测试污染记录')

# 验证最新记录不再是测试数据
latest = session.query(PersonalTransaction).order_by(PersonalTransaction.id.desc()).limit(5).all()
print('当前最新5条记录:')
for r in latest:
    print(f'  id={r.id} type={r.type} cat={r.category} amt={r.amount}')

session.close()