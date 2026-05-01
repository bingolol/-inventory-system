from fastapi import Header, HTTPException, Depends
from sqlalchemy.orm import Session
from database import get_db
import models


def get_account_id(x_account_id: int = Header(..., alias="X-Account-ID")):
    """从请求头获取当前选择的账本ID"""
    return x_account_id