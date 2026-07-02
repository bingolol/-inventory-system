"""未开票收入销项税申报测试 — 业务因果链 A1

验证:散客现金销售(has_invoice_l1=False)的销项税被正确纳入增值税申报,
避免"不开发票=不交税"的合规风险。

业务因果链 A1 关键因果:
  不开发票 ≠ 不确认收入 ≠ 不交税。
  收入的因是"交易完成收到钱",发票只是税务凭据之一。

运行:python -m pytest tests/unit/test_unrecorded_revenue.py -v
"""
import sys
import pytest
from pathlib import Path
from decimal import Decimal
from datetime import datetime

BACKEND_DIR = Path(__file__).resolve().parents[2] / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))


def _ensure_account(db):
    """创建测试账本,返回 account_id"""
    from models import Account
    acc = Account(name="测试账本", type="company", code="TEST-UNREC", taxpayer_type_l3="small_scale")
    db.add(acc)
    db.flush()
    return acc.id


# ═══════════════════════════════════════════════════════════════
# 模型层:has_invoice_l1 字段
# ═══════════════════════════════════════════════════════════════

class TestHasInvoice字段:
    """SaleOrder.has_invoice_l1 字段存在性和默认值"""

    def test_字段存在(self):
        from models import SaleOrder
        assert hasattr(SaleOrder, "has_invoice_l1")

    def test_默认值为True(self, db):
        """向后兼容:已开发票为默认行为"""
        from models import SaleOrder
        aid = _ensure_account(db)
        order = SaleOrder(
            account_id=aid,
            order_no="TEST-HI-DEFAULT",
            order_type="retail",
            total_price_l1=Decimal("100"),
            sale_date_l1=datetime(2026, 6, 1),
        )
        db.add(order)
        db.flush()
        assert order.has_invoice_l1 is True

    def test_可设置为False(self, db):
        from models import SaleOrder
        aid = _ensure_account(db)
        order = SaleOrder(
            account_id=aid,
            order_no="TEST-HI-FALSE",
            order_type="retail",
            total_price_l1=Decimal("100"),
            sale_date_l1=datetime(2026, 6, 1),
            has_invoice_l1=False,
        )
        db.add(order)
        db.flush()
        assert order.has_invoice_l1 is False

    def test_字段层级标注(self):
        """has_invoice_l1 应标注为 L1 外部输入"""
        from models import SaleOrder
        col = SaleOrder.__table__.c.has_invoice_l1
        assert col.info.get("tier") == "L1"
        assert col.info.get("source") == "external"


# ═══════════════════════════════════════════════════════════════
# 增值税申报:未开票收入合并
# ═══════════════════════════════════════════════════════════════

