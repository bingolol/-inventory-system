"""集成测试公共辅助函数
供各测试文件导入使用，减少重复代码。
"""
from datetime import datetime
from database import SessionLocal
from models import Account


def get_entity_id(resp_json):
    """从 API 响应中提取实体 ID（支持 AI Gateway 包装格式 + OperationResult + 传统格式）"""
    if isinstance(resp_json, dict):
        # AI Gateway 格式: {ok, entity: {success, entity_id, data: {id, ...}}}
        if "entity" in resp_json and isinstance(resp_json["entity"], dict):
            ent = resp_json["entity"]
            if "entity_id" in ent:
                return ent["entity_id"]
            if "data" in ent and isinstance(ent["data"], dict) and "id" in ent["data"]:
                return ent["data"]["id"]
            if "id" in ent:
                return ent["id"]
        # 传统 OperationResult: {success, entity_id, data: {id, ...}}
        if "entity_id" in resp_json:
            return resp_json["entity_id"]
        if "data" in resp_json and isinstance(resp_json["data"], dict) and "id" in resp_json["data"]:
            return resp_json["data"]["id"]
        if "id" in resp_json:
            return resp_json["id"]
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
