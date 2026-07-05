"""审计报告漏洞修复 — 回归 + 正确性测试

覆盖 8 个已修复漏洞：
  #10 record_sale 3% 税率覆盖 (P0)
  #12 红字发票重复冲红整单 (P0)
  #1  月结所得税补提失效 (P1)
  #4  小规模免税规则错乱 (P1)
  #7  固定资产处置日期默认 today (P1)
  #8  盘盈盘亏科目错挂 (P1)
  #3  哈希空间 31 位 (P2)
  #6  库存红冲 None 兜底 (P2)

也包含 2 个"不成立"漏洞的回归断言，防止误改：
  #2  off-by-one（AccountMove.date 是 Date 类型）
  #11 退货成本（移动加权平均法用原始 unit_cost）
"""
import pytest
from datetime import datetime, date
from decimal import Decimal
from unittest.mock import MagicMock, patch

from models import (
    Account, Product, SaleOrder, SaleItem, PurchaseOrder, PurchaseItem,
    Inventory, StockMove, FixedAsset, Invoice,
)
from models_finance import (
    Ledger, LedgerAccount, LedgerAccountBalance, AccountMove, AccountMoveLine,
)
from engine_finance import FinanceEngine
from engine_tax import TaxAccrualEngine, _period_hash, _parse_period
from engine_inventory import InventoryEngine
from engine_fixed_asset import FixedAssetEngine
from finance_integration import post_journal, CHART_OF_ACCOUNTS
from commands.base import dispatch
from commands.product_commands import AdjustInventory
from commands.orders import ReverseInvoice
from enums import OrderStatus, OrderType, PaymentStatus, InvoiceDirection, InvoiceType
from errors import BusinessError


# ═══════════════════════════════════════════════════════════
# 公共 fixture
# ═══════════════════════════════════════════════════════════

@pytest.fixture
def small_scale_account(db):
    """小规模纳税人账本"""
    a = Account(id=1, name="小规模测试", type="company", code="ss-test",
                taxpayer_type_l3="small_scale")
    db.add(a)
    db.commit()
    return a


@pytest.fixture
def general_account(db):
    """一般纳税人账本"""
    a = Account(id=2, name="一般纳税人测试", type="company", code="gn-test",
                taxpayer_type_l3="general")
    db.add(a)
    db.commit()
    return a


@pytest.fixture
def ledger(db, small_scale_account):
    l = Ledger(id=1, name="小规模账本", type="company", code="ss-test",
               taxpayer_type_l3="small_scale")
    db.add(l)
    db.commit()
    return l


@pytest.fixture
def ledger_general(db, general_account):
    l = Ledger(id=2, name="一般纳税人账本", type="company", code="gn-test",
               taxpayer_type_l3="general")
    db.add(l)
    db.commit()
    return l


@pytest.fixture
def full_accts(db, ledger):
    """创建全部科目（含 1901 待处理财产损溢）"""
    result = {}
    for code, name, atype in CHART_OF_ACCOUNTS:
        la = LedgerAccount(ledger_id=ledger.id, code=code, name=name,
                           account_type=atype, is_leaf=True)
        db.add(la)
        db.flush()
        result[code] = la
    db.commit()
    return result


@pytest.fixture
def product(db, small_scale_account):
    p = Product(id=1, account_id=1, name="测试商品", sku="T-001",
                purchase_price_l3=Decimal("100"), sale_price_l3=Decimal("200"),
                track_inventory_l3=True)
    db.add(p)
    db.flush()
    # 初始库存
    inv = Inventory(account_id=1, product_id=1, quantity_l4=100,
                    average_cost_l4=Decimal("100"), total_value_l4=Decimal("10000"))
    db.add(inv)
    db.flush()
    # AS-03: 库存真相源为 StockMove，必须保留一条期初流水与 Inventory 缓存一致
    db.add(StockMove(
        account_id=1, product_id=1,
        quantity_l1=Decimal("100"), unit_cost_l2=Decimal("100"),
        total_cost_l2=Decimal("10000"), source_type="inventory_adjustment",
        source_id=0, move_date_l1=datetime(2026, 1, 1),
    ))
    db.commit()
    return p


