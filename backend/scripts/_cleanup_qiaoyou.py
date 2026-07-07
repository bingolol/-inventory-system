"""清理巧游模拟产生的重复数据"""
import sqlite3

c = sqlite3.connect("inventory.db")
cur = c.cursor()

# 查看所有重复的巧游商品
print("=== 巧游商品 ===")
cur.execute(
    "SELECT id, name FROM products WHERE name IN "
    "('信息系统服务','修理修配劳务','微电子组件','其他加工劳务','维修备件') "
    "ORDER BY name, id"
)
rows = cur.fetchall()
for row in rows:
    print(row)

# 每个名字保留最小 id，删除其余
from collections import defaultdict
by_name = defaultdict(list)
for r in rows:
    by_name[r[1]].append(r[0])

to_del = []
for name, ids in by_name.items():
    keep = min(ids)
    for i in ids:
        if i != keep:
            to_del.append(i)

print(f"\n将删除 {len(to_del)} 个重复商品: {to_del}")
cur.execute(f"DELETE FROM products WHERE id IN ({','.join(map(str, to_del))})")

# 同样处理客户
print("\n=== 巧游客户 ===")
cur.execute(
    "SELECT id, name FROM customers WHERE name IN "
    "('中国联通宜宾分公司','四川南山射钉紧固器材有限公司') "
    "ORDER BY name, id"
)
rows = cur.fetchall()
for row in rows:
    print(row)

by_name = defaultdict(list)
for r in rows:
    by_name[r[1]].append(r[0])

to_del = []
for name, ids in by_name.items():
    keep = min(ids)
    for i in ids:
        if i != keep:
            to_del.append(i)

print(f"\n将删除 {len(to_del)} 个重复客户: {to_del}")
cur.execute(f"DELETE FROM customers WHERE id IN ({','.join(map(str, to_del))})")

# 同样处理供应商
print("\n=== 巧游供应商 ===")
cur.execute(
    "SELECT id, name FROM suppliers WHERE name IN "
    "('吴江恒净净化设备经营部','临泉县嘉涵商贸有限公司','乐清市申港电气厂','博控科技（淮安）有限公司') "
    "ORDER BY name, id"
)
rows = cur.fetchall()
for row in rows:
    print(row)

by_name = defaultdict(list)
for r in rows:
    by_name[r[1]].append(r[0])

to_del = []
for name, ids in by_name.items():
    keep = min(ids)
    for i in ids:
        if i != keep:
            to_del.append(i)

print(f"\n将删除 {len(to_del)} 个重复供应商: {to_del}")
cur.execute(f"DELETE FROM suppliers WHERE id IN ({','.join(map(str, to_del))})")

# 删除重复的银行账户（保留最小 id）
print("\n=== 巧游银行账户 ===")
cur.execute(
    "SELECT id, bank_name, account_number FROM bank_accounts "
    "WHERE account_number = '22-478401040025143' ORDER BY id"
)
rows = cur.fetchall()
for row in rows:
    print(row)

if len(rows) > 1:
    keep = rows[0][0]
    to_del = [r[0] for r in rows[1:]]
    print(f"\n将删除 {len(to_del)} 个重复银行账户: {to_del}")
    cur.execute(
        f"DELETE FROM bank_accounts WHERE id IN ({','.join(map(str, to_del))})"
    )

# 删除测试商品
cur.execute("DELETE FROM products WHERE name = '测试商品'")
print(f"\n删除测试商品: {cur.rowcount}")

c.commit()
c.close()
print("\n清理完成")
