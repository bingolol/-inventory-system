import sqlite3
conn = sqlite3.connect('inventory.db')
c = conn.cursor()
c.execute("SELECT name FROM sqlite_master WHERE type='table'")
tables = c.fetchall()
for t in tables:
    name = t[0]
    print('=== %s ===' % name)
    c.execute("PRAGMA table_info(%s)" % name)
    cols = c.fetchall()
    for col in cols:
        print('  %s' % str(col))
    try:
        c.execute("SELECT COUNT(*) FROM %s" % name)
        print('  Rows: %d' % c.fetchone()[0])
    except:
        pass
    print()
conn.close()