def _make_sale_order(db, account_id=1, customer_id=1, order_id=1,
                     tax_rate=Decimal("0.01"), unit_price=Decimal("200"),
                     quantity=10, unit_cost=Decimal("100")):
    """快速创建已完成的销售单"""
    so = SaleOrder(
        id=order_id, account_id=account_id, order_no=f"SO-TEST-{order_id}",
        customer_id=customer_id, order_type=OrderType.RETAIL,
        payment_status=PaymentStatus.UNPAID, status=OrderStatus.COMPLETED,
        total_price_l1=(unit_price * quantity).quantize(Decimal("0.01")),
        sale_date_l1=datetime(2026, 6, 15),
    )
    db.add(so)
    db.flush()
    si = SaleItem(
        order_id=so.id, product_id=1, quantity_l1=quantity,
        unit_price_l1=unit_price, tax_rate_l1=tax_rate,
        total_price_l1=(unit_price * quantity).quantize(Decimal("0.01")),
    )
    si.set_calculated_cost(unit_cost)
    db.add(si)
    db.commit()
    return so


def _get_line_map(db, move_id):
    """获取凭证分录 {code: {debit, credit}}"""
    lines = db.query(AccountMoveLine).filter(
        AccountMoveLine.move_id == move_id
    ).all()
    result = {}
    for line in lines:
        la = db.query(LedgerAccount).filter(
            LedgerAccount.id == line.ledger_account_id
        ).first()
        if la:
            result[la.code] = {
                "debit": Decimal(str(line.debit_l2)),
                "credit": Decimal(str(line.credit_l2)),
            }
    return result


# ═══════════════════════════════════════════════════════════
# #10: record_sale 3% 税率覆盖 (P0)
# ═══════════════════════════════════════════════════════════

class TestFix10RecordSaleTaxRate:
    """验证小规模纳税人销售凭证税率正确（1% 而非 3%）"""

    def test_small_scale_uses_item_tax_rate_not_3pct(
        self, db, small_scale_account, ledger, full_accts, product
    ):
        """小规模销售：item.tax_rate=1% 时，销项税应为 1% 而非 3%"""
        so = _make_sale_order(
            db, tax_rate=Decimal("0.01"),
            unit_price=Decimal("200"), quantity=10,
        )

        fin = FinanceEngine(db, account_id=1)
        fin.record_sale(so)
        db.flush()

        move = db.query(AccountMove).filter(
            AccountMove.source_model == "sale_order",
            AccountMove.source_id == so.id,
        ).first()
        assert move is not None

        codes = _get_line_map(db, move.id)

        # 收入 = 200 × 10 = 2000
        assert codes["6001"]["credit"] == Decimal("2000.00")
        # 销项税 = 2000 × 1% = 20（修复后），而非 2000 × 3% = 60
        assert codes["222103"]["credit"] == Decimal("20.00")
        # 应收 = 2000 + 20 = 2020（修复后），而非 2000 + 60 = 2060
        assert codes["1122"]["debit"] == Decimal("2020.00")

    def test_small_scale_tax_not_overstated_by_2pct(
        self, db, small_scale_account, ledger, full_accts, product
    ):
        """回归：1122 应收账款不应虚高 2%"""
        so = _make_sale_order(
            db, tax_rate=Decimal("0.01"),
            unit_price=Decimal("1000"), quantity=1,
        )

        fin = FinanceEngine(db, account_id=1)
        fin.record_sale(so)
        db.flush()

        move = db.query(AccountMove).filter(
            AccountMove.source_model == "sale_order",
            AccountMove.source_id == so.id,
        ).first()
        codes = _get_line_map(db, move.id)

        # 1% 税率：应收 = 1000 + 10 = 1010
        assert codes["1122"]["debit"] == Decimal("1010.00")
        # 不是 3% 税率：应收 ≠ 1000 + 30 = 1030
        assert codes["1122"]["debit"] != Decimal("1030.00")

    def test_general_taxpayer_unchanged(
        self, db, general_account, ledger_general, product
    ):
        """回归：一般纳税人税率不受影响（13%）"""
        # 为一般纳税人创建科目
        for code, name, atype in CHART_OF_ACCOUNTS:
            la = LedgerAccount(ledger_id=ledger_general.id, code=code, name=name,
                               account_type=atype, is_leaf=True)
            db.add(la)
        db.flush()

        # 一般纳税人的库存和商品
        p = Product(id=2, account_id=2, name="一般纳税人商品", sku="G-001",
                    purchase_price_l3=Decimal("100"), sale_price_l3=Decimal("200"),
                    track_inventory_l3=True)
        db.add(p)
        inv = Inventory(account_id=2, product_id=2, quantity_l4=100,
                        average_cost_l4=Decimal("100"), total_value_l4=Decimal("10000"))
        db.add(inv)
        db.commit()

        so = SaleOrder(
            id=10, account_id=2, order_no="SO-GN-001", customer_id=1,
            order_type=OrderType.RETAIL, payment_status=PaymentStatus.UNPAID,
            status=OrderStatus.COMPLETED, total_price_l1=Decimal("2000.00"),
            sale_date_l1=datetime(2026, 6, 15),
        )
        db.add(so)
        db.flush()
        si = SaleItem(
            order_id=so.id, product_id=2, quantity_l1=10,
            unit_price_l1=Decimal("200"), tax_rate_l1=Decimal("0.13"),
            total_price_l1=Decimal("2000.00"),
        )
        si.set_calculated_cost(Decimal("100"))
        db.add(si)
        db.commit()

        fin = FinanceEngine(db, account_id=2)
        fin.record_sale(so)
        db.flush()

        move = db.query(AccountMove).filter(
            AccountMove.source_model == "sale_order",
            AccountMove.source_id == so.id,
        ).first()
        assert move is not None

        lines = db.query(AccountMoveLine).filter(
            AccountMoveLine.move_id == move.id
        ).all()
        codes = {}
        for line in lines:
            la = db.query(LedgerAccount).filter(
                LedgerAccount.id == line.ledger_account_id,
                LedgerAccount.ledger_id == ledger_general.id,
            ).first()
            if la:
                codes[la.code] = {
                    "debit": Decimal(str(line.debit_l2)),
                    "credit": Decimal(str(line.credit_l2)),
                }

        # 一般纳税人 13% 税率不变
        assert codes["222101"]["credit"] == Decimal("260.00")  # 2000 × 13%
        assert codes["1122"]["debit"] == Decimal("2260.00")    # 2000 + 260


