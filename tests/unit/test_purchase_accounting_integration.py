"""TDD: 采购单创建 → 自动生成会计凭证 + 库存流水

架构改造后，采购单必须由进项发票驱动创建（CreateInvoice direction='in',
purchase_order_action='auto_create'），禁止直接 CreateOrder。

RED→GREEN loop 验证 Buyer 侧的采购行为能正确触发会计系统和库存引擎。
"""
import pytest
from datetime import datetime
from decimal import Decimal

from models import Account, Product, PurchaseOrder, PurchaseItem
from models_finance import (
    Ledger, LedgerAccount, AccountMove, AccountMoveLine,
)
from commands.base import dispatch
from commands.orders import CreateInvoice, CancelOrder
from enums import OrderStatus, PaymentMethod
from models import StockMove


@pytest.fixture
def account(db):
    a = Account(id=1, name="测试账本", type="company", code="test",
                taxpayer_type_l3="general")
    db.add(a)
    db.commit()
    return a


@pytest.fixture
def ledger(db, account):
    l = Ledger(id=1, name="测试账本", type="company", code="test")
    db.add(l)
    db.commit()
    return l


@pytest.fixture
def accts(db, ledger):
    """创建采购单需要的科目"""
    seed = [
        ("1405", "库存商品", "asset"),
        ("2202", "应付账款", "liability"),
        ("222102", "应交增值税-进项税额", "liability"),
    ]
    result = {}
    for code, name, atype in seed:
        a = LedgerAccount(ledger_id=ledger.id, code=code, name=name, account_type=atype, is_leaf=True)
        db.add(a)
        db.flush()
        result[code] = a
    db.commit()
    return result


@pytest.fixture
def product(db):
    p = Product(id=1, account_id=1, name="测试商品", sku="T-001",
                purchase_price_l3=Decimal("10"), sale_price_l3=Decimal("20"),
                track_inventory_l3=True)
    db.add(p)
    db.commit()
    return p


