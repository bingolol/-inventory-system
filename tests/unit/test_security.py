"""双保险安全方案 - 权限拦截单元测试"""
import pytest
from sqlalchemy import text, create_engine, event
from sqlalchemy.orm import sessionmaker
from database import Base, SecureSession, _guard_execute


@pytest.fixture
def db():
    """为安全测试创建专用 in-memory 引擎 + SecureSession"""
    import database
    from database import set_maintenance_mode
    import models  # noqa: F401
    import models_finance  # noqa: F401
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    event.listen(engine, 'before_execute', _guard_execute)
    set_maintenance_mode(True)
    Base.metadata.create_all(bind=engine)
    set_maintenance_mode(False)
    Session = sessionmaker(class_=SecureSession, bind=engine)
    session = Session()
    yield session
    set_maintenance_mode(True)
    session.close()


class TestWriteToken:
    """1.3 有令牌放行 ORM add"""

    def test_orm_add_with_token_allowed(self, db):
        from database import _request_write_perm
        from models import Product, Account
        token = _request_write_perm.set(True)
        acc = Account(name="test", type="company", code="test", taxpayer_type_l3="small_scale")
        db.add(acc)
        db.flush()
        p = Product(name="token-test", account_id=acc.id,
                    purchase_price_l3=10, sale_price_l3=20, unit="个")
        db.add(p)
        db.commit()
        _request_write_perm.reset(token)


class TestRawDML:
    """1.4~1.6 text() DML + CTE 拦截"""

    @pytest.fixture(autouse=True)
    def no_maintenance(self):
        from database import set_maintenance_mode
        set_maintenance_mode(False)

    def test_text_delete_without_token_blocked(self, db):
        from errors import BusinessError
        with pytest.raises(BusinessError, match="直接写"):
            db.execute(text("DELETE FROM products WHERE 1=0"))
            db.commit()

    def test_text_insert_without_token_blocked(self, db):
        from errors import BusinessError
        with pytest.raises(BusinessError, match="直接写"):
            db.execute(text("INSERT INTO products (name) VALUES ('x')"))
            db.commit()

    def test_text_update_without_token_blocked(self, db):
        from errors import BusinessError
        with pytest.raises(BusinessError, match="直接写"):
            db.execute(text("UPDATE products SET name='x' WHERE 1=0"))
            db.commit()

    def test_text_replace_without_token_blocked(self, db):
        from errors import BusinessError
        with pytest.raises(BusinessError, match="直接写"):
            db.execute(text("REPLACE INTO products (id, name) VALUES (999, 'x')"))
            db.commit()

    def test_cte_with_delete_blocked(self, db):
        from errors import BusinessError
        from database import set_maintenance_mode
        set_maintenance_mode(False)
        with pytest.raises(BusinessError, match="CTE"):
            db.execute(text("WITH d AS (DELETE FROM products WHERE id=1) SELECT * FROM d"))
            db.commit()


class TestDDL:
    """1.7~1.8 DDL 红线 + 表名误杀防护"""

    def test_drop_table_blocked(self, db):
        from errors import BusinessError
        with pytest.raises(BusinessError, match="DDL"):
            db.execute(text("DROP TABLE IF EXISTS products"))
            db.commit()

    def test_alter_table_blocked(self, db):
        from errors import BusinessError
        with pytest.raises(BusinessError, match="DDL"):
            db.execute(text("ALTER TABLE products ADD COLUMN x INTEGER"))
            db.commit()

    def test_select_from_create_table_ok(self, db):
        db.execute(text("SELECT * FROM sqlite_master WHERE name='no_such_table'"))
        db.commit()

    def test_select_from_drop_table_ok(self, db):
        db.execute(text("SELECT count(*) FROM sqlite_master WHERE name='drop_tmp'"))
        db.commit()


class TestMaintenanceMode:
    """1.1 维护模式豁免 DDL"""

    def test_maintenance_mode_lets_ddl_through(self, db):
        from database import set_maintenance_mode
        set_maintenance_mode(True)
        db.execute(text("CREATE TABLE IF NOT EXISTS _test_ddl_guard (id INTEGER)"))
        db.commit()
        db.execute(text("DROP TABLE IF EXISTS _test_ddl_guard"))
        db.commit()
        set_maintenance_mode(False)

    def test_no_maintenance_mode_blocks_ddl(self, db):
        from database import set_maintenance_mode
        from errors import BusinessError
        set_maintenance_mode(False)
        with pytest.raises(BusinessError, match="DDL"):
            db.execute(text("CREATE TABLE IF NOT EXISTS _test_ddl_guard (id INTEGER)"))
            db.commit()


class TestORMMutation:
    """1.2 无令牌拦 ORM add/flush"""


    @pytest.fixture(autouse=True)
    def no_maintenance(self):
        from database import set_maintenance_mode
        set_maintenance_mode(False)

    def test_orm_add_without_token_blocked(self, db):
        from errors import BusinessError
        from models import Product
        p = Product(name="test", purchase_price_l3=10, sale_price_l3=20, unit="个")
        db.add(p)
        with pytest.raises(BusinessError, match="ORM"):
            db.commit()

    def test_orm_query_read_only_ok(self, db):
        from models import Product
        rows = db.query(Product).all()
        assert isinstance(rows, list)
