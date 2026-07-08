"""pending_confirms 表初始化（幂等）"""


def run(engine):
    from sqlalchemy import text
    with engine.connect() as conn:
        conn.execute(text(
            "CREATE TABLE IF NOT EXISTS pending_confirms ("
            "  token VARCHAR(32) PRIMARY KEY,"
            "  method VARCHAR(10) NOT NULL,"
            "  path VARCHAR(500) NOT NULL,"
            "  summary VARCHAR(500) DEFAULT '',"
            "  body BLOB,"
            "  query_string BLOB,"
            "  headers JSON,"
            "  created_at REAL NOT NULL"
            ")"
        ))
        conn.commit()
