import hashlib
import secrets
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from database import get_db
from models import Account, User
from finance_integration import get_or_create_ledger_id

router = APIRouter()


@router.post("/init")
def bootstrap_init(db: Session = Depends(get_db)):
    existing = db.query(Account).first()
    if existing:
        return {"status": "already", "account_id": existing.id}

    account = Account(name="公司账本", type="company", code="company", taxpayer_type_l3="small_scale")
    db.add(account)
    db.flush()

    get_or_create_ledger_id(db, account.id)

    salt = secrets.token_hex(16)
    password_hash = hashlib.pbkdf2_hmac('sha256', b"admin", salt.encode(), 100000).hex()
    db.add(User(
        username="admin",
        password_hash=password_hash,
        password_salt=salt,
        account_id=account.id,
        is_active=True,
    ))

    db.commit()
    return {"status": "ok", "account_id": account.id}
