"""测试全局配置 — 使用临时数据库 + 将 backend 目录加入 sys.path"""
import sys
import os
import tempfile

# 将 backend 目录插入 sys.path，使测试能直接 import backend 模块
BACKEND_DIR = os.path.join(os.path.dirname(__file__), "..", "backend")
BACKEND_DIR = os.path.abspath(BACKEND_DIR)
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)

# ── 在 database 模块首次被 import 前替换为临时数据库 ──
# 先 import database 并替换全局变量，确保后续 from database import SessionLocal
# 拿到的是测试用 SessionLocal（而非生产数据库）
import database as _database
import workspace as _workspace

_workspace.ensure_workspace()

_tmp = tempfile.NamedTemporaryFile(suffix=".test.db", delete=False)
_TMP_DB_PATH = _tmp.name
_tmp.close()

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

_TEST_DB_URL = f"sqlite:///{_TMP_DB_PATH}"
_test_engine = create_engine(_TEST_DB_URL, connect_args={"check_same_thread": False})
_test_session_factory = sessionmaker(autocommit=False, autoflush=False, bind=_test_engine)

# 保存原始值
_orig_engine = _database.engine
_orig_session = _database.SessionLocal
_orig_db_path = _database.DB_PATH
_orig_db_url = _database.DATABASE_URL

# 替换
_database.engine = _test_engine
_database.SessionLocal = _test_session_factory
_database.DB_PATH = _TMP_DB_PATH
_database.DATABASE_URL = _TEST_DB_URL

# 建表 + 种子数据
_database.init_db()


def _cleanup_test_db():
    """恢复原始值并清理临时文件"""
    _database.engine = _orig_engine
    _database.SessionLocal = _orig_session
    _database.DB_PATH = _orig_db_path
    _database.DATABASE_URL = _orig_db_url
    _test_engine.dispose()
    try:
        os.unlink(_TMP_DB_PATH)
    except OSError:
        pass


import atexit
atexit.register(_cleanup_test_db)
