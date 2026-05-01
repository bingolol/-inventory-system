from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import sessionmaker, DeclarativeBase
from sqlalchemy.exc import IntegrityError
from decimal import Decimal
import os
import logging
import shutil

logger = logging.getLogger("inventory")

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "inventory.db")
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
        "purchase_orders", "sale_orders", "invoices", "project_costs"
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
    """联动改造：新增字段 + 索引 + 旧数据回填"""
    insp = inspect(engine)

    # ── 1. sale_orders 增加 project_id + 索引 ──
    if "sale_orders" in insp.get_table_names():
        cols = [c["name"] for c in insp.get_columns("sale_orders")]
        if "project_id" not in cols:
            with engine.connect() as conn:
                conn.execute(text("ALTER TABLE sale_orders ADD COLUMN project_id INTEGER REFERENCES projects(id)"))
                conn.execute(text("CREATE INDEX IF NOT EXISTS ix_sale_orders_project_id ON sale_orders(project_id)"))
                conn.commit()
            logger.info("迁移: sale_orders 表添加 project_id 列及索引")
        # ── 1.1 sale_orders 增加 deduct_inventory（零售扣库存开关）──
        if "deduct_inventory" not in cols:
            with engine.connect() as conn:
                conn.execute(text("ALTER TABLE sale_orders ADD COLUMN deduct_inventory INTEGER DEFAULT 0"))
                conn.commit()
            logger.info("迁移: sale_orders 表添加 deduct_inventory 列（默认0）")

    # ── 2. purchase_orders 增加 project_id + 索引 ──
    if "purchase_orders" in insp.get_table_names():
        cols = [c["name"] for c in insp.get_columns("purchase_orders")]
        if "project_id" not in cols:
            with engine.connect() as conn:
                conn.execute(text("ALTER TABLE purchase_orders ADD COLUMN project_id INTEGER REFERENCES projects(id)"))
                conn.execute(text("CREATE INDEX IF NOT EXISTS ix_purchase_orders_project_id ON purchase_orders(project_id)"))
                conn.commit()
            logger.info("迁移: purchase_orders 表添加 project_id 列及索引")

    # ── 3. project_costs 增加 product_id, quantity ──
    if "project_costs" in insp.get_table_names():
        cols = [c["name"] for c in insp.get_columns("project_costs")]
        if "product_id" not in cols:
            with engine.connect() as conn:
                conn.execute(text("ALTER TABLE project_costs ADD COLUMN product_id INTEGER REFERENCES products(id)"))
                conn.commit()
            logger.info("迁移: project_costs 表添加 product_id 列")
        if "quantity" not in cols:
            with engine.connect() as conn:
                conn.execute(text("ALTER TABLE project_costs ADD COLUMN quantity INTEGER"))
                conn.commit()
            logger.info("迁移: project_costs 表添加 quantity 列")

    # ── 4. project_incomes 增加 source_type, source_id + UNIQUE 索引 ──
    if "project_incomes" in insp.get_table_names():
        cols = [c["name"] for c in insp.get_columns("project_incomes")]
        if "source_type" not in cols:
            with engine.connect() as conn:
                conn.execute(text("ALTER TABLE project_incomes ADD COLUMN source_type VARCHAR(20) DEFAULT 'manual'"))
                conn.commit()
        if "source_id" not in cols:
            with engine.connect() as conn:
                conn.execute(text("ALTER TABLE project_incomes ADD COLUMN source_id INTEGER"))
                conn.commit()
        # ★ 保证收入不变量 II：同一 source_type + source_id 唯一
        # 仅对 sale_order 类型去重，手动记录(source_type='manual', source_id=NULL)不受影响
        with engine.connect() as conn:
            conn.execute(text("""
                DELETE FROM project_incomes WHERE rowid NOT IN (
                    SELECT MIN(rowid) FROM project_incomes
                    WHERE source_type = 'sale_order' AND source_id IS NOT NULL
                    GROUP BY source_type, source_id
                ) AND source_type = 'sale_order' AND source_id IS NOT NULL
            """))
            conn.commit()
            conn.execute(text(
                "CREATE UNIQUE INDEX IF NOT EXISTS uq_income_source "
                "ON project_incomes(source_type, source_id)"
            ))
            conn.commit()
            logger.info("迁移: project_incomes 表添加 uq_income_source 唯一索引")

    # ★ source_id 单独索引：sale_delete_income 按 source_type+source_id 查询
    if "project_incomes" in insp.get_table_names():
        with engine.connect() as conn:
            conn.execute(text(
                "CREATE INDEX IF NOT EXISTS ix_project_incomes_source_id "
                "ON project_incomes(source_id)"
            ))
            conn.commit()

    # ── 5. 强制项目名唯一 + 旧数据回填：project_name → project_id ──
    # 5a. 检测并消除同名项目
    with engine.connect() as conn:
        duplicates = conn.execute(text("""
            SELECT account_id, name, COUNT(*) as cnt
            FROM projects
            GROUP BY account_id, name
            HAVING cnt > 1
        """)).fetchall()
        if duplicates:
            logger.warning(f"回填: 发现 {len(duplicates)} 组同名项目，自动加后缀消除")
            for account_id_val, dup_name, cnt in duplicates:
                rows = conn.execute(text("""
                    SELECT id FROM projects
                    WHERE account_id = :aid AND name = :n
                    ORDER BY created_at ASC
                """), {"aid": account_id_val, "n": dup_name}).fetchall()
                for i, row in enumerate(rows):
                    if i > 0:
                        new_name = f"{dup_name}_{i + 1}"
                        conn.execute(text(
                            "UPDATE projects SET name = :nn WHERE id = :pid"
                        ), {"nn": new_name, "pid": row[0]})
                        logger.info(f"回填: 项目ID={row[0]} '{dup_name}' 重命名为 '{new_name}'")
            conn.commit()

    # 5b. 建UNIQUE约束：同账号下项目名唯一
    with engine.connect() as conn:
        conn.execute(text(
            "CREATE UNIQUE INDEX IF NOT EXISTS uq_projects_account_name "
            "ON projects(account_id, name)"
        ))
        conn.commit()
        logger.info("迁移: projects 表添加 uq_projects_account_name 唯一索引")

    # 5c. 安全回填：现在项目名已唯一，project_name → project_id 精确匹配
    with engine.connect() as conn:
        conn.execute(text("""
            UPDATE sale_orders
            SET project_id = (
                SELECT p.id FROM projects p
                WHERE p.name = sale_orders.project_name
                  AND p.account_id = sale_orders.account_id
                LIMIT 1
            )
            WHERE project_name IS NOT NULL AND project_name != '' AND project_id IS NULL
        """))
        conn.execute(text("""
            UPDATE purchase_orders
            SET project_id = (
                SELECT p.id FROM projects p
                WHERE p.name = purchase_orders.project_name
                  AND p.account_id = purchase_orders.account_id
                LIMIT 1
            )
            WHERE project_name IS NOT NULL AND project_name != '' AND project_id IS NULL
        """))
        conn.commit()

    # ── 6. 回填销售单收入：为已关联项目的旧销售单自动生成 ProjectIncome ──
    with engine.connect() as conn:
        conn.execute(text("""
            INSERT INTO project_incomes (project_id, amount, payment_status, invoice_status, notes, source_type, source_id, income_date)
            SELECT so.project_id, so.total_price, 'pending',
                   CASE WHEN so.has_invoice THEN '已开' ELSE '未开' END,
                   '数据迁移：销售单 ' || so.order_no || ' 回填生成',
                   'sale_order', so.id, so.sale_date
            FROM sale_orders so
            WHERE so.project_id IS NOT NULL
              AND NOT EXISTS (
                  SELECT 1 FROM project_incomes pi
                  WHERE pi.source_type = 'sale_order' AND pi.source_id = so.id
              )
        """))
        conn.commit()
    logger.info("迁移: 旧数据 project_id 回填 + 销售单收入回填完成")


