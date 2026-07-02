import hashlib
import secrets
import time
from datetime import datetime, timedelta
from fastapi import APIRouter, HTTPException, Depends, Header
from sqlalchemy.orm import Session
from sqlalchemy import or_
from database import get_db
import models
from models import Account
from schemas.user import (
    LoginRequest, LoginResponse,
    RefreshRequest, RefreshResponse,
    ChangePasswordRequest, UserInfoResponse, LogoutResponse,
)

router = APIRouter(tags=["认证"])

ACCESS_TOKEN_TTL = timedelta(hours=2)
REFRESH_TOKEN_TTL = timedelta(days=7)


@router.get("/api/auth/has-users")
def has_users(db: Session = Depends(get_db)):
    count = db.query(models.User).count()
    return {"hasUsers": count > 0}


@router.post("/api/auth/register", response_model=LoginResponse)
def register(body: LoginRequest, db: Session = Depends(get_db)):
    if db.query(models.User).count() > 0:
        raise HTTPException(status_code=403, detail="系统已初始化，无法重复注册")

    account = db.query(models.Account).first()
    if account is None:
        account = Account(name="默认账本", type="company", code="default", taxpayer_type_l3="small_scale")
        db.add(account)
        db.flush()

    salt = _generate_salt()
    user = models.User(
        username=body.username,
        password_hash=_hash_password(body.password, salt),
        password_salt=salt,
        account_id=account.id,
        is_active=True,
    )
    db.add(user)
    db.flush()

    access_raw, access_hash, refresh_raw, refresh_hash = _make_token_pair()
    now = datetime.now()
    token = models.UserToken(
        user_id=user.id,
        access_token_hash=access_hash,
        refresh_token_hash=refresh_hash,
        access_expires_at=now + ACCESS_TOKEN_TTL,
        refresh_expires_at=now + REFRESH_TOKEN_TTL,
    )
    db.add(token)
    db.commit()

    return LoginResponse(
        access_token=access_raw,
        refresh_token=refresh_raw,
        username=user.username,
        account_id=user.account_id,
        expires_in=int(ACCESS_TOKEN_TTL.total_seconds()),
    )

_OLD_SECRET = "inventory-system-2024"


def _generate_salt() -> str:
    return secrets.token_hex(16)


def _hash_password(password: str, salt: str) -> str:
    return hashlib.pbkdf2_hmac('sha256', password.encode(), salt.encode(), 100000).hex()


def _old_hash(password: str) -> str:
    return hashlib.sha256(f"{password}:{_OLD_SECRET}".encode()).hexdigest()


def _make_token_pair() -> tuple[str, str, str, str]:
    access_raw = secrets.token_urlsafe(32)
    refresh_raw = secrets.token_urlsafe(32)
    return (
        access_raw,
        hashlib.sha256(access_raw.encode()).hexdigest(),
        refresh_raw,
        hashlib.sha256(refresh_raw.encode()).hexdigest(),
    )


def get_user_from_token(token: str, db: Session) -> models.User | None:
    token_hash = hashlib.sha256(token.encode()).hexdigest()
    now = datetime.now()
    row = db.query(models.UserToken).filter(
        models.UserToken.access_token_hash == token_hash,
        models.UserToken.access_expires_at > now,
    ).first()
    if row is None:
        return None
    user = db.query(models.User).filter(models.User.id == row.user_id, models.User.is_active == True).first()
    return user


