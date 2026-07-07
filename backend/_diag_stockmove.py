from sqlalchemy import create_engine, text

e = create_engine('sqlite:///inventory.db')
conn = e.connect()

print('=== StockMove move_date NULL 统计 ===')
for r in conn.execute(text("SELECT COUNT(*) FROM stock_moves WHERE move_date IS NULL")):
    print(f"  move_date IS NULL: {r[0]}")

print('=== StockMove 总数 ===')
for r in conn.execute(text("SELECT COUNT(*) FROM stock_moves")):
    print(f"  total: {r[0]}")

print('=== 前 10 条 move_date IS NULL 的（如果有）===')
for r in conn.execute(text(
    "SELECT id, account_id, source_type, source_id, move_date, created_at "
    "FROM stock_moves WHERE move_date IS NULL LIMIT 10"
)):
    print(f"  {r}")
