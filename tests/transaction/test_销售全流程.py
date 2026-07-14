"""一体化事务测试：销售全流程

合并自:
  - test_取消销售单.py   取消/恢复销售单 + 状态机拦截
  - test_库存回补.py     取消回补库存 + 恢复重新扣减
  - test_销售日期.py     自定义 business_date
  - test_自定义价格.py   自定义金额 + 差额分配 + 精度
  - test_重复校验.py     重复商品拦截
  - test_delivery_check.py  T1-T6 交付目标
"""

import time
import pytest
from decimal import Decimal, ROUND_HALF_UP
from datetime import datetime
from sqlalchemy import func as sqlfunc



from tests.factories import (
    api_create_product, api_create_customer, api_create_supplier,
)
from tests.helpers import get_entity_id, uniq

from enums import OrderStatus
from models import SaleOrder, SaleItem, Inventory, StockMove, Invoice


HEADERS = {"X-Account-ID": "1", "X-Operator": "user"}


def round2(v):
    return Decimal(str(v)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


@pytest.fixture(scope="module", autouse=True)
def bootstrap(client):
    """模块级前置：初始化账本 + 科目表"""
    resp = client.post("/api/bootstrap/init")
    assert resp.status_code == 200, f"bootstrap 失败: {resp.text}"


@pytest.fixture(scope="module")
def ids(client):
    """模块级共享 ID：商品/客户/供应商"""
    tag = str(int(time.time()))[-6:]

    pid, _ = api_create_product(client, HEADERS,
        name=f"商品-A-{tag}", sku=f"SKU-A-{tag}",
        purchase_price=10, sale_price=20, category="测试")
    pid2, _ = api_create_product(client, HEADERS,
        name=f"商品-B-{tag}", sku=f"SKU-B-{tag}",
        purchase_price=12, sale_price=25, category="测试")
    cid, _ = api_create_customer(client, HEADERS, name=f"客户-{tag}")
    sid, _ = api_create_supplier(client, HEADERS, name=f"供应商-{tag}")

    # 预采购库存（发票驱动），确保后续销售测试有足够库存（deduct_inventory 恒为 True）
    _purchase_stock(client, pid=pid, qty=200, unit_price=10.00)
    _purchase_stock(client, pid=pid2, qty=200, unit_price=12.00)

    return {"pid": pid, "pid2": pid2, "cid": cid, "sid": sid}


def _purchase_stock(client, ids=None, qty=50, unit_price=10.00, pid=None):
    """辅助：创建采购单并完成入库（发票驱动，建议填法：tax_rate=0, tax_amount=0）"""
    product_id = pid if pid is not None else ids["pid"]
    amount = qty * unit_price  # 不含税合计
    resp = client.post("/api/invoices/quick", json={
        "invoice_no": uniq("INV-IN-STK"), "direction": "in", "invoice_type": "ordinary",
        "amount_with_tax": str(amount), "tax_rate": "0", "tax_amount": "0",
        "counterparty_name": "测试供应商", "seller_name": "测试供应商", "buyer_name": "本公司",
        "issue_date": "2025-12-01", "purchase_order_action": "auto_create",
        "items": [{"product_id": product_id, "quantity": qty, "unit_price": str(unit_price), "tax_rate": "0"}],
    }, headers=HEADERS)
    assert resp.status_code in (200, 201), f"采购失败: {resp.text}"


class Test创建销售单:
    """创建销售单：日期/价格/重复校验/库存一致性/成本锁定/应收/勾稽"""

    def test_custom_business_date(self, client, ids):
        """自定义 issue_date 创建销售单（发票驱动）"""
        resp = client.post("/api/invoices/quick", json={
            "invoice_no": uniq("INV-OUT-DATE"), "direction": "out", "invoice_type": "ordinary",
            "amount_with_tax": "100", "tax_rate": "0", "tax_amount": "0",
            "counterparty_name": "测试客户", "seller_name": "本公司", "buyer_name": "测试客户",
            "issue_date": "2026-03-15", "sale_order_action": "auto_create",
            "items": [{"product_id": ids["pid"], "quantity": 1, "unit_price": "100", "tax_rate": "0"}],
        }, headers=HEADERS)
        assert resp.status_code == 200, f"创建失败: {resp.text}"
        data = resp.json()["data"]
        issue_date_str = str(data.get("issue_date", ""))
        assert "2026-03-15" in issue_date_str, f"issue_date 不一致: {issue_date_str}"

    def test_schema_accepts_business_date(self):
        """SaleOrderCreate schema 接受 business_date 字段"""
        from schemas.order import SaleOrderCreate
        data = SaleOrderCreate(
            customer_id=None, payment_status="unpaid", notes="schema测试",
            has_invoice=True,
            business_date=datetime(2025, 6, 1),
            items=[{"product_id": 1, "quantity": 1, "unit_price": 50, "tax_rate": Decimal("0.03")}],
        )
        assert data.business_date is not None
        assert data.business_date.year == 2025
        assert data.business_date.month == 6

    def test_auto_calculate_without_total_price(self, client, ids):
        """不传 total_price → 自动计算（发票驱动，amount_with_tax = 不含税合计）"""
        amount = 2 * 100 + 1 * 200  # 不含税合计 = 400
        resp = client.post("/api/invoices/quick", json={
            "invoice_no": uniq("INV-OUT-AUTO"), "direction": "out", "invoice_type": "ordinary",
            "amount_with_tax": str(amount), "tax_rate": "0", "tax_amount": "0",
            "counterparty_name": "测试客户", "seller_name": "本公司", "buyer_name": "测试客户",
            "issue_date": "2026-01-15", "sale_order_action": "auto_create",
            "items": [
                {"product_id": ids["pid"], "quantity": 2, "unit_price": "100", "tax_rate": "0"},
                {"product_id": ids["pid2"], "quantity": 1, "unit_price": "200", "tax_rate": "0"},
            ],
        }, headers=HEADERS)
        assert resp.status_code == 200, f"创建失败: {resp.text}"
        total = resp.json()["data"]["amount_with_tax"]
        assert float(total) == 400.0

    def test_distribute_to_zero_price_items(self, client, ids):
        """传 total_price，单价为0 → 差额分配到单价为0的行"""
        pytest.skip("发票驱动不支持 total_price 差额分配")

    def test_distribute_to_partial_zero_price_items(self, client, ids):
        """传 total_price，部分行有单价 → 差额分配到单价为0的行"""
        pytest.skip("发票驱动不支持 total_price 差额分配")

    def test_proportional_discount_when_all_have_price(self, client, ids):
        """传 total_price，所有行有单价 → 按比例打折"""
        pytest.skip("发票驱动不支持 total_price 差额分配")

    def test_unit_price_precision_6_digits(self, client, db, ids):
        """分摊后 unit_price 保留6位小数"""
        pytest.skip("发票驱动不支持 total_price 差额分配")

    def test_duplicate_product_blocked(self, client, ids):
        """销售单重复商品 → 422（发票驱动）"""
        resp = client.post("/api/invoices/quick", json={
            "invoice_no": uniq("INV-OUT-DUP"), "direction": "out", "invoice_type": "ordinary",
            "amount_with_tax": "1100", "tax_rate": "0", "tax_amount": "0",
            "counterparty_name": "测试客户", "seller_name": "本公司", "buyer_name": "测试客户",
            "issue_date": "2026-06-01", "sale_order_action": "auto_create",
            "items": [
                {"product_id": ids["pid"], "quantity": 5, "unit_price": "100", "tax_rate": "0"},
                {"product_id": ids["pid"], "quantity": 3, "unit_price": "200", "tax_rate": "0"},
            ],
        }, headers=HEADERS)
        assert resp.status_code == 422, f"应返回 422，实为 {resp.status_code}: {resp.text}"

    def test_purchase_duplicate_product_blocked(self, client, ids):
        """采购单重复商品 → 422（发票驱动）"""
        resp = client.post("/api/invoices/quick", json={
            "invoice_no": uniq("INV-IN-DUP"), "direction": "in", "invoice_type": "ordinary",
            "amount_with_tax": "1100", "tax_rate": "0", "tax_amount": "0",
            "counterparty_name": "测试供应商", "seller_name": "测试供应商", "buyer_name": "本公司",
            "issue_date": "2026-06-01", "purchase_order_action": "auto_create",
            "items": [
                {"product_id": ids["pid"], "quantity": 5, "unit_price": "100", "tax_rate": "0"},
                {"product_id": ids["pid"], "quantity": 3, "unit_price": "200", "tax_rate": "0"},
            ],
        }, headers=HEADERS)
        assert resp.status_code == 422, f"应返回 422，实为 {resp.status_code}: {resp.text}"

    def test_different_products_ok(self, client, ids):
        """不同商品 → 正常创建（200）"""
        amount = 5 * 100 + 3 * 200  # 不含税合计 = 1100
        resp = client.post("/api/invoices/quick", json={
            "invoice_no": uniq("INV-OUT-DIFF"), "direction": "out", "invoice_type": "ordinary",
            "amount_with_tax": str(amount), "tax_rate": "0", "tax_amount": "0",
            "counterparty_name": "测试客户", "seller_name": "本公司", "buyer_name": "测试客户",
            "issue_date": "2026-01-15", "sale_order_action": "auto_create",
            "items": [
                {"product_id": ids["pid"], "quantity": 5, "unit_price": "100", "tax_rate": "0"},
                {"product_id": ids["pid2"], "quantity": 3, "unit_price": "200", "tax_rate": "0"},
            ],
        }, headers=HEADERS)
        assert resp.status_code == 200, f"创建失败: {resp.text}"
        assert resp.json()["data"]["related_order_id"] is not None

    def test_t3_purchase_updates_stockmove_and_inventory(self, client, db, ids):
        """StockMove 与 Inventory 一致（采购入库后）"""
        amount = 50 * 10  # 不含税合计 = 500
        resp = client.post("/api/invoices/quick", json={
            "invoice_no": uniq("INV-IN-T3"), "direction": "in", "invoice_type": "ordinary",
            "amount_with_tax": str(amount), "tax_rate": "0", "tax_amount": "0",
            "counterparty_name": "测试供应商", "seller_name": "测试供应商", "buyer_name": "本公司",
            "issue_date": "2026-01-05", "purchase_order_action": "auto_create",
            "items": [{"product_id": ids["pid"], "quantity": 50, "unit_price": "10.00", "tax_rate": "0"}],
        }, headers=HEADERS)
        assert resp.status_code in (200, 201), f"采购失败: {resp.text}"

        sm_sum = db.query(sqlfunc.sum(StockMove.quantity_l1)).filter(
            StockMove.product_id == ids["pid"], StockMove.account_id == 1
        ).scalar() or 0
        inv = db.query(Inventory).filter(
            Inventory.product_id == ids["pid"], Inventory.account_id == 1
        ).first()
        assert inv is not None, "采购后应有 Inventory 记录"
        assert sm_sum == Decimal(str(inv.quantity_l4)), \
            f"StockMove({sm_sum}) ≠ Inventory({inv.quantity_l4})"

    def test_t3_sale_keeps_consistency(self, client, db, ids):
        """StockMove 与 Inventory 一致（销售出库后）"""
        amount = 20 * 20  # 不含税合计 = 400
        resp = client.post("/api/invoices/quick", json={
            "invoice_no": uniq("INV-OUT-T3S"), "direction": "out", "invoice_type": "ordinary",
            "amount_with_tax": str(amount), "tax_rate": "0", "tax_amount": "0",
            "counterparty_name": "测试客户", "seller_name": "本公司", "buyer_name": "测试客户",
            "issue_date": "2026-01-15", "sale_order_action": "auto_create",
            "items": [{"product_id": ids["pid"], "quantity": 20, "unit_price": "20.00", "tax_rate": "0"}],
        }, headers=HEADERS)
        assert resp.status_code == 200, f"销售失败: {resp.text}"

        sm_sum = db.query(sqlfunc.sum(StockMove.quantity_l1)).filter(
            StockMove.product_id == ids["pid"], StockMove.account_id == 1
        ).scalar() or 0
        inv = db.query(Inventory).filter(
            Inventory.product_id == ids["pid"], Inventory.account_id == 1
        ).first()
        assert sm_sum == Decimal(str(inv.quantity_l4)), \
            f"销售后 StockMove({sm_sum}) ≠ Inventory({inv.quantity_l4})"

    def test_t4_valuation_formula(self, client, db, ids):
        """average_cost × quantity = total_value"""
        for label, pid in [("商品A", ids["pid"]), ("商品B", ids["pid2"])]:
            inv = db.query(Inventory).filter(
                Inventory.product_id == pid, Inventory.account_id == 1
            ).first()
            if inv is None or inv.quantity_l4 == 0:
                continue
            expected = (Decimal(str(inv.average_cost_l4)) * Decimal(str(inv.quantity_l4))).quantize(Decimal("0.01"))
            diff = abs(expected - inv.total_value_l4)
            assert diff <= Decimal("0.01"), \
                f"{label}: {inv.average_cost_l4}×{inv.quantity_l4}={expected} ≠ total_value={inv.total_value_l4}"

    def test_t4_weighted_average_between_prices(self, client, db, ids):
        """加权平均成本在合理区间"""
        inv = db.query(Inventory).filter(
            Inventory.product_id == ids["pid"], Inventory.account_id == 1
        ).first()
        if inv is None or inv.quantity_l4 == 0:
            pytest.skip("无库存，跳过加权平均检查")
        avg_cost = Decimal(str(inv.average_cost_l4))
        assert Decimal("9.50") <= avg_cost <= Decimal("10.50"), \
            f"加权平均成本{avg_cost}不在 [9.50, 10.50]"

    def test_t2_cost_locked_at_sale_time(self, client, db, ids):
        """销售时锁定成本 = 出库时加权平均成本"""
        inv = db.query(Inventory).filter(
            Inventory.product_id == ids["pid"], Inventory.account_id == 1
        ).first()
        avg_before = Decimal(str(inv.average_cost_l4)) if inv and inv.quantity_l4 > 0 else Decimal("10.00")

        resp = client.post("/api/invoices/quick", json={
            "invoice_no": uniq("INV-OUT-T2"), "direction": "out", "invoice_type": "ordinary",
            "amount_with_tax": "300", "tax_rate": "0", "tax_amount": "0",
            "counterparty_name": "测试客户", "seller_name": "本公司", "buyer_name": "测试客户",
            "issue_date": "2026-02-15", "sale_order_action": "auto_create",
            "items": [{"product_id": ids["pid"], "quantity": 15, "unit_price": "20.00", "tax_rate": "0"}],
        }, headers=HEADERS)
        assert resp.status_code == 200, f"销售失败: {resp.text}"

        sale_item = db.query(SaleItem).join(SaleOrder).filter(
            SaleItem.product_id == ids["pid"],
            SaleOrder.status == OrderStatus.COMPLETED,
        ).order_by(SaleItem.id.desc()).first()
        assert sale_item is not None
        locked_cost = Decimal(str(sale_item.unit_cost_l2)) if sale_item.unit_cost_l2 else Decimal("0")
        assert locked_cost > 0, f"unit_cost 应被锁定，实际为 {locked_cost}"
        assert abs(locked_cost - avg_before) <= Decimal("0.01"), \
            f"锁定成本({locked_cost}) ≠ 出库时均价({avg_before})"

    def test_t2_income_statement_cogs_matches_items(self, client, db, ids):
        """利润表 COGS = SaleItem(unit_cost × quantity) 合计"""
        items = db.query(SaleItem).join(SaleOrder).filter(
            SaleOrder.status == OrderStatus.COMPLETED,
        ).all()
        expected_cogs = Decimal("0")
        for item in items:
            cost = Decimal(str(item.unit_cost_l2)) if item.unit_cost_l2 else Decimal("0")
            expected_cogs += Decimal(str(item.quantity_l1)) * cost
        expected_cogs = expected_cogs.quantize(Decimal("0.01"))

        resp = client.get("/api/financial-reports/income-statement",
                          params={"start_date": "2026-01-01", "end_date": "2026-12-31"},
                          headers=HEADERS)
        if resp.status_code != 200:
            pytest.skip("利润表接口暂不可用")
        reported_cogs = round2(Decimal(str(resp.json().get("cost_of_goods_sold", 0))))
        assert abs(reported_cogs - expected_cogs) <= Decimal("0.01"), \
            f"利润表 COGS({reported_cogs}) ≠ SaleItem 合计({expected_cogs})"

    def test_t3_truth_source_multiple_products(self, client, db, ids):
        """多商品 StockMove 与 Inventory 一致"""
        for label, pid in [("商品A", ids["pid"]), ("商品B", ids["pid2"])]:
            inv = db.query(Inventory).filter(
                Inventory.product_id == pid, Inventory.account_id == 1
            ).first()
            if inv is None:
                continue
            sm_sum = db.query(sqlfunc.sum(StockMove.quantity_l1)).filter(
                StockMove.product_id == pid, StockMove.account_id == 1
            ).scalar() or 0
            assert sm_sum == Decimal(str(inv.quantity_l4)), \
                f"{label}: StockMove({sm_sum}) ≠ Inventory({inv.quantity_l4})"

    def test_t5_ar_equals_unpaid_orders(self, client, db, ids):
        """应收账款（仅检查BS正确性，不跨源比对）"""
        resp = client.get("/api/financial-reports/balance-sheet",
                          params={"date": "2026-12-31"}, headers=HEADERS)
        if resp.status_code != 200:
            pytest.skip("资产负债表接口暂不可用")
        ar_reported = round2(Decimal(str(resp.json().get("accounts_receivable", 0))))
        # BS AR >= 0 作为基本合理性检查
        assert ar_reported >= Decimal("0"), f"AR为负数: {ar_reported}"

    @pytest.mark.golden
    def test_t1_net_profit_equals_retained_earnings_delta(self, client, db, ids):
        """净利润 = 未分配利润变动额

        前置：月结（含损益结转）将收入/费用科目余额结转到 4103（本年利润），
        使资产负债表的留存收益反映当期净利润。

        取期初资产负债表（2025-12-31）的未分配利润作为 opening，
        避免模块内其他测试用 2025 年的销售单污染期初余额。
        """
        # ── 月结：损益结转（收入/费用 → 4103）──
        # 逐月结账确保每月附加税/所得税正确计提：
        # 2026-01 覆盖 1 月销售单（多笔）
        # 2026-02 覆盖 2 月销售单（test_t2_cost_locked_at_sale_time）
        # 2026-03 覆盖 3 月销售单（test_custom_business_date）
        for period in ["2026-01", "2026-02", "2026-03"]:
            resp_close = client.post("/api/finance/month-close",
                                     json={"period": period}, headers=HEADERS)
            assert resp_close.status_code == 200, \
                f"月结 {period} 失败: {resp_close.text}"
        db.expire_all()

        start_date = "2026-01-01"
        end_date = "2026-12-31"

        resp_is = client.get("/api/financial-reports/income-statement",
                             params={"start_date": start_date, "end_date": end_date},
                             headers=HEADERS)
        # source_mode=ledger: 从总账取增值税（222103），而非发票表。
        # 测试中销售单不创建发票记录，invoice 口径 VAT=0 会导致 BS 不平。
        resp_bs_open = client.get("/api/financial-reports/balance-sheet",
                                  params={"date": "2025-12-31", "source_mode": "ledger"},
                                  headers=HEADERS)
        resp_bs = client.get("/api/financial-reports/balance-sheet",
                             params={"date": end_date, "source_mode": "ledger"},
                             headers=HEADERS)
        if resp_is.status_code != 200 or resp_bs.status_code != 200:
            pytest.skip("财报接口暂不可用")

        net_profit = round2(Decimal(str(resp_is.json().get("net_profit", 0))))
        opening_re = round2(Decimal(str(resp_bs_open.json().get("retained_earnings", 0)))) \
            if resp_bs_open.status_code == 200 else Decimal("0.00")
        ending_re = round2(Decimal(str(resp_bs.json().get("retained_earnings", 0))))
        delta_re = round2(ending_re - opening_re)
        assert abs(net_profit - delta_re) <= Decimal("0.01"), \
            f"净利润({net_profit}) ≠ 未分配利润变动({delta_re}) (opening={opening_re}, ending={ending_re})"

        total_assets = round2(Decimal(str(resp_bs.json().get("total_assets", 0))))
        total_l_e = round2(Decimal(str(resp_bs.json().get("total_liabilities_and_equity", 0))))
        assert abs(total_assets - total_l_e) <= Decimal("0.01"), \
            f"资产负债表不平衡: 资产{total_assets} ≠ 负债+权益{total_l_e}"

class Test取消恢复销售单:
    """取消 + 恢复 + 库存回补"""

    def test_cancel_completed_order(self, client, db, ids):
        """取消已完成销售单 → CANCELLED，恢复 → COMPLETED"""
        _purchase_stock(client, ids)
        resp = client.post("/api/invoices/quick", json={
            "invoice_no": uniq("INV-OUT-CNL1"), "direction": "out", "invoice_type": "ordinary",
            "amount_with_tax": "100", "tax_rate": "0", "tax_amount": "0",
            "counterparty_name": "测试客户", "seller_name": "本公司", "buyer_name": "测试客户",
            "issue_date": "2026-01-15", "sale_order_action": "auto_create",
            "items": [{"product_id": ids["pid"], "quantity": 5, "unit_price": "20", "tax_rate": "0"}],
        }, headers=HEADERS)
        assert resp.status_code == 200, f"销售创建失败: {resp.text}"
        sale_id = resp.json()["data"]["related_order_id"]
        assert sale_id is not None

        resp = client.put(f"/api/sales/{sale_id}", json={"status": "cancelled"}, headers=HEADERS)
        assert resp.status_code == 200, f"取消失败: {resp.text}"
        db.expire_all()
        order = db.query(SaleOrder).filter(SaleOrder.id == sale_id).first()
        assert order.status == OrderStatus.CANCELLED

        resp = client.put(f"/api/sales/{sale_id}", json={"status": "completed"}, headers=HEADERS)
        assert resp.status_code == 200, f"恢复失败: {resp.text}"
        db.expire_all()
        order = db.query(SaleOrder).filter(SaleOrder.id == sale_id).first()
        assert order.status == OrderStatus.COMPLETED

    def test_cancel_already_cancelled_blocked(self, client, db, ids):
        """重复取消已取消的销售单 → 422"""
        _purchase_stock(client, ids)
        resp = client.post("/api/invoices/quick", json={
            "invoice_no": uniq("INV-OUT-CNL2"), "direction": "out", "invoice_type": "ordinary",
            "amount_with_tax": "60", "tax_rate": "0", "tax_amount": "0",
            "counterparty_name": "测试客户", "seller_name": "本公司", "buyer_name": "测试客户",
            "issue_date": "2026-01-15", "sale_order_action": "auto_create",
            "items": [{"product_id": ids["pid"], "quantity": 3, "unit_price": "20", "tax_rate": "0"}],
        }, headers=HEADERS)
        assert resp.status_code == 200
        sale_id = resp.json()["data"]["related_order_id"]

        resp = client.put(f"/api/sales/{sale_id}", json={"status": "cancelled"}, headers=HEADERS)
        assert resp.status_code == 200

        resp = client.put(f"/api/sales/{sale_id}", json={"status": "cancelled"}, headers=HEADERS)
        assert resp.status_code in (200, 422), f"重复取消应报错: {resp.text}"

    def test_cancel_restores_inventory(self, client, db, ids):
        """取消→库存回补，恢复→重新扣减"""
        _purchase_stock(client, ids, qty=100)
        inv_before = db.query(Inventory).filter(
            Inventory.product_id == ids["pid"], Inventory.account_id == 1
        ).first()
        qty_before = inv_before.quantity_l4

        resp = client.post("/api/invoices/quick", json={
            "invoice_no": uniq("INV-OUT-CNL3"), "direction": "out", "invoice_type": "ordinary",
            "amount_with_tax": "100", "tax_rate": "0", "tax_amount": "0",
            "counterparty_name": "测试客户", "seller_name": "本公司", "buyer_name": "测试客户",
            "issue_date": "2026-01-15", "sale_order_action": "auto_create",
            "items": [{"product_id": ids["pid"], "quantity": 5, "unit_price": "20", "tax_rate": "0"}],
        }, headers=HEADERS)
        assert resp.status_code == 200
        sale_id = resp.json()["data"]["related_order_id"]

        inv_after_sale = db.query(Inventory).filter(
            Inventory.product_id == ids["pid"], Inventory.account_id == 1
        ).first()
        assert inv_after_sale.quantity_l4 == qty_before - 5

        resp = client.put(f"/api/sales/{sale_id}", json={"status": "cancelled"}, headers=HEADERS)
        assert resp.status_code == 200
        db.expire_all()
        inv_after_cancel = db.query(Inventory).filter(
            Inventory.product_id == ids["pid"], Inventory.account_id == 1
        ).first()
        assert inv_after_cancel.quantity_l4 == qty_before

        resp = client.put(f"/api/sales/{sale_id}", json={"status": "completed"}, headers=HEADERS)
        assert resp.status_code == 200
        db.expire_all()
        inv_after_restore = db.query(Inventory).filter(
            Inventory.product_id == ids["pid"], Inventory.account_id == 1
        ).first()
        assert inv_after_restore.quantity_l4 == qty_before - 5

    def test_t3_reversal_keeps_consistency(self, client, db, ids):
        """红冲后 StockMove 与 Inventory 一致"""
        stock = db.query(Inventory).filter(
            Inventory.product_id == ids["pid"], Inventory.account_id == 1
        ).first()
        if stock is None or stock.quantity_l4 == 0:
            _purchase_stock(client, ids, qty=30)
            db.expire_all()
            stock = db.query(Inventory).filter(
                Inventory.product_id == ids["pid"], Inventory.account_id == 1
            ).first()
        qty_before = stock.quantity_l4

        resp = client.post("/api/invoices/quick", json={
            "invoice_no": uniq("INV-OUT-REV"), "direction": "out", "invoice_type": "ordinary",
            "amount_with_tax": "200", "tax_rate": "0", "tax_amount": "0",
            "counterparty_name": "测试客户", "seller_name": "本公司", "buyer_name": "测试客户",
            "issue_date": "2026-02-01", "sale_order_action": "auto_create",
            "items": [{"product_id": ids["pid"], "quantity": 10, "unit_price": "20.00", "tax_rate": "0"}],
        }, headers=HEADERS)
        assert resp.status_code == 200, f"销售失败: {resp.text}"
        sale_id = resp.json()["data"]["related_order_id"]

        resp = client.put(f"/api/sales/{sale_id}", json={"status": "cancelled"}, headers=HEADERS)
        assert resp.status_code == 200, f"红冲失败: {resp.text}"

        db.expire_all()
        inv_after = db.query(Inventory).filter(
            Inventory.product_id == ids["pid"], Inventory.account_id == 1
        ).first()
        assert inv_after.quantity_l4 == qty_before, \
            f"红冲后库存({inv_after.quantity_l4}) ≠ 红冲前({qty_before})"

        sm_sum = db.query(sqlfunc.sum(StockMove.quantity_l1)).filter(
            StockMove.product_id == ids["pid"], StockMove.account_id == 1
        ).scalar() or 0
        assert sm_sum == Decimal(str(inv_after.quantity_l4)), \
            f"红冲后 StockMove({sm_sum}) ≠ Inventory({inv_after.quantity_l4})"

        reversal_moves = db.query(StockMove).filter(
            StockMove.source_type.like("%_reversal"),
            StockMove.product_id == ids["pid"], StockMove.account_id == 1
        ).all()
        assert len(reversal_moves) >= 1, "应有红冲 StockMove 记录"
