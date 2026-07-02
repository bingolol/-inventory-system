import contextvars
import re
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker, Session, DeclarativeBase
from sqlalchemy.sql.dml import Update, Delete, Insert
from errors import BusinessError, ErrorCode

from workspace import get_db_path as _get_db_path

# ── 全局状态 ──
_request_write_perm = contextvars.ContextVar('_request_write_perm', default=False)
_maintenance_mode = False


def _is_write_permitted() -> bool:
    return _maintenance_mode or _request_write_perm.get()


def set_maintenance_mode(val: bool):
    global _maintenance_mode
    _maintenance_mode = val


# ── Engine 私有化 ──
DB_PATH = _get_db_path()
DATABASE_URL = f"sqlite:///{DB_PATH}"

_DDL_KEYWORDS = {"drop", "alter", "create", "truncate"}
_DML_KEYWORDS = {"insert", "update", "delete", "replace"}


def _guard_text_dml(stmt_str: str, first_word: str):
    """非 ORM 写操作拦截（覆盖 text() CTE 绕过）"""
    if not _is_write_permitted():
        if first_word in _DML_KEYWORDS:
            raise BusinessError(code=ErrorCode.SECURITY_VIOLATION,
                                message="禁止直接写数据库，请调用合规 API")
        for kw in _DML_KEYWORDS:
            if re.search(rf'\b{kw}\b', stmt_str):
                # 放行 SELECT ... FOR UPDATE（行锁，非 DML）
                if kw == "update" and re.search(r'\bfor\s+update\b', stmt_str):
                    continue
                raise BusinessError(code=ErrorCode.SECURITY_VIOLATION,
                                    message="禁止直接写数据库（CTE 内 DML 被拦截）")


def _guard_execute(conn, clauseelement, multiparams, params, execution_options):
    if _maintenance_mode:
        return

    stmt_str = str(clauseelement).lower()
    first_word = stmt_str.strip().split()[0] if stmt_str.strip() else ""

    # DDL 红线（首单词检测，防表名含关键字误杀）
    if first_word in _DDL_KEYWORDS:
        raise BusinessError(code=ErrorCode.SECURITY_VIOLATION,
                            message="禁止执行结构变更(DDL)")

    # ORM-level DML
    if isinstance(clauseelement, (Update, Delete, Insert)):
        if not _is_write_permitted():
            raise BusinessError(code=ErrorCode.SECURITY_VIOLATION,
                                message="禁止直接写数据库，请调用合规 API")
        return

    # Raw SQL DML（text()、TextClause 等全靠字符串检测）
    _guard_text_dml(stmt_str, first_word)


def _make_engine(db_url: str):
    e = create_engine(db_url, connect_args={"check_same_thread": False})
    event.listen(e, 'before_execute', _guard_execute)
    return e


_engine = _make_engine(DATABASE_URL)


def get_db_url() -> str:
    return str(_engine.url)


def get_engine():
    """返回当前底层 SQLAlchemy Engine（供测试/运维做原生查询用）。

    业务代码应通过 SessionLocal 走 ORM；仅在需要 raw_connection 等底层能力时使用。
    """
    return _engine


def configure_engine(db_url: str):
    global _engine, SessionLocal
    _engine = _make_engine(db_url)
    SessionLocal = sessionmaker(class_=SecureSession, bind=_engine)


# ── SecureSession ──
class SecureSession(Session):
    pass


SessionLocal = sessionmaker(class_=SecureSession, bind=_engine)


@event.listens_for(SecureSession, 'before_flush')
def _guard_flush(session, context, instances):
    if _is_write_permitted():
        return
    if session.new or session.dirty or session.deleted:
        raise BusinessError(code=ErrorCode.SECURITY_VIOLATION,
                            message="ORM 操作被拦截：请通过 API 操作")


class Base(DeclarativeBase):
    pass


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    import models
    import models_finance
    import models_bank
    # init_db 执行 create_all / 迁移 / 触发器创建等 DDL 操作，需临时进入维护模式
    # 放行 _guard_execute 的 DDL 红线（否则被 SECURITY_VIOLATION 拦截）。
    # 调用方（main.py startup / 测试）无需关心，函数返回后自动恢复。
    set_maintenance_mode(True)
    try:
        Base.metadata.create_all(bind=_engine)
        _auto_migrate_columns()
        _migrate_asset_code_unique_to_account_scoped()
        _sync_bank_account_balance_from_ledger()
        _create_immutable_triggers()
        _init_pending_confirms_table()
    finally:
        set_maintenance_mode(False)


