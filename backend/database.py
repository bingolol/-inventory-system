from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import sessionmaker, DeclarativeBase
from sqlalchemy.exc import IntegrityError
from decimal import Decimal
import os
import logging
import shutil

from workspace import get_db_path as _get_db_path

logger = logging.getLogger("inventory")

DB_PATH = _get_db_path()
DATABASE_URL = f"sqlite:///{DB_PATH}"

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    pass


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def _migrate_image_url(engine):
    """为缺少 image_url 列的表自动添加字段（SQLite ALTER TABLE ADD COLUMN）"""
    tables_need_image_url = [
        "purchase_orders", "sale_orders", "invoices"
    ]
    insp = inspect(engine)
    for table in tables_need_image_url:
        columns = [col["name"] for col in insp.get_columns(table)]
        if "image_url" not in columns:
            with engine.connect() as conn:
                conn.execute(text(f"ALTER TABLE {table} ADD COLUMN image_url VARCHAR(500) DEFAULT ''"))
                conn.commit()
            logger.info(f"迁移: {table} 表添加 image_url 列")


def _migrate_operator(engine):
    """为 operation_logs 表添加 operator 列（区分 user/ai 操作者）"""
    insp = inspect(engine)
    if "operation_logs" in insp.get_table_names():
        columns = [col["name"] for col in insp.get_columns("operation_logs")]
        if "operator" not in columns:
            with engine.connect() as conn:
                conn.execute(text("ALTER TABLE operation_logs ADD COLUMN operator VARCHAR(20) NOT NULL DEFAULT 'user'"))
                conn.commit()
            logger.info("迁移: operation_logs 表添加 operator 列")


def _migrate_linkage(engine):
    """联动改造迁移（已废弃：项目功能已移除）
    
    保留空函数以避免 init_db 调用报错。
    项目相关表(project_costs, project_incomes, projects)在旧数据库中仍存在，
    但新代码不再使用。迁移不再需要执行。
    """
    logger.info("迁移: 联动迁移已跳过（项目功能已移除）")





def _migrate_unique_item_constraint(engine):
    """为 sale_items 和 purchase_items 添加 (order_id, product_id) 唯一约束
    防止同一订单内同一商品重复出现

    注意：迁移函数使用 engine.connect() 而非 Session，其 conn.commit() 独立于 Unit of Work 事务边界。
    这是设计如此——迁移在应用启动时执行，不属于业务代码范畴。
    """
    insp = inspect(engine)
    existing_indexes = {row[0] for row in engine.connect().execute(
        text("SELECT name FROM sqlite_master WHERE type='index'")
    ).fetchall()}
    
    if "uix_sale_item_order_product" not in existing_indexes:
        # 先检查是否有重复数据，如有则合并
        with engine.connect() as conn:
            dupes = conn.execute(text("""
                SELECT order_id, product_id, COUNT(*) as cnt
                FROM sale_items
                GROUP BY order_id, product_id
                HAVING cnt > 1
            """)).fetchall()
            if dupes:
                logger.warning(f"迁移: sale_items 存在 {len(dupes)} 组重复商品，需先清理")
                for order_id, product_id, cnt in dupes:
                    # 合并：保留最早一行，数量求和，金额求和
                    conn.execute(text("""
                        UPDATE sale_items
                        SET quantity = (SELECT SUM(quantity) FROM sale_items WHERE order_id=:oid AND product_id=:pid),
                            total_price = (SELECT SUM(total_price) FROM sale_items WHERE order_id=:oid AND product_id=:pid)
                        WHERE order_id=:oid AND product_id=:pid AND id = (
                            SELECT MIN(id) FROM sale_items WHERE order_id=:oid AND product_id=:pid
                        )
                    """), {"oid": order_id, "pid": product_id})
                    conn.execute(text("""
                        DELETE FROM sale_items
                        WHERE order_id=:oid AND product_id=:pid AND id != (
                            SELECT MIN(id) FROM sale_items WHERE order_id=:oid AND product_id=:pid
                        )
                    """), {"oid": order_id, "pid": product_id})
                conn.commit()
                logger.info("迁移: sale_items 重复数据已合并")
            conn.execute(text("CREATE UNIQUE INDEX IF NOT EXISTS uix_sale_item_order_product ON sale_items (order_id, product_id)"))
            conn.commit()
        logger.info("迁移: sale_items 添加 (order_id, product_id) 唯一约束")

    if "uix_purchase_item_order_product" not in existing_indexes:
        with engine.connect() as conn:
            dupes = conn.execute(text("""
                SELECT order_id, product_id, COUNT(*) as cnt
                FROM purchase_items
                GROUP BY order_id, product_id
                HAVING cnt > 1
            """)).fetchall()
            if dupes:
                logger.warning(f"迁移: purchase_items 存在 {len(dupes)} 组重复商品，需先清理")
                for order_id, product_id, cnt in dupes:
                    conn.execute(text("""
                        UPDATE purchase_items
                        SET quantity = (SELECT SUM(quantity) FROM purchase_items WHERE order_id=:oid AND product_id=:pid),
                            total_price = (SELECT SUM(total_price) FROM purchase_items WHERE order_id=:oid AND product_id=:pid)
                        WHERE order_id=:oid AND product_id=:pid AND id = (
                            SELECT MIN(id) FROM purchase_items WHERE order_id=:oid AND product_id=:pid
                        )
                    """), {"oid": order_id, "pid": product_id})
                    conn.execute(text("""
                        DELETE FROM purchase_items
                        WHERE order_id=:oid AND product_id=:pid AND id != (
                            SELECT MIN(id) FROM purchase_items WHERE order_id=:oid AND product_id=:pid
                        )
                    """), {"oid": order_id, "pid": product_id})
                conn.commit()
                logger.info("迁移: purchase_items 重复数据已合并")
            conn.execute(text("CREATE UNIQUE INDEX IF NOT EXISTS uix_purchase_item_order_product ON purchase_items (order_id, product_id)"))
            conn.commit()
        logger.info("迁移: purchase_items 添加 (order_id, product_id) 唯一约束")