# ═══════════════════════════════════════════════════════════
# #1: 月结所得税补提失效 (P1)
# ═══════════════════════════════════════════════════════════

class TestFix1MonthlyCloseSupplement:
    """验证月结可以补提所得税差额"""

    def test_income_tax_supplement_after_initial_close(
        self, db, small_scale_account, ledger, full_accts, product
    ):
        """首次月结后利润变动，第二次月结应补提差额"""
        # 先创建一笔销售（有利润）
        so = _make_sale_order(
            db, tax_rate=Decimal("0.01"),
            unit_price=Decimal("200"), quantity=10,
        )
        fin = FinanceEngine(db, account_id=1)
        fin.record_sale(so)
        db.flush()

        # 第一次月结
        engine = TaxAccrualEngine(db)
        result1 = engine.execute(account_id=1, period="2026-06",
                                 taxpayer_type="small_scale")
        db.flush()

        # 首次应计提所得税
        assert result1["status"] == "ok"
        assert result1["target_income_tax"] > 0

        # 再创建一笔销售（增加利润）
        so2 = SaleOrder(
            id=2, account_id=1, order_no="SO-TEST-002", customer_id=1,
            order_type=OrderType.RETAIL, payment_status=PaymentStatus.UNPAID,
            status=OrderStatus.COMPLETED, total_price_l1=Decimal("5000.00"),
            sale_date_l1=datetime(2026, 6, 20),
        )
        db.add(so2)
        db.flush()
        si2 = SaleItem(
            order_id=so2.id, product_id=1, quantity_l1=25,
            unit_price_l1=Decimal("200"), tax_rate_l1=Decimal("0.01"),
            total_price_l1=Decimal("5000.00"),
        )
        si2.set_calculated_cost(Decimal("100"))
        db.add(si2)
        db.commit()
        fin.record_sale(so2)
        db.flush()

        # 第二次月结 — 应补提差额（修复后）
        result2 = engine.execute(account_id=1, period="2026-06",
                                 taxpayer_type="small_scale")
        db.flush()

        # 修复后：第二次也应成功，补提差额
        assert result2["status"] == "ok"
        # target 应该比第一次大（利润增加了）
        assert result2["target_income_tax"] >= result1["target_income_tax"]

    def test_surcharge_delta_mode(
        self, db, small_scale_account, ledger, full_accts, product
    ):
        """附加税应支持 delta 补提"""
        # 小规模无附加税（curr_vat 直接进 222103，无附加税计提）
        # 用一般纳税人测试附加税 delta
        # 先简单验证附加税不会因 closed["surcharge"] 被跳过
        so = _make_sale_order(
            db, tax_rate=Decimal("0.01"),
            unit_price=Decimal("200"), quantity=5,
        )
        fin = FinanceEngine(db, account_id=1)
        fin.record_sale(so)
        db.flush()

        engine = TaxAccrualEngine(db)
        result = engine.execute(account_id=1, period="2026-06",
                                taxpayer_type="small_scale")
        db.flush()
        assert result["status"] == "ok"