def _migrate_unique_item_constraint(engine):
    """为 sale_items 和 purchase_items 添加 (order_id, product_id) 唯一约束
    防止同一订单内同一商品重复出现"""
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
    """
    insp = inspect(engine)
    
    # 幂等检查：检查 products 表的 purchase_price 字段是否已是 NUMERIC
    if "products" in insp.get_table_names():
        cols = [c for c in insp.get_columns("products") if c["name"] == "purchase_price"]
        if cols and str(cols[0]["type"]).upper().startswith("NUMERIC"):
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
        "projects",
        "project_costs",
        "project_incomes",
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
        "projects": ["total_income", "total_cost", "profit"],
        "project_costs": ["amount"],
        "project_incomes": ["amount", "received_amount"],
        "expenses": ["amount"],
        "opening_balances": ["cash_balance", "bank_balance", "accounts_receivable", "inventory_value", "accounts_payable", "tax_payable", "retained_earnings"],
        "cash_flow_transactions": ["amount"],
        "personal_transactions": ["amount"],
    }
    
    with engine.connect() as conn:
        # 禁用外键约束以避免迁移顺序问题
        conn.execute(text("PRAGMA foreign_keys=OFF"))
        conn.commit()
        
        for table in tables_to_migrate:
            if table not in insp.get_table_names():
                continue
            
            old_table = f"{table}__old_numeric"
            
            # 1. RENAME旧表
            conn.execute(text(f"ALTER TABLE [{table}] RENAME TO [{old_table}]"))
            conn.commit()
            
            # 2. 用新models创建新表结构
            import models
            metadata_table = Base.metadata.tables.get(table)
            if metadata_table:
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
    
    # 补全所有约束和索引
    import models
    Base.metadata.create_all(bind=engine)
    logger.info("Float→Numeric 迁移: 全部完成，约束和索引已补全")


def init_db():
    import models
    Base.metadata.create_all(bind=engine)
    _migrate_image_url(engine)
    _migrate_operator(engine)
    _migrate_linkage(engine)
    _migrate_unique_item_constraint(engine)
    _migrate_numeric_fields(engine)