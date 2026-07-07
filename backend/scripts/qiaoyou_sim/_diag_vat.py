"""临时诊断脚本：查 222101/222103 分录"""
import sqlite3

conn = sqlite3.connect('inventory.db')
c = conn.cursor()

print("=== 222101 (一般纳税人销项) 分录 ===")
c.execute("""
SELECT am.date_l1, am.source_model, la.code, aml.debit_l2, aml.credit_l2
FROM account_moves am
JOIN account_move_lines aml ON aml.move_id = am.id
JOIN ledger_accounts la ON aml.ledger_account_id = la.id
WHERE la.code IN ('222101', '222103')
ORDER BY am.date_l1
""")
for r in c.fetchall():
    print(r)

print("\n=== 6001 主营业务收入（6月销售） ===")
c.execute("""
SELECT am.date_l1, am.source_model, la.code, aml.debit_l2, aml.credit_l2
FROM account_moves am
JOIN account_move_lines aml ON aml.move_id = am.id
JOIN ledger_accounts la ON aml.ledger_account_id = la.id
WHERE la.code = '6001' AND am.date_l1 LIKE '2026-06%'
ORDER BY am.date_l1
""")
for r in c.fetchall():
    print(r)

print("\n=== 6月所有凭证 ===")
c.execute("""
SELECT am.date_l1, am.source_model, am.source_id
FROM account_moves am
WHERE am.date_l1 LIKE '2026-06%'
ORDER BY am.date_l1, am.id
""")
for r in c.fetchall():
    print(r)

conn.close()
