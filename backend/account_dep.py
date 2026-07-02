from fastapi import Header, Depends, HTTPException
from sqlalchemy.orm import Session
from database import get_db
import models


def get_account_id(x_account_id: int = Header(None, alias="X-Account-ID")) -> int:
    if x_account_id is None:
        raise HTTPException(status_code=401, detail="缺少 X-Account-ID 请求头，请先选择账本")
    return x_account_id


def get_operator(x_operator: str = Header("user", alias="X-Operator"),
                 authorization: str = Header("", alias="Authorization")) -> str:
    if authorization.startswith("Bearer "):
        token = authorization[7:]
        from routers.auth import get_user_from_token
        from database import SessionLocal
        db = SessionLocal()
        try:
            user = get_user_from_token(token, db)
            if user is not None:
                return user.username
        finally:
            db.close()
    if x_operator == "ai":
        return "ai"
    return "user"