class Test未开票收入申报:
    """验证散客不开发票的销售单销项税被纳入增值税申报"""

    def test_无未开票收入时返回零(self, db):
        """无未开票销售单时,unrecorded_revenue/tax 应为 0"""
        from crud.finance.tax_declarations import aggregate_vat_invoices
        aid = _ensure_account(db)

        agg = aggregate_vat_invoices(
            db, account_id=aid,
            start_date=datetime(2026, 1, 1),
            end_date_exclusive=datetime(2026, 4, 1),
        )
        assert agg["unrecorded_revenue"] == Decimal("0")
        assert agg["unrecorded_tax"] == Decimal("0")
        assert len(agg["unrecorded_orders"]) == 0

    def test_未开票销售单被汇总(self, db):
        """has_invoice_l1=False 的销售单应被纳入未开票收入"""
        from crud.finance.tax_declarations import aggregate_vat_invoices
        from models import SaleOrder, SaleItem, Product
        aid = _ensure_account(db)

        # 创建测试商品
        product = Product(
            account_id=aid, name="测试商品-未开票", sku="TEST-UNREC-001",
            unit="个", track_inventory_l3=False,
        )
        db.add(product)
        db.flush()

        # 创建未开票销售单(散客现金销售,1% 税率)
        order = SaleOrder(
            account_id=aid, order_no="TEST-UNREC-001",
            order_type="retail", total_price_l1=Decimal("101.00"),
            tax_amount_l1=Decimal("1.00"),
            has_invoice_l1=False,  # 散客不开发票
            sale_date_l1=datetime(2026, 5, 15),
            status="completed",
        )
        db.add(order)
        db.flush()

        item = SaleItem(
            order_id=order.id, product_id=product.id,
            quantity_l1=1, unit_price_l1=Decimal("101.00"),
            tax_rate_l1=Decimal("0.01"), total_price_l1=Decimal("101.00"),
        )
        db.add(item)
        db.flush()

        agg = aggregate_vat_invoices(
            db, account_id=aid,
            start_date=datetime(2026, 4, 1),
            end_date_exclusive=datetime(2026, 7, 1),
        )

        assert len(agg["unrecorded_orders"]) == 1
        assert agg["unrecorded_revenue"] == Decimal("100.00")  # 101 / 1.01
        assert agg["unrecorded_tax"] == Decimal("1.00")

    def test_已开票销售单不被纳入未开票汇总(self, db):
        """has_invoice_l1=True 的销售单不应被纳入未开票收入"""
        from crud.finance.tax_declarations import aggregate_vat_invoices
        from models import SaleOrder, SaleItem, Product
        aid = _ensure_account(db)

        product = Product(
            account_id=aid, name="测试商品-已开票", sku="TEST-REC-001",
            unit="个", track_inventory_l3=False,
        )
        db.add(product)
        db.flush()

        order = SaleOrder(
            account_id=aid, order_no="TEST-REC-001",
            order_type="retail", total_price_l1=Decimal("113.00"),
            tax_amount_l1=Decimal("13.00"),
            has_invoice_l1=True,  # 已开票
            sale_date_l1=datetime(2026, 5, 15),
            status="completed",
        )
        db.add(order)
        db.flush()

        item = SaleItem(
            order_id=order.id, product_id=product.id,
            quantity_l1=1, unit_price_l1=Decimal("113.00"),
            tax_rate_l1=Decimal("0.13"), total_price_l1=Decimal("113.00"),
        )
        db.add(item)
        db.flush()

        agg = aggregate_vat_invoices(
            db, account_id=aid,
            start_date=datetime(2026, 4, 1),
            end_date_exclusive=datetime(2026, 7, 1),
        )

        assert len(agg["unrecorded_orders"]) == 0
        assert agg["unrecorded_revenue"] == Decimal("0")

    def test_已取消销售单不被纳入未开票汇总(self, db):
        """status=cancelled 的销售单不应被纳入未开票收入"""
        from crud.finance.tax_declarations import aggregate_vat_invoices
        from models import SaleOrder, SaleItem, Product
        aid = _ensure_account(db)

        product = Product(
            account_id=aid, name="测试商品-取消", sku="TEST-CANCEL-001",
            unit="个", track_inventory_l3=False,
        )
        db.add(product)
        db.flush()

        order = SaleOrder(
            account_id=aid, order_no="TEST-CANCEL-001",
            order_type="retail", total_price_l1=Decimal("101.00"),
            has_invoice_l1=False,
            sale_date_l1=datetime(2026, 5, 15),
            status="cancelled",  # 已取消
        )
        db.add(order)
        db.flush()

        item = SaleItem(
            order_id=order.id, product_id=product.id,
            quantity_l1=1, unit_price_l1=Decimal("101.00"),
            tax_rate_l1=Decimal("0.01"), total_price_l1=Decimal("101.00"),
        )
        db.add(item)
        db.flush()

        agg = aggregate_vat_invoices(
            db, account_id=aid,
            start_date=datetime(2026, 4, 1),
            end_date_exclusive=datetime(2026, 7, 1),
        )

        assert len(agg["unrecorded_orders"]) == 0

    def test_未开票收入合并到output_total和output_tax(self, db):
        """未开票收入应合并到 output_total(销项总额)和 output_tax(销项税)"""
        from crud.finance.tax_declarations import aggregate_vat_invoices
        from models import SaleOrder, SaleItem, Product
        aid = _ensure_account(db)

        product = Product(
            account_id=aid, name="测试商品-合并", sku="TEST-MERGE-001",
            unit="个", track_inventory_l3=False,
        )
        db.add(product)
        db.flush()

        order = SaleOrder(
            account_id=aid, order_no="TEST-MERGE-001",
            order_type="retail", total_price_l1=Decimal("101.00"),
            has_invoice_l1=False,
            sale_date_l1=datetime(2026, 5, 15),
            status="completed",
        )
        db.add(order)
        db.flush()

        item = SaleItem(
            order_id=order.id, product_id=product.id,
            quantity_l1=1, unit_price_l1=Decimal("101.00"),
            tax_rate_l1=Decimal("0.01"), total_price_l1=Decimal("101.00"),
        )
        db.add(item)
        db.flush()

        agg = aggregate_vat_invoices(
            db, account_id=aid,
            start_date=datetime(2026, 4, 1),
            end_date_exclusive=datetime(2026, 7, 1),
        )

        # 未开票收入应合并到 output_total 和 output_tax
        assert agg["output_total"] == Decimal("100.00")
        assert agg["output_tax"] == Decimal("1.00")
        # 未开票收入按普通收入处理(纳入小规模免税判定)
        assert agg["ordinary_revenue"] == Decimal("100.00")

    def test_未开票收入纳入申报表(self, db):
        """generate_vat_declaration 返回结果应包含未开票收入明细"""
        from crud.finance.tax_declarations import generate_vat_declaration
        from models import SaleOrder, SaleItem, Product
        aid = _ensure_account(db)

        product = Product(
            account_id=aid, name="测试商品-申报", sku="TEST-DECL-001",
            unit="个", track_inventory_l3=False,
        )
        db.add(product)
        db.flush()

        order = SaleOrder(
            account_id=aid, order_no="TEST-DECL-001",
            order_type="retail", total_price_l1=Decimal("101.00"),
            has_invoice_l1=False,
            sale_date_l1=datetime(2026, 5, 15),
            status="completed",
        )
        db.add(order)
        db.flush()

        item = SaleItem(
            order_id=order.id, product_id=product.id,
            quantity_l1=1, unit_price_l1=Decimal("101.00"),
            tax_rate_l1=Decimal("0.01"), total_price_l1=Decimal("101.00"),
        )
        db.add(item)
        db.flush()

        result = generate_vat_declaration(db, account_id=aid, year=2026, quarter=2)

        assert result["unrecorded_revenue"] == Decimal("100.00")
        assert result["unrecorded_tax"] == Decimal("1.00")
        assert result["unrecorded_order_count"] == 1


