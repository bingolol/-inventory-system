from fastapi import Header, Depends, HTTPException
from sqlalchemy.orm import Session
from database import get_db
import models

# 全局变量：存储前端通过 header 传来的当前账本ID
# 默认使用第一个账本（日运办公），如果未提供则报错

def get_account_id(x_account_id: int = Header(None, alias="X-Account-ID")) -> int:
    if x_account_id is None:
        raise HTTPException(status_code=401, detail="缺少 X-Account-ID 请求头，请先选择账本")
    return x_account_id


def get_operator(x_operator: str = Header("user", alias="X-Operator")) -> str:
    """识别操作者：前端请求默认 user，AI请求带 X-Operator: ai"""
    return x_operator