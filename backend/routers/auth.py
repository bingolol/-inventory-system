"""登录认证路由"""
import hashlib
import time
import secrets
from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from database import get_db
import models
from schemas.user import LoginRequest, LoginResponse

router = APIRouter(tags=["认证"])

# 内存 token 存储：username → {"token_hash": str, "expiry": float}
_tokens: dict[str, dict] = {}
TOKEN_TTL = 86400  # 24 小时

_SECRET = "inventory-system-2024"  # 固定盐值


def _hash_password(password: str) -> str:
    return hashlib.sha256(f"{password}:{_SECRET}".encode()).hexdigest()


def _generate_token(username: str) -> str:
    expiry = time.time() + TOKEN_TTL
    raw = f"{username}:{_SECRET}:{int(expiry)}"
    token = hashlib.sha256(raw.encode()).hexdigest()
    _tokens[username] = {"token_hash": token, "expiry": expiry}
    return token


def validate_token(token: str) -> tuple[str, int] | None:
    """校验 token，返回 (username, account_id) 或 None"""
    for username, data in _tokens.items():
        if data["token_hash"] == token and time.time() < data["expiry"]:
            return username, 0  # account_id 由调用方查 DB
    return None


def get_authenticated_username(token: str, db: Session) -> str | None:
    """从 token 解析用户名"""
    result = validate_token(token)
    if not result:
        return None
    username, _ = result
    user = db.query(models.User).filter(
        models.User.username == username,
        models.User.is_active == True,
    ).first()
    return user.username if user else None


@router.post("/api/auth/login", response_model=LoginResponse)
def login(body: LoginRequest, db: Session = Depends(get_db)):
    user = db.query(models.User).filter(
        models.User.username == body.username,
        models.User.is_active == True,
    ).first()
    if not user or user.password_hash != _hash_password(body.password):
        raise HTTPException(status_code=401, detail="用户名或密码错误")
    token = _generate_token(user.username)
    return LoginResponse(token=token, username=user.username, account_id=user.account_id)