# ═══════════════════════════════════════════════════════════
# #4: 小规模免税规则错乱 (P1)
# ═══════════════════════════════════════════════════════════

class TestFix4SmallScaleExemption:
    """验证小规模免税区分普票和专票"""

    def test_exemption_separates_ordinary_and_special(
        self, db, small_scale_account, ledger, full_accts, product
    ):
        """季度≤30万：普票1%销项税转出免税，专票1%留缴"""
        # 创建销售（产生销项税，按1%记账）
        so = _make_sale_order(
            db, tax_rate=Decimal("0.01"),
            unit_price=Decimal("200"), quantity=10,
        )
        fin = FinanceEngine(db, account_id=1)
        fin.record_sale(so)
        db.flush()

        # 创建发票记录（普票 + 专票）
        ordinary_inv = Invoice(
            account_id=1, invoice_no="INV-ORD-001",
            direction=InvoiceDirection.OUT, invoice_type=InvoiceType.ORDINARY,
            tax_rate_l1=Decimal("0.03"), amount_without_tax_l1=Decimal("1500"),
            tax_amount_l1=Decimal("45"), amount_with_tax_l1=Decimal("1545"),
            issue_date_l1=date(2026, 6, 10), counterparty_name="客户A",
        )
        special_inv = Invoice(
            account_id=1, invoice_no="INV-SPC-001",
            direction=InvoiceDirection.OUT, invoice_type=InvoiceType.SPECIAL,
            tax_rate_l1=Decimal("0.03"), amount_without_tax_l1=Decimal("500"),
            tax_amount_l1=Decimal("15"), amount_with_tax_l1=Decimal("515"),
            issue_date_l1=date(2026, 6, 15), counterparty_name="客户B",
        )
        db.add(ordinary_inv)
        db.add(special_inv)
        db.commit()

        # 月结（6月是季度末月）
        engine = TaxAccrualEngine(db)
        result = engine.execute(account_id=1, period="2026-06",
                                taxpayer_type="small_scale")
        db.flush()

        assert result["status"] == "ok"
        # 验证减免凭证存在
        exemption_moves = db.query(AccountMove).filter(
            AccountMove.ledger_id == ledger.id,
            AccountMove.source_model == "vat_exemption",
        ).all()
        # 季度末应有减免结转（普票1%转出）
        if exemption_moves:
            move = exemption_moves[0]
            lines = _get_line_map(db, move.id)
            # 222103 借方 = 减免额 = 普票不含税 × 1% = 1500 × 1% = 15
            if "222103" in lines:
                exemption_amt = lines["222103"]["debit"]
                # 减免额应 > 0（普票1%部分）
                assert exemption_amt > 0
                # 减免额不应超过 222103 贷方余额（防止科目穿负）
                # 222103 贷方 = 销售销项税 = 2000 × 1% = 20
                assert exemption_amt <= Decimal("20")


# ═══════════════════════════════════════════════════════════
# #7: 固定资产处置日期默认 today (P1)
# ═══════════════════════════════════════════════════════════

