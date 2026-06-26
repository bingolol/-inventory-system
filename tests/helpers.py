"""集成测试公共辅助函数
供各测试文件导入使用，减少重复代码。
"""
from datetime import datetime
from database import SessionLocal
from models import Account


def get_entity_id(resp_json):
    """从 API 响应中提取实体 ID"""
    if isinstance(resp_json, dict):
        if "id" in resp_json:
            return resp_json["id"]
        if "data" in resp_json and isinstance(resp_json["data"], dict) and "id" in resp_json["data"]:
            return resp_json["data"]["id"]
        if "entity_id" in resp_json:
            return resp_json["entity_id"]
    return None


def uniq(prefix):
    """生成唯一标识前缀（基于当前时间，保证并发安全）"""
    return f"{prefix}-{datetime.now().strftime('%H%M%S%f')}"


def get_account_id():
    """获取第一个账本 ID"""
    db = SessionLocal()
    try:
        acc = db.query(Account).first()
        return acc.id if acc else 1
    finally:
        db.close()