class TestPurchaseCreateTriggersAccounting:
    """Tracer Bullet: 创建采购单（发票驱动）后，自动生成会计凭证和库存流水"""

    def test_creates_account_move_and_stock_move(self, db, account, accts, product):
        invoice = dispatch(CreateInvoice(
            account_id=account.id,
            operator="test",
            invoice_no="TEST-INV-PUR-001",
            direction="in",
            invoice_type="ordinary",
            tax_rate=Decimal("0.13"),
            amount_without_tax=Decimal("100.00"),
            tax_amount=Decimal("13.00"),
            amount_with_tax=Decimal("113.00"),
            counterparty_name="测试供应商",
            issue_date="2026-06-01",
            purchase_order_action="auto_create",
            items=[{
                "product_id": product.id,
                "quantity": 10,
                "unit_price": "10.00",
                "tax_rate": "0.13",
            }],
        ), db)
        db.flush()
        order = db.query(PurchaseOrder).filter(
            PurchaseOrder.id == invoice.related_order_id
        ).first()

        # ── RED 1: AccountMove 存在 ──
        moves = db.query(AccountMove).filter(
            AccountMove.source_model == "purchase_order",
            AccountMove.source_id == order.id,
        ).all()
        assert len(moves) == 1, "创建采购单后应生成 1 条会计凭证"
        move = moves[0]

        lines = db.query(AccountMoveLine).filter(
            AccountMoveLine.move_id == move.id
        ).order_by(AccountMoveLine.id).all()
        assert len(lines) == 3, "一般纳税人采购应有 3 行分录"

        codes = {}
        for line in lines:
            la = db.query(LedgerAccount).filter(
                LedgerAccount.id == line.ledger_account_id
            ).first()
            codes[la.code] = {"debit": line.debit_l2, "credit": line.credit_l2}

        assert codes["1405"]["debit"] == Decimal("100.00"), "库存商品借(不含税): 100.00"
        assert codes["222102"]["debit"] == Decimal("13.00"), "进项税借: 13.00"
        assert codes["2202"]["credit"] == Decimal("113.00"), "应付账款贷(价税合计): 113.00"

        # ── StockMove 存在 ──
        from models import StockMove
        stock_moves = db.query(StockMove).filter(
            StockMove.source_type == "purchase_order",
            StockMove.source_id == order.id,
        ).all()
        assert len(stock_moves) == 1, "创建采购单后应生成 1 条库存流水"
        sm = stock_moves[0]
        assert sm.quantity_l1 == 10
        # 发票驱动路径不传 total_price，unit_price_l1 保持不含税口径，
        # StockMove.total_cost_l2 为不含税金额(100.00)。
        # 采购凭证正确做价税分离(库存=100, 进项税=13), 见上方断言。
        assert sm.total_cost_l2 == Decimal("100.00")
        assert sm.product_id == product.id

    def test_invoice_path_unit_price_stays_tax_exclusive(self, db, account, accts, product):
        """负向测试：发票驱动路径不得走 _distribute_total_price 把 unit_price_l1 改成含税口径。

        回归 bug：_auto_generate_purchase_order 曾传 total_price=invoice.amount_with_tax_l1，
        触发 _distribute_total_price 修改 unit_price_l1 为含税价（10→11.30），
        导致库存记录虚高、价税分离失败。

        本测试断言：
          - PurchaseItem.unit_price_l1 == 不含税单价(10.00)，而非含税(11.30)
          - PurchaseItem.total_price_l1 == 不含税行小计(100.00)，而非含税(113.00)
          - PurchaseOrder.total_price_l1 == 价税合计(113.00)（订单总价仍为含税）
          - StockMove.total_cost_l2 == 不含税金额(100.00)
        """
        invoice = dispatch(CreateInvoice(
            account_id=account.id,
            operator="test",
            invoice_no="TEST-INV-PUR-NEG-001",
            direction="in",
            invoice_type="ordinary",
            tax_rate=Decimal("0.13"),
            amount_without_tax=Decimal("100.00"),
            tax_amount=Decimal("13.00"),
            amount_with_tax=Decimal("113.00"),
            counterparty_name="测试供应商",
            issue_date="2026-06-01",
            purchase_order_action="auto_create",
            items=[{
                "product_id": product.id,
                "quantity": 10,
                "unit_price": "10.00",
                "tax_rate": "0.13",
            }],
        ), db)
        db.flush()
        order = db.query(PurchaseOrder).filter(
            PurchaseOrder.id == invoice.related_order_id
        ).first()

        # 1. 明细单价保持不含税
        item = db.query(PurchaseItem).filter(
            PurchaseItem.order_id == order.id
        ).first()
        assert item.unit_price_l1 == Decimal("10.00"), \
            f"unit_price_l1 应为不含税 10.00，实际 {item.unit_price_l1}（含税 bug 会变成 11.30）"
        assert item.total_price_l1 == Decimal("100.00"), \
            f"明细 total_price_l1 应为不含税 100.00，实际 {item.total_price_l1}"

        # 2. 订单总价为价税合计（正确行为：total_price_l1 表示对外含税总额）
        assert order.total_price_l1 == Decimal("113.00"), \
            f"订单 total_price_l1 应为价税合计 113.00，实际 {order.total_price_l1}"
        assert order.tax_amount_l1 == Decimal("13.00"), \
            f"订单 tax_amount_l1 应为 13.00，实际 {order.tax_amount_l1}"

        # 3. 库存流水按不含税金额入账
        sm = db.query(StockMove).filter(
            StockMove.source_type == "purchase_order",
            StockMove.source_id == order.id,
        ).first()
        assert sm.total_cost_l2 == Decimal("100.00"), \
            f"StockMove.total_cost_l2 应为不含税 100.00，实际 {sm.total_cost_l2}（含税 bug 会变成 113.00）"

    def test_idempotent_post_journal(self, db, account, accts, product):
        """重复调用 FinanceEngine.record_purchase 不应重复生成凭证 (post_journal 幂等)"""
        from engine_finance import FinanceEngine
        invoice = dispatch(CreateInvoice(
            account_id=account.id,
            operator="test",
            invoice_no="TEST-INV-PUR-002",
            direction="in",
            invoice_type="ordinary",
            tax_rate=Decimal("0.13"),
            amount_without_tax=Decimal("100.00"),
            tax_amount=Decimal("13.00"),
            amount_with_tax=Decimal("113.00"),
            counterparty_name="测试供应商",
            issue_date="2026-06-01",
            purchase_order_action="auto_create",
            items=[{
                "product_id": product.id,
                "quantity": 10,
                "unit_price": "10.00",
                "tax_rate": "0.13",
            }],
        ), db)
        db.flush()
        order = db.query(PurchaseOrder).filter(
            PurchaseOrder.id == invoice.related_order_id
        ).first()

        fin = FinanceEngine(db, account.id)
        fin.record_purchase(order)
        db.flush()
        fin.record_purchase(order)
        db.flush()

        moves = db.query(AccountMove).filter(
            AccountMove.source_model == "purchase_order",
            AccountMove.source_id == order.id,
        ).count()
        assert moves == 1, "幂等: 同一条凭证不应重复生成"