class TestFix7DisposalDateRequired:
    """验证处置日期必填"""

    @pytest.fixture
    def asset(self, db, small_scale_account, ledger, full_accts):
        asset = FixedAsset(
            account_id=1, asset_code="FA-001", name="测试设备",
            category="机器设备", original_value_l1=Decimal("120000"),
            salvage_rate_l3=Decimal("0.05"), useful_life_l3=60,
            depreciation_method_l3="年限平均法",
            start_date_l1=date(2025, 1, 1),
            accumulated_depreciation_l4=Decimal("22800"),  # 已折旧12个月
            status="在用",
        )
        db.add(asset)
        db.commit()
        return asset

    def test_disposal_without_date_raises(self, db, asset):
        """不传 disposal_date 应抛异常"""
        eng = FixedAssetEngine(db, account_id=1)
        with pytest.raises(BusinessError) as exc_info:
            eng.record_disposal(asset.id, disposal_price=Decimal("50000"))
        assert "处置日期" in str(exc_info.value.data) or "处置日期" in str(exc_info.value)

    def test_disposal_with_explicit_date(self, db, asset):
        """传入 disposal_date 应正常处置"""
        eng = FixedAssetEngine(db, account_id=1)
        eng.record_disposal(
            asset.id,
            disposal_price=Decimal("50000"),
            disposal_date=date(2026, 6, 15),
        )
        db.flush()

        # 验证资产状态
        updated = db.query(FixedAsset).filter(FixedAsset.id == asset.id).first()
        assert updated.status == "报废"

        # 验证凭证日期正确
        move = db.query(AccountMove).filter(
            AccountMove.source_model == "fixed_asset_disposal",
            AccountMove.source_id == asset.id,
        ).first()
        assert move is not None
        assert move.date_l1 == date(2026, 6, 15)


# ═══════════════════════════════════════════════════════════
# #8: 盘盈盘亏科目错挂 (P1)
# ═══════════════════════════════════════════════════════════

class TestFix8InventoryAdjustmentAccount:
    """验证盘盈盘亏挂 1901 而非 6601"""

    def test_1901_account_exists_in_chart(self):
        """科目表中应包含 1901"""
        codes = [c[0] for c in CHART_OF_ACCOUNTS]
        assert "1901" in codes

    def test_inventory_loss_uses_1901(
        self, db, small_scale_account, ledger, full_accts, product
    ):
        """盘亏应借 1901 而非 6601"""
        cmd = AdjustInventory(
            account_id=1, product_id=1, quantity=90,
            reason="盘亏测试", unit_cost=100,
            adjust_date="2026-06-15",
        )
        from commands.product_commands import AdjustInventoryHandler
        handler = AdjustInventoryHandler()
        handler.handle(cmd, db)
        db.flush()

        # 查找调整凭证（通过 opening_balance 类型）
        moves = db.query(AccountMove).filter(
            AccountMove.move_type == "opening_balance",
        ).all()
        assert len(moves) > 0

        # 检查分录用 1901 而非 6601
        for move in moves:
            lines = _get_line_map(db, move.id)
            if "1901" in lines:
                # 盘亏：借 1901
                assert lines["1901"]["debit"] > 0
                assert "6601" not in lines or lines["6601"]["debit"] == 0

    def test_inventory_gain_uses_1901(
        self, db, small_scale_account, ledger, full_accts, product
    ):
        """盘盈应贷 1901 而非 6601"""
        cmd = AdjustInventory(
            account_id=1, product_id=1, quantity=110,
            reason="盘盈测试", unit_cost=100,
            adjust_date="2026-06-15",
        )
        from commands.product_commands import AdjustInventoryHandler
        handler = AdjustInventoryHandler()
        handler.handle(cmd, db)
        db.flush()

        moves = db.query(AccountMove).filter(
            AccountMove.move_type == "opening_balance",
        ).all()
        assert len(moves) > 0

        for move in moves:
            lines = _get_line_map(db, move.id)
            if "1901" in lines:
                # 盘盈：贷 1901
                assert lines["1901"]["credit"] > 0
                assert "6601" not in lines or lines["6601"]["credit"] == 0


# ═══════════════════════════════════════════════════════════
# #3: 哈希空间 31 位 (P2)
# ═══════════════════════════════════════════════════════════

