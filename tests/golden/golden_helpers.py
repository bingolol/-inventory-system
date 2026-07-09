"""Golden Tests 公共辅助函数

仅保留与 backend 完全解耦的工具：
- make_engine: 创建独立临时数据库引擎
- _get_id: 从 API 响应中提取 entity ID

注意：不再提供任何直接查询 AccountMoveLine / LedgerAccount 的辅助函数，
黄金测试的 L3 验证必须通过报表 API 完成。
"""
import os
import tempfile
import uuid

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker


def make_engine():
    """创建独立的临时 SQLite 引擎（每个测试文件隔离）"""
    TEST_DB = os.path.join(tempfile.gettempdir(), f"test_golden_{uuid.uuid4().hex[:8]}.db")
    _engine = create_engine(
        f"sqlite:///{TEST_DB}",
        connect_args={"check_same_thread": False},
    )
    _SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=_engine)
    return _engine, _SessionLocal


def _get_id(resp, label=""):
    """从各种响应格式中提取 entity ID"""
    data = resp.json()
    eid = data.get("entity_id") or data.get("id")
    if eid is None and "entity" in data:
        eid = data["entity"].get("entity_id") or data["entity"].get("id")
    if eid is None and "data" in data:
        if isinstance(data["data"], dict):
            eid = data["data"].get("id") or data["data"].get("entity_id")
    if eid is None and isinstance(data.get("data"), dict) and "advance" in data["data"]:
        eid = data["data"]["advance"].get("id")
    assert eid is not None, f"No entity id in {label} response: {data}"
    return int(eid)