def _init_pending_confirms_table():
    """创建 pending_confirms 表（幂等），confirm_middleware 依赖此表"""
    prev = _maintenance_mode
    set_maintenance_mode(True)
    try:
        from sqlalchemy import text
        with _engine.connect() as conn:
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
    finally:
        set_maintenance_mode(prev)

    # confirm_middleware 模块级初始化（在导入 main.py 时发生）
    # 也会通过 ConfirmStore.__init__ 尝试建表，已移除 __init__
    # 中的 _init_db 调用，改为懒建表（首次 put/remove 时自动创建）。
    # 此处提前创建好，confirm_store 后续操作不再触达 DDL。


def _create_immutable_triggers():
    """为真相源流水表创建 SQLite BEFORE UPDATE 触发器（数据库级防护）

    SQLAlchemy 的 before_update 事件只拦截 ORM 操作，不拦截原始 SQL UPDATE。
    此触发器在数据库层阻断所有 UPDATE，补全 BR-8 防护链。

    受保护表：
      - stock_moves（库存流水，BR-7）
      - account_moves（会计凭证，BR-8）
      - fixed_asset_depreciations（折旧流水，BR-8）

    系统内部冲红/反向操作均通过 INSERT 新记录实现，不 UPDATE 既有记录。
    """
    from sqlalchemy import text

    triggers = [
        ("trg_immutable_stock_moves", "stock_moves",
         "StockMove 是库存真相源，禁止 UPDATE，错误更正请通过红冲调整单实现"),
        ("trg_immutable_account_moves", "account_moves",
         "AccountMove 是会计凭证真相源，禁止 UPDATE，错误更正请通过红字冲销实现"),
        ("trg_immutable_depreciations", "fixed_asset_depreciations",
         "FixedAssetDepreciation 是折旧真相源，禁止 UPDATE"),
    ]

    # 进入维护模式绕过 DDL 拦截
    prev = _maintenance_mode
    set_maintenance_mode(True)
    try:
        with _engine.connect() as conn:
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
    finally:
        set_maintenance_mode(prev)


def _auto_migrate_columns():
    """自动检测并添加模型中新增但数据库表缺少的列（仅 SQLite，仅新增列，不删除/修改）

    解决 create_all 不更新已有表结构的问题，避免模型加字段后 INSERT 报错。
    """
    from sqlalchemy import inspect, text
    inspector = inspect(_engine)

    for table_name, mapper in Base.metadata.tables.items():
        if not inspector.has_table(table_name):
            continue
        db_cols = {col["name"] for col in inspector.get_columns(table_name)}
        model_cols = {col.name for col in mapper.columns}

        missing = model_cols - db_cols
        if not missing:
            continue

        for col_name in missing:
            col_obj = mapper.columns[col_name]
            col_type = col_obj.type.compile(_engine.dialect)
            default = ""
            if col_obj.default is not None and hasattr(col_obj.default, "arg"):
                val = col_obj.default.arg
                if isinstance(val, bool):
                    default = f" DEFAULT {1 if val else 0}"
                elif isinstance(val, (int, float)):
                    default = f" DEFAULT {val}"
                elif isinstance(val, str):
                    default = f" DEFAULT '{val}'"
            nullable = "" if col_obj.nullable else " NOT NULL"
            sql = f"ALTER TABLE {table_name} ADD COLUMN {col_name} {col_type}{default}{nullable}"
            with _engine.connect() as conn:
                conn.execute(text(sql))
                conn.commit()
            print(f"[AutoMigrate] {table_name}: added column {col_name} ({col_type})")


