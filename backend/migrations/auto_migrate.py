"""自动检测并添加模型中新增但数据库表缺少的列（仅 SQLite）"""


def run(engine, Base):
    from sqlalchemy import inspect, text
    inspector = inspect(engine)

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
            col_type = col_obj.type.compile(engine.dialect)
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
            with engine.connect() as conn:
                conn.execute(text(sql))
                conn.commit()
            print(f"[AutoMigrate] {table_name}: added column {col_name} ({col_type})")
