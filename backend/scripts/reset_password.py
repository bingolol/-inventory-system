import hashlib
import secrets
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from workspace import get_db_path
from models import User, UserToken


def _generate_salt() -> str:
    return secrets.token_hex(16)


def _hash_password(password: str, salt: str) -> str:
    return hashlib.pbkdf2_hmac('sha256', password.encode(), salt.encode(), 100000).hex()


def reset_password(username: str, new_password: str):
    db_path = get_db_path()
    if not os.path.exists(db_path):
        print(f"数据库不存在: {db_path}")
        return False

    engine = create_engine(f"sqlite:///{db_path}")
    Session = sessionmaker(bind=engine)
    db = Session()

    try:
        user = db.query(User).filter(User.username == username).first()
        if user is None:
            print(f"用户不存在: {username}")
            return False

        salt = _generate_salt()
        user.password_salt = salt
        user.password_hash = _hash_password(new_password, salt)
        user.is_active = True

        # 清空该用户所有 token，强制重新登录
        db.query(UserToken).filter(UserToken.user_id == user.id).delete()

        db.commit()
        print(f"用户 {username} 密码已重置，新密码长度为 {len(new_password)}，所有 token 已清空。")
        return True
    finally:
        db.close()


if __name__ == "__main__":
    if len(sys.argv) >= 3:
        username = sys.argv[1]
        new_password = sys.argv[2]
    else:
        username = "admin"
        new_password = "admin"

    reset_password(username, new_password)
