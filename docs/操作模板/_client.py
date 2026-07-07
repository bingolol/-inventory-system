"""HTTP 客户端 + 响应解析工具，供操作模板调用。

后端要求写操作带 X-Operator: ai 头（通过 AIGatewayMiddleware），
响应被包装为 {"ok": bool, "entity": {...}, ...} 格式。
GET 查询走原始格式。
"""
import os, json, requests as _req

_BASE = os.environ.get("INVENTORY_API_BASE", "http://localhost:8000")
_ACCOUNT_ID = None
_TIMEOUT = 30


def set_account(account_id):
    global _ACCOUNT_ID
    _ACCOUNT_ID = account_id


def _headers(operator=None):
    h = {"Content-Type": "application/json"}
    if _ACCOUNT_ID:
        h["X-Account-Id"] = str(_ACCOUNT_ID)
    if operator:
        h["X-Operator"] = operator
    return h


def _parse(resp):
    try:
        return resp.json()
    except Exception:
        return {"ok": False, "entity": {"error": {"code": "PARSE_ERROR", "message": resp.text[:500]}}}


def post(path, body):
    """POST JSON → 解析 dict。自动带 X-Operator: ai。"""
    try:
        r = _req.post(_BASE + path, json=body, headers=_headers("ai"), timeout=_TIMEOUT)
        return _parse(r)
    except _req.RequestException as e:
        return {"ok": False, "entity": {"error": {"code": "NETWORK_ERROR", "message": str(e)}}}


def put(path, body):
    """PUT JSON → 解析 dict。自动带 X-Operator: ai。"""
    try:
        r = _req.put(_BASE + path, json=body, headers=_headers("ai"), timeout=_TIMEOUT)
        return _parse(r)
    except _req.RequestException as e:
        return {"ok": False, "entity": {"error": {"code": "NETWORK_ERROR", "message": str(e)}}}


def get(path):
    """GET → 解析 dict。查询不走 AI gateway。"""
    try:
        r = _req.get(_BASE + path, headers=_headers(), timeout=_TIMEOUT)
        return _parse(r)
    except _req.RequestException as e:
        return {"error": {"code": "NETWORK_ERROR", "message": str(e)}}


def post_pending(path, body):
    """POST 危险操作（返回 202 confirm_token）。"""
    return post(path, body)


def put_pending(path, body):
    """PUT 危险操作（返回 202 confirm_token）。"""
    return put(path, body)


def confirm(token):
    """确认危险操作。"""
    return post("/api/confirm/" + token, {})


def cancel_pending(token):
    """取消危险操作。"""
    return post("/api/cancel/" + token, {})


def ping():
    """检查后端是否运行。"""
    try:
        r = _req.get(_BASE + "/api/bootstrap/init", timeout=5)
        return "ok" if r.status_code < 500 else f"unreachable ({r.status_code})"
    except _req.RequestException:
        return "unreachable"


# === 响应解析工具 ===


def is_ok(resp):
    if not isinstance(resp, dict):
        return False
    if "ok" in resp:
        return resp.get("ok") is True
    if "success" in resp:
        return resp.get("success") is True
    if "error" in resp:
        return False
    return True


def extract_id(resp):
    """从响应中提取实体 ID。"""
    if not isinstance(resp, dict):
        return None
    entity = resp.get("entity") if "entity" in resp else resp
    if not isinstance(entity, dict):
        entity = resp
    for key in ("id", "entity_id"):
        val = entity.get(key)
        if val is not None:
            return val
    if isinstance(entity.get("data"), dict):
        return entity["data"].get("id")
    return None


def extract_field(resp, key, default=None):
    """从响应中提取指定字段。"""
    if not isinstance(resp, dict):
        return default
    entity = resp.get("entity") if "entity" in resp else resp
    if isinstance(entity, dict) and key in entity:
        return entity[key]
    if isinstance(entity, dict) and isinstance(entity.get("data"), dict) and key in entity["data"]:
        return entity["data"][key]
    return resp.get(key, default)


def extract_data(resp):
    """提取 data 子对象。"""
    if not isinstance(resp, dict):
        return None
    entity = resp.get("entity") if "entity" in resp else resp
    if isinstance(entity, dict):
        return entity.get("data") or entity
    return entity


def extract_error(resp):
    """提取错误信息 dict。"""
    if not isinstance(resp, dict):
        return {"code": "UNKNOWN", "message": str(resp)}
    err = resp.get("error")
    if isinstance(err, dict):
        return err
    entity = resp.get("entity", {})
    if isinstance(entity, dict):
        err = entity.get("error")
        if isinstance(err, dict):
            return err
    return {"code": "UNKNOWN", "message": str(resp)}


def format_for_user(resp, label="操作"):
    """格式化操作为用户可读文本。"""
    if not isinstance(resp, dict):
        return f"{label}：返回格式异常"
    if is_ok(resp):
        msg = extract_field(resp, "summary") or extract_field(resp, "message") or ""
        eid = extract_id(resp)
        if eid:
            return f"{label}：成功 — ID={eid}" + (f"，{msg}" if msg else "")
        return f"{label}：成功" + (f" — {msg}" if msg else "")
    err = extract_error(resp)
    return f"{label}：失败 — {err.get('message', '未知错误')}"
