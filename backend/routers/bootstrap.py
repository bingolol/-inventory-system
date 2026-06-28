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

    account = Account(name="公司账本", type="company", code="company", taxpayer_type="small_scale")
    db.add(account)
    db.flush()

    get_or_create_ledger_id(db, account.id)

    import hashlib
    password_hash = hashlib.sha256(b"admin:inventory-system-2024").hexdigest()
    db.add(User(username="admin", password_hash=password_hash, account_id=account.id, is_active=True))

    db.commit()
    return {"status": "ok", "account_id": account.id}