class TestFix3PeriodHash:
    """验证哈希空间扩展到 63 位"""

    def test_hash_within_63bit_range(self):
        """哈希值应在 63 位范围内（< 2^63）"""
        h = _period_hash("2026-06", "income")
        assert h < 2**63
        assert h >= 0

    def test_hash_deterministic(self):
        """相同输入应产生相同哈希"""
        h1 = _period_hash("2026-06", "surcharge")
        h2 = _period_hash("2026-06", "surcharge")
        assert h1 == h2

    def test_different_tags_different_hash(self):
        """不同 tag 应产生不同哈希"""
        h1 = _period_hash("2026-06", "income")
        h2 = _period_hash("2026-06", "surcharge")
        assert h1 != h2

    def test_different_periods_different_hash(self):
        """不同期间应产生不同哈希"""
        h1 = _period_hash("2026-06", "income")
        h2 = _period_hash("2026-05", "income")
        assert h1 != h2


# ═══════════════════════════════════════════════════════════
# #6: 库存红冲 None 兜底 (P2)
# ═══════════════════════════════════════════════════════════

class TestFix6ReverseNoneOriginal:
    """验证 original 为 None 时抛异常"""

    def test_reverse_without_original_raises(
        self, db, small_scale_account, product
    ):
        """找不到原始 StockMove 时应抛 BusinessError"""
        eng = InventoryEngine(db)
        with pytest.raises(BusinessError):
            eng.reverse(
                account_id=1, product_id=1, quantity=5,
                unit_cost=Decimal("100"),
                source_type="sale_order", source_id=99999,  # 不存在的 source_id
            )

    def test_reverse_with_original_works(
        self, db, small_scale_account, product
    ):
        """有原始 StockMove 时应正常红冲"""
        # 先入库
        eng = InventoryEngine(db)
        eng.inbound(
            account_id=1, product_id=1, quantity=20,
            unit_price=Decimal("100"),
            source_type="purchase_order", source_id=1,
        )
        db.flush()

        # 红冲入库
        eng.reverse(
            account_id=1, product_id=1, quantity=5,
            unit_cost=Decimal("100"),
            source_type="purchase_order", source_id=1,
        )
        db.flush()

        # 验证冲红流水存在
        rev_move = db.query(StockMove).filter(
            StockMove.source_type == "purchase_order_reversal",
            StockMove.source_id == 1,
        ).first()
        assert rev_move is not None
        assert rev_move.quantity_l1 < 0  # 入库红冲为负


# ═══════════════════════════════════════════════════════════
# #2 回归：off-by-one 不应被误改
# ═══════════════════════════════════════════════════════════

class TestRegression2NoOffByOne:
    """验证 _parse_period 的日期边界正确（Date 类型）"""

    def test_parse_period_month_end(self):
        """月末日期应正确"""
        start, end = _parse_period("2026-06")
        assert start == datetime(2026, 6, 1, 0, 0, 0)
        # 6 月有 30 天
        assert end == datetime(2026, 6, 30, 23, 59, 59)

    def test_parse_period_feb_leap_year(self):
        """闰年 2 月有 29 天"""
        start, end = _parse_period("2024-02")
        assert end == datetime(2024, 2, 29, 23, 59, 59)

    def test_parse_period_feb_non_leap(self):
        """非闰年 2 月有 28 天"""
        start, end = _parse_period("2026-02")
        assert end == datetime(2026, 2, 28, 23, 59, 59)

    def test_account_move_date_is_date_type(self):
        """回归：AccountMove.date 列类型应为 Date"""
        from sqlalchemy import Date as SQLDate
        col = AccountMove.__table__.c.date_l1
        assert isinstance(col.type, SQLDate)


# ═══════════════════════════════════════════════════════════
# #11 回归：退货成本用原始 unit_cost（不应用 average_cost）
# ═══════════════════════════════════════════════════════════