# ═══════════════════════════════════════════════════════════════
# 零税率处理
# ═══════════════════════════════════════════════════════════════

class Test零税率处理:
    """tax_rate=0 的未开票销售单(如免税商品)应正确处理"""

    def test_零税率未开票收入(self, db):
        from crud.finance.tax_declarations import aggregate_vat_invoices
        from models import SaleOrder, SaleItem, Product
        aid = _ensure_account(db)

        product = Product(
            account_id=aid, name="测试商品-零税", sku="TEST-ZERO-001",
            unit="个", track_inventory_l3=False,
        )
        db.add(product)
        db.flush()

        order = SaleOrder(
            account_id=aid, order_no="TEST-ZERO-001",
            order_type="retail", total_price_l1=Decimal("100.00"),
            has_invoice_l1=False,
            sale_date_l1=datetime(2026, 5, 15),
            status="completed",
        )
        db.add(order)
        db.flush()

        item = SaleItem(
            order_id=order.id, product_id=product.id,
            quantity_l1=1, unit_price_l1=Decimal("100.00"),
            tax_rate_l1=Decimal("0"), total_price_l1=Decimal("100.00"),
        )
        db.add(item)
        db.flush()

        agg = aggregate_vat_invoices(
            db, account_id=aid,
            start_date=datetime(2026, 4, 1),
            end_date_exclusive=datetime(2026, 7, 1),
        )

        assert agg["unrecorded_revenue"] == Decimal("100.00")
        assert agg["unrecorded_tax"] == Decimal("0")