def _migrate_numeric_fields(engine):
    """Float→Numeric(12,2) 迁移（幂等，安全）
    
    SQLite不支持ALTER COLUMN，需逐表重建：
    1. RENAME旧表 → 2. CREATE新表（用新models） → 3. INSERT迁移数据 → 4. DROP旧表

    注意：迁移函数使用 engine.connect() 而非 Session，其 conn.commit() 独立于 Unit of Work 事务边界。
    这是设计如此——迁移在应用启动时执行，不属于业务代码范畴。
    """
    insp = inspect(engine)

    # 幂等检查：检查所有关键字段是否已是 NUMERIC（防止部分迁移后跳过）
    all_numeric = True
    check_fields = [
        ("products", "purchase_price"),
        ("sale_orders", "total_price"),
    ]
    for table_name, col_name in check_fields:
        if table_name in insp.get_table_names():
            cols = [c for c in insp.get_columns(table_name) if c["name"] == col_name]
            if cols and not str(cols[0]["type"]).upper().startswith("NUMERIC"):
                all_numeric = False
                break

    if all_numeric:
        # 清理可能因崩溃残留的 __old_numeric 表
        for t in insp.get_table_names():
            if t.endswith("__old_numeric"):
                with engine.connect() as conn:
                    conn.execute(text(f"DROP TABLE [{t}]"))
                    conn.commit()
                logger.info(f"Float→Numeric 迁移: 清理残留表 {t}")
        logger.info("Float→Numeric 迁移: 已完成，跳过")
        return
    
    # 备份数据库
    backup_path = DB_PATH + ".pre_numeric_backup"
    if not os.path.exists(backup_path):
        shutil.copy2(DB_PATH, backup_path)
        logger.info(f"Float→Numeric 迁移前备份: {backup_path}")
    
    # 需要迁移的表列表（按依赖顺序，先迁移被依赖的表）
    tables_to_migrate = [
        "products",
        "purchase_orders",
        "purchase_items",
        "sale_orders",
        "sale_items",
        "invoices",
        "expenses",
        "opening_balances",
        "cash_flow_transactions",
        "personal_transactions",
    ]
    
    # Float→Numeric 的字段映射
    float_columns = {
        "products": ["purchase_price", "sale_price"],
        "purchase_orders": ["total_price"],
        "purchase_items": ["unit_price", "tax_rate", "total_price"],
        "sale_orders": ["total_price"],
        "sale_items": ["unit_price", "tax_rate", "total_price"],
        "invoices": ["tax_rate", "amount_without_tax", "tax_amount", "amount_with_tax"],
        "expenses": ["amount"],
        "opening_balances": ["cash_balance", "bank_balance", "accounts_receivable", "inventory_value", "accounts_payable", "tax_payable", "retained_earnings"],
        "cash_flow_transactions": ["amount"],
        "personal_transactions": ["amount"],
    }
    
    # 清理可能因崩溃残留的 __old_numeric 表（先恢复数据再清理）
    for t in insp.get_table_names():
        if t.endswith("__old_numeric"):
            base_name = t.replace("__old_numeric", "")
            # 如果新表已存在且旧表残留，直接丢弃旧表（数据已在新表中）
            if base_name in insp.get_table_names():
                with engine.connect() as conn:
                    conn.execute(text(f"DROP TABLE [{t}]"))
                    conn.commit()
                logger.info(f"Float→Numeric 迁移: 清理残留表 {t}")
            else:
                # 新表不存在，需要恢复：将旧表重命名回原名
                with engine.connect() as conn:
                    conn.execute(text(f"ALTER TABLE [{t}] RENAME TO [{base_name}]"))
                    conn.commit()
                logger.info(f"Float→Numeric 迁移: 恢复残留表 {t} → {base_name}")

    with engine.connect() as conn:
        # 禁用外键约束以避免迁移顺序问题
        conn.execute(text("PRAGMA foreign_keys=OFF"))
        conn.commit()

        for table in tables_to_migrate:
            if table not in insp.get_table_names():
                continue

            # 跳过已经是 NUMERIC 的表
            table_cols = {c["name"]: str(c["type"]).upper() for c in inspect(engine).get_columns(table)}
            target_cols = float_columns.get(table, [])
            if all(table_cols.get(c, "").startswith("NUMERIC") for c in target_cols if c in table_cols):
                continue
            
            old_table = f"{table}__old_numeric"
            
            # 1. RENAME旧表
            conn.execute(text(f"ALTER TABLE [{table}] RENAME TO [{old_table}]"))
            conn.commit()

            # 1.5 清理旧表的自定义索引（SQLite 重命名表时索引不跟着走）
            # 跳过 sqlite_autoindex_ 开头的约束索引（不能 DROP）
            old_indexes = conn.execute(text(
                "SELECT name FROM sqlite_master WHERE type='index' AND tbl_name=:t AND name NOT LIKE 'sqlite_autoindex_%'"
            ), {"t": old_table}).fetchall()
            for (idx_name,) in old_indexes:
                conn.execute(text(f"DROP INDEX IF EXISTS [{idx_name}]"))
            conn.commit()

            # 2. 用新models创建新表结构
            import models
            metadata_table = Base.metadata.tables.get(table)
            if metadata_table is not None:
                metadata_table.create(bind=engine)
            
            # 3. 获取旧表和新表的列名，确保INSERT只插入共有的列
            old_cols = [c["name"] for c in inspect(engine).get_columns(old_table)]
            new_cols = [c["name"] for c in inspect(engine).get_columns(table)]
            common_cols = [c for c in new_cols if c in old_cols]
            cols_str = ", ".join(f"[{c}]" for c in common_cols)
            
            # 4. INSERT迁移数据
            conn.execute(text(
                f"INSERT INTO [{table}] ({cols_str}) SELECT {cols_str} FROM [{old_table}]"
            ))
            conn.commit()
            
            # 5. DROP旧表
            conn.execute(text(f"DROP TABLE [{old_table}]"))
            conn.commit()
            
            logger.info(f"Float→Numeric 迁移: 表 [{table}] 完成")
        
        # 重新启用外键约束
        conn.execute(text("PRAGMA foreign_keys=ON"))
        conn.commit()

    logger.info("Float→Numeric 迁移: 全部完成")