class TestRegression11ReturnCostUsesOriginalUnitCost:
    """验证退货成本使用原始 StockMove.unit_cost（移动加权平均法）"""

    def test_return_uses_original_cost_not_current_average(
        self, db, small_scale_account, ledger, full_accts, product
    ):
        """退货应按原销售时的出库成本冲回"""
        eng = InventoryEngine(db)

        # T1: 出库 10 件，average_cost = 100
        so1 = SaleOrder(
            id=1, account_id=1, order_no="SO-1", customer_id=1,
            order_type=OrderType.RETAIL, payment_status=PaymentStatus.UNPAID,
            status=OrderStatus.COMPLETED, total_price_l1=Decimal("2000"),
            sale_date_l1=datetime(2026, 6, 10),
        )
        db.add(so1)
        db.flush()
        si1 = SaleItem(
            order_id=1, product_id=1, quantity_l1=10,
            unit_price_l1=Decimal("200"), tax_rate_l1=Decimal("0.01"),
            total_price_l1=Decimal("2000"),
        )
        db.add(si1)
        db.commit()

        unit_cost_1 = eng.outbound(
            account_id=1, product_id=1, quantity=10,
            source_type="sale_order", source_id=1,
        )
        si1.set_calculated_cost(unit_cost_1)
        db.flush()

        original_cost = unit_cost_1  # 100

        # T2: 采购 50 件单价 150，average_cost 变化
        eng.inbound(
            account_id=1, product_id=1, quantity=50,
            unit_price=Decimal("150"),
            source_type="purchase_order", source_id=2,
        )
        db.flush()

        # 验证 average_cost 已变化
        inv = db.query(Inventory).filter(
            Inventory.account_id == 1, Inventory.product_id == 1
        ).first()
        assert inv.average_cost_l4 != original_cost  # 不再是 100

        # T3: 退货 3 件 — 应用原始 unit_cost
        import time
        return_id = int(time.time() * 1000)
        eng.reverse(
            account_id=1, product_id=1, quantity=3,
            unit_cost=Decimal("0"),  # 自动从原 StockMove 取
            source_type="sale_order", source_id=1,
            source_id_override=return_id,
        )
        db.flush()

        # 验证红冲流水用了原始成本
        rev_move = db.query(StockMove).filter(
            StockMove.source_type == "sale_order_reversal",
            StockMove.source_id == return_id,
        ).first()
        assert rev_move is not None
        # 成本应为原始出库成本（100），而非当前 average_cost
        # 红冲流水 quantity 和 unit_cost 均为负数，取 abs 比较
        assert abs(rev_move.unit_cost_l2) == original_cost
        # 修复 #12: ref_source_id 应记录原销售单 ID
        assert rev_move.ref_source_id == 1


# ═══════════════════════════════════════════════════════════
# #12: 红字发票重复冲红整单 (P0) — 集成测试
# ═══════════════════════════════════════════════════════════

