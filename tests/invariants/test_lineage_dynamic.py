"""动态血缘验证：执行引擎方法后检查实际写入是否匹配 @writes 声明

现有的 test_lineage_registry.py 只检查装饰器声明的格式正确性，
不验证函数实际运行时是否真的写入了声明中的字段。

本测试执行每个关键引擎方法，然后查询 DB 确认：
- 声明了 @writes 的表确实有新记录
- 关键字段值符合预期

运行：pytest tests/invariants/test_lineage_dynamic.py -v
"""
import uuid
import pytest
from decimal import Decimal
from datetime import datetime

pytestmark = pytest.mark.usefixtures("bootstrap_db")

from models import Account, StockMove, SaleItem, PurchaseItem, PurchaseOrder, SaleOrder
from models_finance import AccountMove, AccountMoveLine
from commands.base import dispatch
from commands.orders import CreateInvoice
from engine_inventory import InventoryEngine
from tests.factories import make_product
from utils import Q2


PURCHASE_DATE = datetime(2026, 6, 10)
SALE_DATE = datetime(2026, 6, 15)


def _aid(db):
    return db.query(Account).first().id


def _make_product_with_stock(db, aid, qty=100):
    """创建商品并初始化库存"""
    from models import Inventory
    pid = make_product(db, account_id=aid).id
    inv = db.query(Inventory).filter(
        Inventory.account_id == aid, Inventory.product_id == pid,
    ).first()
    if inv is None:
        inv = Inventory(account_id=aid, product_id=pid, quantity_l4=qty,
                        total_value_l4=Decimal("0"))
        db.add(inv)
        db.flush()
    return pid


def _create_purchase_via_invoice(db, aid, pid, qty, unit_price, tax_rate):
    """通过进项发票驱动创建采购单，返回 PurchaseOrder。"""
    unit_price = Decimal(str(unit_price))
    tax_rate = Decimal(str(tax_rate))
    amount_without_tax = (Decimal(str(qty)) * unit_price).quantize(Q2)
    tax_amount = (amount_without_tax * tax_rate).quantize(Q2)
    amount_with_tax = (amount_without_tax + tax_amount).quantize(Q2)
    inv = dispatch(CreateInvoice(
        account_id=aid, operator="tester",
        invoice_no=f"INV-LD-PUR-{uuid.uuid4().hex[:8]}",
        direction="in", invoice_type="ordinary",
        tax_rate=tax_rate,
        amount_without_tax=amount_without_tax,
        tax_amount=tax_amount,
        amount_with_tax=amount_with_tax,
        counterparty_name="测试供应商",
        seller_name="测试供应商", buyer_name="本公司",
        issue_date=PURCHASE_DATE.strftime("%Y-%m-%d"),
        purchase_order_action="auto_create",
        items=[{"product_id": pid, "quantity": qty,
                "unit_price": str(unit_price), "tax_rate": str(tax_rate)}],
    ), db)
    return db.query(PurchaseOrder).filter(PurchaseOrder.id == inv.related_order_id).first()


def _create_sale_via_invoice(db, aid, pid, qty, unit_price, tax_rate):
    """通过销项发票驱动创建销售单，返回 SaleOrder。"""
    unit_price = Decimal(str(unit_price))
    tax_rate = Decimal(str(tax_rate))
    amount_without_tax = (Decimal(str(qty)) * unit_price).quantize(Q2)
    tax_amount = (amount_without_tax * tax_rate).quantize(Q2)
    amount_with_tax = (amount_without_tax + tax_amount).quantize(Q2)
    inv = dispatch(CreateInvoice(
        account_id=aid, operator="tester",
        invoice_no=f"INV-LD-SALE-{uuid.uuid4().hex[:8]}",
        direction="out", invoice_type="ordinary",
        tax_rate=tax_rate,
        amount_without_tax=amount_without_tax,
        tax_amount=tax_amount,
        amount_with_tax=amount_with_tax,
        counterparty_name="测试客户",
        seller_name="本公司", buyer_name="测试客户",
        issue_date=SALE_DATE.strftime("%Y-%m-%d"),
        sale_order_action="auto_create",
        items=[{"product_id": pid, "quantity": qty,
                "unit_price": str(unit_price), "tax_rate": str(tax_rate)}],
    ), db)
    return db.query(SaleOrder).filter(SaleOrder.id == inv.related_order_id).first()