def _ensure_default_accounts():
    """确保至少存在默认账本 + 对应 Ledger + 科目（首次安装时自动创建）"""
    import models
    from models_finance import Ledger, LedgerAccount, LedgerAccountBalance
    with SessionLocal() as db:
        count = db.query(models.Account).count()
        if count == 0:
            defaults = [
                models.Account(name="公司账本", type="company", code="company", taxpayer_type="small_scale"),
                models.Account(name="个人账本", type="personal", code="personal", taxpayer_type="small_scale"),
            ]
            for acc in defaults:
                db.add(acc)
            db.flush()
            logger.info("首次安装：已创建默认账本")

        # 为每个 Account 创建对应的 Ledger（如不存在）
        for acc in db.query(models.Account).all():
            existing = db.query(Ledger).filter(Ledger.code == acc.code).first()
            if existing:
                continue
            lgr = Ledger(name=acc.name, type=acc.type, code=acc.code,
                         taxpayer_type=acc.taxpayer_type)
            db.add(lgr)
            db.flush()
            _seed_ledger_accounts(db, lgr.id)
            logger.info(f"已创建 Ledger + 科目: code={acc.code}")

        db.commit()


def _seed_ledger_accounts(db, ledger_id):
    """为指定 Ledger 插入标准科目"""
    from models_finance import LedgerAccount, LedgerAccountBalance
    all_accounts = [
        ("1001", "库存现金", "asset"),
        ("1002", "银行存款", "asset"),
        ("1122", "应收账款", "asset_receivable"),
        ("1123", "预付账款", "asset_prepaid"),
        ("1221", "其他应收款", "asset"),
        ("1405", "库存商品", "asset"),
        ("1601", "固定资产", "asset"),
        ("1602", "累计折旧", "asset_contra"),
        ("1701", "无形资产", "asset"),
        ("1702", "累计摊销", "asset_contra"),
        ("2001", "短期借款", "liability"),
        ("2202", "应付账款", "liability_payable"),
        ("2203", "预收账款", "liability_advance"),
        ("2211", "应付职工薪酬", "liability"),
        ("2221", "应交税费", "liability"),
        ("222101", "应交增值税-销项税额", "liability"),
        ("222102", "应交增值税-进项税额", "liability"),
        ("222103", "应交增值税-小规模", "liability"),
        ("2241", "其他应付款", "liability"),
        ("2501", "长期借款", "liability"),
        ("3001", "实收资本", "equity"),
        ("4001", "实收资本", "equity"),
        ("4101", "盈余公积", "equity"),
        ("4103", "本年利润", "equity"),
        ("4104", "利润分配", "equity"),
        ("5001", "主营业务收入", "income"),
        ("5401", "主营业务成本", "expense"),
        ("5601", "销售费用", "expense"),
        ("5602", "管理费用", "expense"),
        ("5603", "财务费用", "expense"),
        ("6001", "主营业务收入(旧)", "income"),
        ("6051", "其他业务收入", "income"),
        ("6111", "资产处置收益", "income"),
        ("6401", "主营业务成本(旧)", "expense"),
        ("6403", "税金及附加", "expense"),
        ("6601", "管理费用(旧)", "expense"),
        ("6602", "销售费用(旧)", "expense"),
        ("6603", "财务费用(旧)", "expense"),
        ("6701", "营业外支出", "expense"),
        ("6711", "营业外支出", "expense"),
        ("6801", "所得税费用", "expense"),
    ]
    for code, name, atype in all_accounts:
        a = LedgerAccount(ledger_id=ledger_id, code=code, name=name,
                          account_type=atype, is_leaf=True)
        db.add(a)
        db.flush()
        db.add(LedgerAccountBalance(ledger_account_id=a.id, balance=0,
                                     debit_total=0, credit_total=0))