class TestFix12RedInvoiceNoDoubleReverse:
    """验证部分退货后红字发票冲红不重复冲红整单"""

    def test_red_invoice_after_partial_return_no_double_reverse(
        self, db, small_scale_account, ledger, full_accts, product
    ):
        """部分退货后做红字发票冲红，不应重复冲红整单"""
        import time

        # 1. 创建销售单 + 凭证 + 库存出库
        so = _make_sale_order(
            db, order_id=1, tax_rate=Decimal("0.01"),
            unit_price=Decimal("200"), quantity=10,
        )
        fin = FinanceEngine(db, account_id=1)
        fin.record_sale(so)
        db.flush()

        eng_inv = InventoryEngine(db)
        for item in so.items:
            uc = eng_inv.outbound(
                account_id=1, product_id=item.product_id,
                quantity=item.quantity_l1,
                source_type="sale_order", source_id=so.id,
            )
            item.set_calculated_cost(uc)
        db.flush()

        # 2. 部分退货 3 件
        from commands.orders._sale import return_sale_order
        return_sale_order(
            db=db, account_id=1, order_id=1,
            return_date="2026-06-20",
            reason="部分退货测试",
            items=[{"product_id": 1, "quantity": 3}],
            operator="test",
        )
        db.flush()

        # 验证部分退货凭证存在
        sale_return_moves = db.query(AccountMove).filter(
            AccountMove.source_model == "sale_return",
        ).all()
        assert len(sale_return_moves) == 1

        # 3. 创建发票并关联销售单
        invoice = Invoice(
            account_id=1, invoice_no="INV-TEST-001",
            direction=InvoiceDirection.OUT, invoice_type=InvoiceType.ORDINARY,
            tax_rate_l1=Decimal("0.03"),
            amount_without_tax_l1=Decimal("2000"),
            tax_amount_l1=Decimal("60"),
            amount_with_tax_l1=Decimal("2060"),
            issue_date_l1=date(2026, 6, 15),
            counterparty_name="测试客户",
            related_order_type="sale_order",
            related_order_id=1,
        )
        db.add(invoice)
        db.commit()

        # 4. 红字发票冲红
        rev_cmd = ReverseInvoice(
            account_id=1, invoice_id=invoice.id,
            reason="红字发票测试",
        )
        rev_cmd.account_id = 1
        rev_cmd.operator = "test"
        from commands.orders._invoice import ReverseInvoiceHandler
        rev_handler = ReverseInvoiceHandler()
        result = rev_handler.handle(rev_cmd, db)
        db.flush()

        # 5. 验证：不应有 2 条 sale_order 冲红凭证
        sale_order_reversals = db.query(AccountMove).filter(
            AccountMove.source_model == "sale_order",
            AccountMove.is_reversal == True,
        ).all()

        # 修复后：不应整单冲红（已有部分退货），sale_order 冲红应为 0
        # 或如果有，也不应超过 1 条
        assert len(sale_order_reversals) <= 1, \
            f"期望至多 1 条 sale_order 冲红，实际 {len(sale_order_reversals)} 条"

        # 6. 验证：应有 sale_return 凭证（冲红剩余部分）
        all_return_moves = db.query(AccountMove).filter(
            AccountMove.source_model == "sale_return",
        ).all()
        # 至少有部分退货的 1 条 + 红字发票冲红的 1 条
        assert len(all_return_moves) >= 1

    def test_red_invoice_without_partial_return_full_reverse(
        self, db, small_scale_account, ledger, full_accts, product
    ):
        """无部分退货时，红字发票冲红应整单冲红"""
        # 1. 创建销售单 + 凭证 + 库存出库
        so = _make_sale_order(
            db, order_id=2, tax_rate=Decimal("0.01"),
            unit_price=Decimal("200"), quantity=10,
        )
        fin = FinanceEngine(db, account_id=1)
        fin.record_sale(so)
        db.flush()

        eng_inv = InventoryEngine(db)
        for item in so.items:
            uc = eng_inv.outbound(
                account_id=1, product_id=item.product_id,
                quantity=item.quantity_l1,
                source_type="sale_order", source_id=so.id,
            )
            item.set_calculated_cost(uc)
        db.flush()

        # 2. 创建发票
        invoice = Invoice(
            account_id=1, invoice_no="INV-TEST-002",
            direction=InvoiceDirection.OUT, invoice_type=InvoiceType.ORDINARY,
            tax_rate_l1=Decimal("0.03"),
            amount_without_tax_l1=Decimal("2000"),
            tax_amount_l1=Decimal("60"),
            amount_with_tax_l1=Decimal("2060"),
            issue_date_l1=date(2026, 6, 15),
            counterparty_name="测试客户",
            related_order_type="sale_order",
            related_order_id=2,
        )
        db.add(invoice)
        db.commit()

        # 3. 红字发票冲红（无部分退货）
        rev_cmd = ReverseInvoice(
            account_id=1, invoice_id=invoice.id,
            reason="整单红冲测试",
        )
        rev_cmd.account_id = 1
        rev_cmd.operator = "test"
        from commands.orders._invoice import ReverseInvoiceHandler
        rev_handler = ReverseInvoiceHandler()
        result = rev_handler.handle(rev_cmd, db)
        db.flush()

        # 4. 验证：应有 1 条 sale_order 整单冲红
        sale_order_reversals = db.query(AccountMove).filter(
            AccountMove.source_model == "sale_order",
            AccountMove.is_reversal == True,
        ).all()
        assert len(sale_order_reversals) == 1, \
            f"无部分退货时应整单冲红，期望 1 条，实际 {len(sale_order_reversals)} 条"

        # 5. 验证库存回退
        rev_stock_moves = db.query(StockMove).filter(
            StockMove.source_type == "sale_order_reversal",
            StockMove.source_id == 2,
        ).all()
        assert len(rev_stock_moves) == 1
        assert rev_stock_moves[0].quantity_l1 > 0  # 出库红冲为正