class TestStockMoveWrites:
    """InventoryEngine 每个方法执行后 StockMove 表确实有新记录"""

    def test_inbound_writes_stockmove(self, db):
        aid = _aid(db)
        pid = make_product(db, account_id=aid).id
        engine = InventoryEngine(db)
        engine.inbound(
            account_id=aid, product_id=pid, quantity=10,
            unit_price=Decimal("50"), source_type="test_dyn",
            source_id=99901, operator="tester",
            move_date=PURCHASE_DATE,
        )

        moves = db.query(StockMove).filter(
            StockMove.source_type == "test_dyn",
            StockMove.product_id == pid,
        ).all()
        assert len(moves) == 1
        assert moves[0].quantity_l1 == 10
        assert moves[0].unit_cost_l2 == Decimal("50")
        assert moves[0].total_cost_l2 == Decimal("500")

    def test_outbound_writes_stockmove(self, db):
        aid = _aid(db)
        pid = _make_product_with_stock(db, aid)

        InventoryEngine(db).outbound(
            account_id=aid, product_id=pid, quantity=5,
            source_type="test_dyn_out", source_id=99902, operator="tester",
            move_date=PURCHASE_DATE,
        )

        moves = db.query(StockMove).filter(
            StockMove.source_type == "test_dyn_out",
            StockMove.product_id == pid,
        ).all()
        assert len(moves) == 1
        assert moves[0].quantity_l1 == -5

    def test_reverse_writes_stockmove(self, db):
        aid = _aid(db)
        pid = make_product(db, account_id=aid).id
        # 通过进项发票驱动生成采购单 + 原始 StockMove，reverse 才能取到业务日期
        order = _create_purchase_via_invoice(db, aid, pid, 10, Decimal("50"), Decimal("0.01"))
        InventoryEngine(db).reverse(
            account_id=aid, product_id=pid, quantity=3,
            unit_cost=Decimal("50"), source_type="purchase_order",
            source_id=order.id, operator="tester",
        )
        moves = db.query(StockMove).filter(
            StockMove.source_type == "purchase_order_reversal",
            StockMove.product_id == pid,
        ).all()
        assert len(moves) >= 1


class TestOrderLifecycleWrites:
    """OrderLifecycle 执行后业务表确实有新记录"""

    def test_create_purchase_writes_items(self, db):
        aid = _aid(db)
        pid = make_product(db, account_id=aid).id

        order = _create_purchase_via_invoice(db, aid, pid, 5, Decimal("80"), Decimal("0.01"))

        items = db.query(PurchaseItem).filter(PurchaseItem.order_id == order.id).all()
        assert len(items) == 1
        assert items[0].quantity_l1 == 5

        moves = db.query(StockMove).filter(
            StockMove.source_type == "purchase_order",
            StockMove.source_id == order.id,
        ).all()
        assert len(moves) == 1
        assert moves[0].quantity_l1 == 5

    def test_create_sale_writes_items(self, db):
        aid = _aid(db)
        pid = _make_product_with_stock(db, aid)

        order = _create_sale_via_invoice(db, aid, pid, 3, Decimal("150"), Decimal("0.01"))

        items = db.query(SaleItem).filter(SaleItem.order_id == order.id).all()
        assert len(items) == 1
        assert items[0].quantity_l1 == 3

    def test_create_purchase_writes_accountmove(self, db):
        aid = _aid(db)
        pid = make_product(db, account_id=aid).id

        order = _create_purchase_via_invoice(db, aid, pid, 2, Decimal("100"), Decimal("0.01"))

        am = db.query(AccountMove).filter(
            AccountMove.source_model == "purchase_order",
            AccountMove.source_id == order.id,
        ).all()
        assert len(am) >= 1

    def test_create_sale_writes_accountmove(self, db):
        aid = _aid(db)
        pid = _make_product_with_stock(db, aid)

        order = _create_sale_via_invoice(db, aid, pid, 1, Decimal("200"), Decimal("0.01"))

        am = db.query(AccountMove).filter(
            AccountMove.source_model == "sale_order",
            AccountMove.source_id == order.id,
        ).all()
        assert len(am) >= 1


class TestJournalEngineWrites:
    """post_journal 写入 AccountMove + AccountMoveLine"""

    def test_post_journal_writes_moveline(self, db):
        from finance_integration import post_journal
        aid = _aid(db)

        move = post_journal(
            db=db, account_id=aid, move_type="expense",
            source={
                "date": PURCHASE_DATE,
                "amount": Decimal("500"),
                "expense_account_code": "6601",
                "credit_account_code": "2202",
                "source_model": "test_dyn_journal", "source_id": 0,
                "move_name": "TX-测试",
            },
        )

        assert move.date_l1 is not None
        assert move.amount_total_l2 == Decimal("500")

        lines = db.query(AccountMoveLine).filter(AccountMoveLine.move_id == move.id).all()
        assert len(lines) == 2
        debits = sum(l.debit_l2 for l in lines)
        credits = sum(l.credit_l2 for l in lines)
        assert debits == credits


class TestRegistrySelfConsistency:
    """验证 REGISTRY 中声明的函数存在且 ORM 模型字段存在"""

    def test_writes_property_exists_on_model(self):
        from lineage import REGISTRY
        import models as m
        import models_finance as mf

        for w in REGISTRY.writes:
            model_name = w.field.model_name
            field_name = w.field.field_name
            cls = getattr(m, model_name, None) or getattr(mf, model_name, None)
            assert cls is not None, f"模型 {model_name} 不存在（来自 {w.field.path}）"
            assert hasattr(cls, field_name), \
                f"字段 {model_name}.{field_name} 不存在（来自 {w.field.path}）"