def _migrate_opening_balance_fields(engine):
    """为 opening_balances 表添加非流动资产/负债字段"""
    insp = inspect(engine)
    if "opening_balances" not in insp.get_table_names():
        return
    
    columns = [col["name"] for col in insp.get_columns("opening_balances")]
    
    new_columns = [
        ("fixed_assets_original", "NUMERIC(12, 2) DEFAULT 0"),
        ("accumulated_depreciation", "NUMERIC(12, 2) DEFAULT 0"),
        ("intangible_assets_original", "NUMERIC(12, 2) DEFAULT 0"),
        ("accumulated_amortization", "NUMERIC(12, 2) DEFAULT 0"),
        ("long_term_borrowings", "NUMERIC(12, 2) DEFAULT 0"),
        ("paid_in_capital", "NUMERIC(12, 2) DEFAULT 0"),
    ]
    
    with engine.connect() as conn:
        for col_name, col_type in new_columns:
            if col_name not in columns:
                conn.execute(text(f"ALTER TABLE opening_balances ADD COLUMN {col_name} {col_type}"))
                conn.commit()
                logger.info(f"迁移: opening_balances 表添加 {col_name} 列")


def _migrate_expense_functional_category(engine):
    """为 expenses 表添加 functional_category 字段"""
    insp = inspect(engine)
    if "expenses" not in insp.get_table_names():
        return
    
    columns = [col["name"] for col in insp.get_columns("expenses")]
    
    if "functional_category" not in columns:
        with engine.connect() as conn:
            conn.execute(text("ALTER TABLE expenses ADD COLUMN functional_category VARCHAR(20) NOT NULL DEFAULT '管理费用'"))
            conn.commit()
            logger.info("迁移: expenses 表添加 functional_category 列")