class TestSmallScaleTaxpayerPurchase:
    """小规模纳税人：价税合计全部进成本，不进项税"""

    def test_small_scale_no_tax_separation(self, db):
        """自包含：创建小规模账本+科目+商品→采购→验证无进项税"""
        acc = Account(id=2, name="小规模", type="company", code="small_test",
                      taxpayer_type_l3="small_scale")
        db.add(acc)
        lgr = Ledger(id=2, name="小规模账本", type="company", code="small_test")
        db.add(lgr)
        for code, name, atype in [("1405", "库存商品", "asset"), ("2202", "应付账款", "liability")]:
            db.add(LedgerAccount(ledger_id=lgr.id, code=code, name=name, account_type=atype, is_leaf=True))
        prod = Product(id=2, account_id=2, name="测试商品2", sku="T-002",
                       purchase_price_l3=Decimal("10"), sale_price_l3=Decimal("20"),
                       track_inventory_l3=True)
        db.add(prod)
        db.commit()

        invoice = dispatch(CreateInvoice(
            account_id=acc.id,
            operator="test",
            invoice_no="TEST-INV-PUR-003",
            direction="in",
            invoice_type="ordinary",
            tax_rate=Decimal("0.01"),
            amount_without_tax=Decimal("100.00"),
            tax_amount=Decimal("0.00"),
            amount_with_tax=Decimal("100.00"),
            counterparty_name="测试供应商",
            issue_date="2026-06-01",
            purchase_order_action="auto_create",
            items=[{
                "product_id": prod.id,
                "quantity": 10,
                "unit_price": "10.00",
                "tax_rate": "0.01",
            }],
        ), db)
        db.flush()
        order = db.query(PurchaseOrder).filter(
            PurchaseOrder.id == invoice.related_order_id
        ).first()

        moves = db.query(AccountMove).filter(
            AccountMove.source_model == "purchase_order",
            AccountMove.source_id == order.id,
        ).all()
        assert len(moves) == 1

        lines = db.query(AccountMoveLine).filter(
            AccountMoveLine.move_id == moves[0].id
        ).order_by(AccountMoveLine.id).all()
        assert len(lines) == 2, "小规模纳税人：只有库存商品+应付账款，无进项税"

        codes = {}
        for line in lines:
            la = db.query(LedgerAccount).filter(
                LedgerAccount.id == line.ledger_account_id
            ).first()
            codes[la.code] = {"debit": line.debit_l2, "credit": line.credit_l2}

        assert codes["1405"]["debit"] == Decimal("100.00"), "小规模：全额100进成本"
        assert codes["2202"]["credit"] == Decimal("100.00"), "小规模：应付账款100"


class TestCancelPurchaseTriggersReversal:
    """取消采购单 → 冲红凭证 + 反向 StockMove"""

    def test_cancel_creates_reversal(self, db, account, accts, product):
        invoice = dispatch(CreateInvoice(
            account_id=account.id,
            operator="test",
            invoice_no="TEST-INV-PUR-004",
            direction="in",
            invoice_type="ordinary",
            tax_rate=Decimal("0.13"),
            amount_without_tax=Decimal("100.00"),
            tax_amount=Decimal("13.00"),
            amount_with_tax=Decimal("113.00"),
            counterparty_name="测试供应商",
            issue_date="2026-06-01",
            purchase_order_action="auto_create",
            items=[{
                "product_id": product.id,
                "quantity": 10,
                "unit_price": "10.00",
                "tax_rate": "0.13",
            }],
        ), db)
        db.flush()
        order = db.query(PurchaseOrder).filter(
            PurchaseOrder.id == invoice.related_order_id
        ).first()

        cancel_cmd = CancelOrder(order_type="purchase", account_id=account.id, operator="test", order_id=order.id)
        dispatch(cancel_cmd, db)
        db.flush()

        # 冲红凭证存在 (is_reversal=True)
        reversals = db.query(AccountMove).filter(
            AccountMove.source_model == "purchase_order",
            AccountMove.source_id == order.id,
            AccountMove.is_reversal == True,
        ).all()
        assert len(reversals) == 1, "取消采购单应生成 1 条冲红凭证"

        # 反向 StockMove 存在
        rev_moves = db.query(StockMove).filter(
            StockMove.source_type == "purchase_order_reversal",
            StockMove.source_id == order.id,
        ).all()
        assert len(rev_moves) == 1, "取消采购单应生成 1 条反向库存流水"
        assert rev_moves[0].quantity_l1 == -10, "反向流水数量应为负数"
