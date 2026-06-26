import sys
import os
from logging.config import fileConfig

from sqlalchemy import engine_from_config
from sqlalchemy import pool

from alembic import context

# 将 backend 目录加入 sys.path，以便 import database / models_finance
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(__file__)), "backend"))

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Interpret the config file for Python logging.
# This line sets up loggers basically.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# 使用应用的实际数据库路径覆盖配置中的 URL（仅当未通过编程方式设置时）
url = config.get_main_option("sqlalchemy.url")
if url is None or "driver://" in url:
    from workspace import get_db_path
    db_path = get_db_path()
    config.set_main_option("sqlalchemy.url", f"sqlite:///{db_path}")

# import models 注册所有表到 Base.metadata
import database
import models  # noqa — 注册业务模型（products, orders, invoices 等）
import models_finance  # noqa — 注册财务模块模型
target_metadata = database.Base.metadata


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        render_as_batch=True,
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode."""
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            render_as_batch=True,
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