def _migrate_drop_has_invoice(engine):
    """删除 sale_orders/purchase_orders/expenses 的 has_invoice 列(单一真相源迁移)

    方案1:has_invoice 改为从 Invoice 表派生查询,删除冗余列。
    SQLite 不支持 ALTER TABLE DROP COLUMN,需重建表。
    """
    insp = inspect(engine)
    tables_to_migrate = ["sale_orders", "purchase_orders", "expenses"]

    # 幂等检查:如果任一表仍有 has_invoice 列,执行迁移
    need_migrate = False
    for table in tables_to_migrate:
        if table not in insp.get_table_names():
            continue
        cols = [c["name"] for c in insp.get_columns(table)]
        if "has_invoice" in cols:
            need_migrate = True
            break

    if not need_migrate:
        logger.info("has_invoice 迁移:已完成,跳过")
        return

    # 备份数据库
    backup_path = DB_PATH + ".pre_drop_has_invoice"
    if not os.path.exists(backup_path):
        shutil.copy2(DB_PATH, backup_path)
        logger.info(f"has_invoice 迁移前备份: {backup_path}")

    with engine.connect() as conn:
        conn.execute(text("PRAGMA foreign_keys=OFF"))
        conn.commit()

        for table in tables_to_migrate:
            if table not in insp.get_table_names():
                continue
            cols = [c["name"] for c in insp.get_columns(table)]
            if "has_invoice" not in cols:
                continue

            old_table = f"{table}__old_has_invoice"

            # 1. RENAME 旧表
            conn.execute(text(f"ALTER TABLE [{table}] RENAME TO [{old_table}]"))
            conn.commit()

            # 2. 清理旧表自定义索引
            old_indexes = conn.execute(text(
                "SELECT name FROM sqlite_master WHERE type='index' AND tbl_name=:t AND name NOT LIKE 'sqlite_autoindex_%'"
            ), {"t": old_table}).fetchall()
            for (idx_name,) in old_indexes:
                conn.execute(text(f"DROP INDEX IF EXISTS [{idx_name}]"))
            conn.commit()

            # 3. 用新 models 创建新表(无 has_invoice 列)
            metadata_table = Base.metadata.tables.get(table)
            if metadata_table is not None:
                metadata_table.create(bind=engine)

            # 4. INSERT 迁移数据(只插入共有列)
            old_cols = [c["name"] for c in inspect(engine).get_columns(old_table)]
            new_cols = [c["name"] for c in inspect(engine).get_columns(table)]
            common_cols = [c for c in new_cols if c in old_cols]
            cols_str = ", ".join(f"[{c}]" for c in common_cols)

            conn.execute(text(
                f"INSERT INTO [{table}] ({cols_str}) SELECT {cols_str} FROM [{old_table}]"
            ))
            conn.commit()

            # 5. 行数校验
            old_count = conn.execute(text(f"SELECT COUNT(*) FROM [{old_table}]")).scalar()
            new_count = conn.execute(text(f"SELECT COUNT(*) FROM [{table}]")).scalar()
            if old_count != new_count:
                raise RuntimeError(
                    f"has_invoice 迁移行数不一致: {table} 旧表 {old_count} 行,新表 {new_count} 行"
                )

            # 6. DROP 旧表
            conn.execute(text(f"DROP TABLE [{old_table}]"))
            conn.commit()
            logger.info(f"has_invoice 迁移: 表 [{table}] 完成(删除 has_invoice 列)")

        conn.execute(text("PRAGMA foreign_keys=ON"))
        conn.commit()

    logger.info("has_invoice 迁移: 全部完成")