def _migrate_asset_code_unique_to_account_scoped():
    """将 fixed_assets/intangible_assets.asset_code 从全局唯一迁移为 (account_id, asset_code) 联合唯一

    背景：原模型 asset_code=Column(unique=True) 是全局唯一，跨账本使用相同编码（如 FA-001）
    会冲突。BR-19 修复改为账本内唯一。SQLite 不能直接修改约束，需重建索引。

    幂等：若新约束已存在则跳过；若存在旧全局 unique 索引则先 drop。
    """
    from sqlalchemy import inspect, text

    inspector = inspect(_engine)

    # 同时处理 fixed_assets 和 intangible_assets
    targets = [
        ("fixed_assets", "uix_account_asset_code"),
        ("intangible_assets", "uix_intangible_account_asset_code"),
    ]

    set_maintenance_mode(True)
    try:
        for table_name, new_constraint_name in targets:
            if not inspector.has_table(table_name):
                continue

            with _engine.connect() as conn:
                # 查看现有索引
                indexes = inspector.get_indexes(table_name)
                existing_index_names = {idx["name"] for idx in indexes}

                # 如果新约束已存在，跳过
                if new_constraint_name in existing_index_names:
                    continue

                # 查找并删除 asset_code 的单列 unique 索引
                for idx in indexes:
                    idx_name = idx["name"]
                    col_names = idx.get("column_names", [])
                    is_unique = idx.get("unique", False)
                    # 只处理 asset_code 单列 unique 索引
                    if is_unique and col_names == ["asset_code"]:
                        # SQLite 自动索引名形如 sqlite_autoindex_<table>_N
                        try:
                            conn.execute(text(f"DROP INDEX IF EXISTS {idx_name}"))
                            conn.commit()
                            print(f"[AssetCodeMigrate] {table_name}: dropped old unique index: {idx_name}")
                        except Exception as e:
                            print(f"[AssetCodeMigrate] {table_name}: WARN: could not drop {idx_name}: {e}")
                        break

                # 创建新的联合 unique 约束
                try:
                    conn.execute(text(
                        f"CREATE UNIQUE INDEX IF NOT EXISTS {new_constraint_name} "
                        f"ON {table_name} (account_id, asset_code)"
                    ))
                    conn.commit()
                    print(f"[AssetCodeMigrate] {table_name}: created (account_id, asset_code) unique index")
                except Exception as e:
                    print(f"[AssetCodeMigrate] {table_name}: WARN: could not create new index: {e}")
    finally:
        set_maintenance_mode(False)


def _sync_bank_account_balance_from_ledger():
    """启动时把 BankAccount.balance 对齐到 1002 科目余额（历史数据修复 + 持续一致性）

    背景：期初余额流程只过账到 1002 总账科目，未同步 BankAccount.balance。
    导致：
      - 付款/收款校验用 BankAccount.balance（缺期初）
      - 前端展示用 BankAccount.balance（缺期初）
      - 银行对账 _read_book_balance 读 1002（正确），但 BankAccount.balance 错

    修复策略：每次启动遍历所有 BankAccount，把 balance 重置为 1002 科目余额。
    幂等：以 1002 科目为单一真相源，BankAccount.balance 始终跟随。
    """
    from sqlalchemy import inspect, text
    from decimal import Decimal

    inspector = inspect(_engine)
    if not inspector.has_table("bank_accounts") or not inspector.has_table("account_moves"):
        return
    if not inspector.has_table("accounts") or not inspector.has_table("ledgers"):
        return
    if not inspector.has_table("ledger_accounts") or not inspector.has_table("account_move_lines"):
        return

    set_maintenance_mode(True)
    try:
        with _engine.connect() as conn:
            # 取每个 BankAccount 对应账本的 1002 科目余额
            rows = conn.execute(text(
                """
                SELECT ba.id AS bank_account_id, ba.account_id, ba.bank_name,
                       COALESCE(SUM(aml.debit_l2), 0) - COALESCE(SUM(aml.credit_l2), 0) AS ledger_balance,
                       ba.balance_l4 AS current_balance
                FROM bank_accounts ba
                LEFT JOIN accounts a ON a.id = ba.account_id
                LEFT JOIN ledgers l ON l.code = a.code
                LEFT JOIN ledger_accounts la ON la.ledger_id = l.id AND la.code = '1002'
                LEFT JOIN account_move_lines aml ON aml.ledger_account_id = la.id
                LEFT JOIN account_moves am ON am.id = aml.move_id
                GROUP BY ba.id, ba.account_id, ba.bank_name, ba.balance_l4
                """
            )).fetchall()

            updated = 0
            for r in rows:
                bank_account_id = r._mapping["bank_account_id"]
                # 注意 SQL 里列顺序：bank_account_id, account_id, bank_name, ledger_balance, current_balance
                # 不能用 r[2]——那是 bank_name 字符串，会抛 decimal.ConversionSyntax
                ledger_balance = Decimal(str(r._mapping["ledger_balance"] or 0)).quantize(Decimal("0.01"))
                current_balance = Decimal(str(r._mapping["current_balance"] or 0)).quantize(Decimal("0.01"))
                if ledger_balance != current_balance:
                    conn.execute(text(
                        "UPDATE bank_accounts SET balance_l4 = :bal WHERE id = :id"
                    ), {"bal": float(ledger_balance), "id": bank_account_id})
                    print(f"[BankSync] bank_account#{bank_account_id} balance: "
                          f"{current_balance} → {ledger_balance}")
                    updated += 1
            if updated > 0:
                conn.commit()
                print(f"[BankSync] 已同步 {updated} 个 BankAccount.balance 与 1002 科目")
    finally:
        set_maintenance_mode(False)

