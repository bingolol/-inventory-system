"""真相源流水表 SQLite BEFORE UPDATE 触发器（数据库级防护）"""


def run(engine):
    from sqlalchemy import text

    triggers = [
        ("trg_immutable_stock_moves", "stock_moves",
         "StockMove 是库存真相源，禁止 UPDATE，错误更正请通过红冲调整单实现"),
        ("trg_immutable_account_moves", "account_moves",
         "AccountMove 是会计凭证真相源，禁止 UPDATE，错误更正请通过红字冲销实现"),
        ("trg_immutable_depreciations", "fixed_asset_depreciations",
         "FixedAssetDepreciation 是折旧真相源，禁止 UPDATE"),
        ("trg_immutable_bank_transactions", "bank_transactions",
         "BankTransaction 是银行流水真相源，禁止 UPDATE"),
        ("trg_immutable_amortizations", "intangible_asset_amortizations",
         "IntangibleAssetAmortization 是摊销流水真相源，禁止 UPDATE"),
    ]

    with engine.connect() as conn:
        for trg_name, table, msg in triggers:
            conn.execute(text(f"DROP TRIGGER IF EXISTS {trg_name}"))
            conn.execute(text(
                f"CREATE TRIGGER {trg_name} "
                f"BEFORE UPDATE ON {table} "
                f"BEGIN "
                f"SELECT RAISE(ABORT, '{msg}'); "
                f"END"
            ))
        conn.commit()
    print(f"[ImmutableTriggers] 已创建 {len(triggers)} 个真相源表 UPDATE 触发器")