def _migrate_bank_transaction_flow_category(engine):
    """为 bank_transactions 表添加 flow_category 字段"""
    insp = inspect(engine)
    if "bank_transactions" not in insp.get_table_names():
        return

    columns = [col["name"] for col in insp.get_columns("bank_transactions")]

    if "flow_category" not in columns:
        with engine.connect() as conn:
            conn.execute(text("ALTER TABLE bank_transactions ADD COLUMN flow_category VARCHAR(20) NOT NULL DEFAULT 'operating'"))
            conn.commit()
            logger.info("迁移: bank_transactions 表添加 flow_category 列")


def _migrate_invoice_party_names(engine):
    """为 invoices 表添加 seller_name 和 buyer_name 列"""
    insp = inspect(engine)
    if "invoices" not in insp.get_table_names():
        return
    columns = [col["name"] for col in insp.get_columns("invoices")]
    with engine.connect() as conn:
        if "seller_name" not in columns:
            conn.execute(text("ALTER TABLE invoices ADD COLUMN seller_name VARCHAR(200) NOT NULL DEFAULT ''"))
            logger.info("迁移: invoices 表添加 seller_name 列")
        if "buyer_name" not in columns:
            conn.execute(text("ALTER TABLE invoices ADD COLUMN buyer_name VARCHAR(200) NOT NULL DEFAULT ''"))
            logger.info("迁移: invoices 表添加 buyer_name 列")
        conn.commit()


def _migrate_sale_order_tax_amount(engine):
    """为 sale_orders 表添加 tax_amount 列"""
    insp = inspect(engine)
    if "sale_orders" not in insp.get_table_names():
        return
    columns = [col["name"] for col in insp.get_columns("sale_orders")]
    if "tax_amount" not in columns:
        with engine.connect() as conn:
            conn.execute(text("ALTER TABLE sale_orders ADD COLUMN tax_amount NUMERIC(12,2) DEFAULT 0"))
            conn.commit()
            logger.info("迁移: sale_orders 表添加 tax_amount 列")


def _migrate_purchase_order_tax_amount(engine):
    """为 purchase_orders 表添加 tax_amount 列"""
    insp = inspect(engine)
    if "purchase_orders" not in insp.get_table_names():
        return
    columns = [col["name"] for col in insp.get_columns("purchase_orders")]
    if "tax_amount" not in columns:
        with engine.connect() as conn:
            conn.execute(text("ALTER TABLE purchase_orders ADD COLUMN tax_amount NUMERIC(12,2) DEFAULT 0"))
            conn.commit()
            logger.info("迁移: purchase_orders 表添加 tax_amount 列")


def init_db():
    import models
    import models_finance
    Base.metadata.create_all(bind=engine)
    _migrate_image_url(engine)
    _migrate_operator(engine)
    _migrate_linkage(engine)
    _migrate_unique_item_constraint(engine)
    _migrate_numeric_fields(engine)
    _migrate_opening_balance_fields(engine)
    _migrate_expense_functional_category(engine)
    _migrate_drop_has_invoice(engine)
    _migrate_bank_transaction_flow_category(engine)
    _migrate_invoice_party_names(engine)
    _migrate_sale_order_tax_amount(engine)
    _migrate_purchase_order_tax_amount(engine)
    # _migrate_v4_order_type 已删除：所有字段已在 models.py 中定义，create_all 自动创建
    _ensure_default_accounts()
    # 旧迁移的第6步"清空数据"无幂等保护，导致每次重启都会丢失所有数据