@router.post("/api/auth/login", response_model=LoginResponse)
def login(body: LoginRequest, db: Session = Depends(get_db)):
    user = db.query(models.User).filter(
        models.User.username == body.username,
        models.User.is_active == True,
    ).first()
    if user is None:
        raise HTTPException(status_code=401, detail="用户名或密码错误")

    # 兼容旧 SHA256 哈希：password_salt 为 NULL 表示旧格式
    if user.password_salt is None:
        if user.password_hash != _old_hash(body.password):
            raise HTTPException(status_code=401, detail="用户名或密码错误")
        # 升级为新哈希
        user.password_salt = _generate_salt()
        user.password_hash = _hash_password(body.password, user.password_salt)
        db.flush()
    else:
        if user.password_hash != _hash_password(body.password, user.password_salt):
            raise HTTPException(status_code=401, detail="用户名或密码错误")

    access_raw, access_hash, refresh_raw, refresh_hash = _make_token_pair()
    now = datetime.now()
    token = models.UserToken(
        user_id=user.id,
        access_token_hash=access_hash,
        refresh_token_hash=refresh_hash,
        access_expires_at=now + ACCESS_TOKEN_TTL,
        refresh_expires_at=now + REFRESH_TOKEN_TTL,
    )
    db.add(token)
    db.commit()

    return LoginResponse(
        access_token=access_raw,
        refresh_token=refresh_raw,
        username=user.username,
        account_id=user.account_id,
        expires_in=int(ACCESS_TOKEN_TTL.total_seconds()),
    )


@router.post("/api/auth/refresh", response_model=RefreshResponse)
def refresh_token(body: RefreshRequest, db: Session = Depends(get_db)):
    refresh_hash = hashlib.sha256(body.refresh_token.encode()).hexdigest()
    now = datetime.now()
    row = db.query(models.UserToken).filter(
        models.UserToken.refresh_token_hash == refresh_hash,
        models.UserToken.refresh_expires_at > now,
    ).first()
    if row is None:
        raise HTTPException(status_code=401, detail="刷新令牌无效或已过期")

    user = db.query(models.User).filter(models.User.id == row.user_id, models.User.is_active == True).first()
    if user is None:
        raise HTTPException(status_code=401, detail="用户不存在或已禁用")

    # 生成新 access token，复用同一 refresh token
    access_raw = secrets.token_urlsafe(32)
    access_hash = hashlib.sha256(access_raw.encode()).hexdigest()
    row.access_token_hash = access_hash
    row.access_expires_at = now + ACCESS_TOKEN_TTL
    db.commit()

    return RefreshResponse(
        access_token=access_raw,
        expires_in=int(ACCESS_TOKEN_TTL.total_seconds()),
    )


@router.post("/api/auth/change-password")
def change_password(body: ChangePasswordRequest, db: Session = Depends(get_db),
                    authorization: str = Header("", alias="Authorization")):
    user = _resolve_user(authorization, db)
    if user is None:
        raise HTTPException(status_code=401, detail="未登录或令牌无效")

    # 验证旧密码（兼容两种哈希格式）
    if user.password_salt is None:
        if user.password_hash != _old_hash(body.old_password):
            raise HTTPException(status_code=422, detail="旧密码错误")
    else:
        if user.password_hash != _hash_password(body.old_password, user.password_salt):
            raise HTTPException(status_code=422, detail="旧密码错误")

    # 换新盐 + 新哈希
    user.password_salt = _generate_salt()
    user.password_hash = _hash_password(body.new_password, user.password_salt)
    # 使该用户所有 token 失效
    db.query(models.UserToken).filter(models.UserToken.user_id == user.id).delete()
    db.commit()

    return {"message": "密码修改成功，请重新登录"}


@router.get("/api/auth/me", response_model=UserInfoResponse)
def get_me(db: Session = Depends(get_db),
           authorization: str = Header("", alias="Authorization")):
    user = _resolve_user(authorization, db)
    if user is None:
        raise HTTPException(status_code=401, detail="未登录或令牌无效")
    return UserInfoResponse(username=user.username, account_id=user.account_id, is_active=user.is_active)


@router.post("/api/auth/logout", response_model=LogoutResponse)
def logout(db: Session = Depends(get_db),
           authorization: str = Header("", alias="Authorization")):
    user = _resolve_user(authorization, db)
    if user is None:
        raise HTTPException(status_code=401, detail="未登录或令牌无效")
    # 使该用户所有 token 失效
    db.query(models.UserToken).filter(models.UserToken.user_id == user.id).delete()
    db.commit()
    return LogoutResponse(message="已退出登录")


def _resolve_user(authorization: str, db: Session) -> models.User | None:
    if not authorization.startswith("Bearer "):
        return None
    token = authorization[7:]
    return get_user_from_token(token, db)
