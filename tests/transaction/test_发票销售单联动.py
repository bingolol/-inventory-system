"""事务测试：发票联动销售单/采购单与 /quick 合并端点

涵盖：销项发票联动销售单、进项发票联动采购单、/quick 合并端点、校验拒绝场景
"""
import pytest
from decimal import Decimal

pytestmark = pytest.mark.usefixtures("bootstrap_db")

from tests.helpers import get_account_id, get_entity_id, uniq
from models import Invoice, SaleOrder, FixedAsset
from accounting_engine import AccountingEngine

HEADERS = {"X-Account-ID": "1", "X-Operator": "user"}


def _product_id(c):
    resp = c.post("/api/products", json={
        "name": uniq("商品-"), "sku": uniq("SKU-"), "category": "测试",
        "unit": "个", "purchase_price": 50, "sale_price": 100,
    }, headers=HEADERS)
    assert resp.status_code == 200
    body = resp.json()
    return body.get("entity_id") or body.get("data", {}).get("id") or body.get("id")


def _purchase_stock(client, pid, qty=50):
    """辅助：创建采购单并完成入库"""
    tag = uniq("PO")
    from tests.factories import api_create_supplier
    sid, _ = api_create_supplier(client, HEADERS)
    resp = client.post("/api/purchases", json={
        "supplier_id": sid, "payment_method": "company", "payment_status": "unpaid",
        "business_date": "2026-06-01",
        "items": [{"product_id": pid, "quantity": qty, "unit_price": 50, "tax_rate": 0.13}],
    }, headers=HEADERS)
    assert resp.status_code in (200, 201), f"采购失败: {resp.text}"


def _out_payload(pid):
    return {
        "invoice_no": uniq("INV-OUT-"),
        "direction": "out",
        "invoice_type": "ordinary",
        "amount_with_tax": "1030.00",
        "tax_amount": "30.00",
        "tax_rate": "0.03",
        "counterparty_name": "测试买方公司",
        "seller_name": "本公司",
        "buyer_name": "测试买方公司",
        "issue_date": "2026-06-15",
        "items": [{"product_id": pid, "quantity": 10, "unit_price": "100.00", "tax_rate": "0.03"}],
        "sale_order_action": "auto_create",
    }


def _in_payload(pid):
    return {
        "invoice_no": uniq("INV-IN-"),
        "direction": "in",
        "invoice_type": "special",
        "amount_with_tax": "11300.00",
        "tax_amount": "1300.00",
        "tax_rate": "0.13",
        "counterparty_name": "测试供应商",
        "seller_name": "测试供应商",
        "buyer_name": "本公司",
        "issue_date": "2026-06-01",
        "notes": "quick 合并测试",
        "purchase_order_action": "auto_create",
        "items": [{"product_id": pid, "quantity": 1, "unit_price": "10000.00", "tax_rate": "0.13"}],
    }


class Test销项发票联动销售单:
    """销项发票自动创建销售单"""

    def test_out_invoice_creates_sale_order(self, db, client):
        pid = _product_id(client)
        _purchase_stock(client, pid)
        payload = _out_payload(pid)
        r = client.post("/api/invoices/quick", json=payload, headers=HEADERS)
        assert r.status_code == 200, r.text
        data = r.json()["data"]
        assert data["related_order_type"] == "sale_order"
        assert data["related_order_id"] is not None
        inv = db.query(Invoice).filter(Invoice.invoice_no == payload["invoice_no"]).first()
        assert inv is not None
        assert inv.related_order_type == "sale_order"
        so = db.query(SaleOrder).filter(SaleOrder.id == inv.related_order_id).first()
        assert so is not None

    def test_out_invoice_sale_order_amounts_match(self, db, client):
        pid = _product_id(client)
        _purchase_stock(client, pid)
        payload = _out_payload(pid)
        r = client.post("/api/invoices/quick", json=payload, headers=HEADERS)
        assert r.status_code == 200, r.text
        inv = db.query(Invoice).filter(Invoice.invoice_no == payload["invoice_no"]).first()
        so = db.query(SaleOrder).filter(SaleOrder.id == inv.related_order_id).first()
        assert Decimal(str(so.total_price_l1)) == Decimal("1030.00")
        assert Decimal(str(so.tax_amount_l1)) == Decimal("30.00")

    def test_out_invoice_items_synced_to_sale_order(self, db, client):
        pid = _product_id(client)
        _purchase_stock(client, pid)
        payload = _out_payload(pid)
        r = client.post("/api/invoices/quick", json=payload, headers=HEADERS)
        assert r.status_code == 200, r.text
        inv = db.query(Invoice).filter(Invoice.invoice_no == payload["invoice_no"]).first()
        so = db.query(SaleOrder).filter(SaleOrder.id == inv.related_order_id).first()
        assert len(so.items) == 1
        item = so.items[0]
        assert item.product_id == payload["items"][0]["product_id"]
        assert item.quantity_l1 == 10
        assert len(inv.items) == 1
        assert inv.items[0].product_id == payload["items"][0]["product_id"]

    def test_out_invoice_link_existing_no_new_sale_order(self, client):
        pid = _product_id(client)
        _purchase_stock(client, pid, qty=20)
        r_sale = client.post("/api/sales", json={
            "customer_id": None, "has_invoice": True, "deduct_inventory": True, "payment_status": "unpaid",
            "business_date": "2026-06-10",
            "items": [{"product_id": pid, "quantity": 5, "unit_price": "100.00", "tax_rate": "0.03"}],
        }, headers=HEADERS)
        assert r_sale.status_code in (200, 201), r_sale.text
        existing_sale_id = get_entity_id(r_sale.json())
        payload = _out_payload(pid)
        payload["sale_order_action"] = "link_existing"
        payload["related_order_id"] = existing_sale_id
        payload["related_order_type"] = "sale_order"
        r = client.post("/api/invoices/quick", json=payload, headers=HEADERS)
        assert r.status_code == 200, r.text
        data = r.json()["data"]
        assert data["related_order_type"] == "sale_order"
        assert data["related_order_id"] == existing_sale_id


class Test进项发票联动采购单:
    """进项发票自动创建采购单"""

    def test_in_invoice_creates_purchase_order(self, client):
        pid = _product_id(client)
        payload = _out_payload(pid)
        payload["direction"] = "in"
        payload["invoice_no"] = uniq("INV-IN-")
        payload["seller_name"] = "测试供应商"
        payload["buyer_name"] = "本公司"
        payload["purchase_order_action"] = "auto_create"
        del payload["sale_order_action"]
        r = client.post("/api/invoices/quick", json=payload, headers=HEADERS)
        assert r.status_code == 200, r.text
        data = r.json()["data"]
        assert data["related_order_type"] == "purchase_order"
        assert data["related_order_id"] is not None


class TestQuick合并端点:
    """POST /api/invoices/quick 合并端点"""

    def test_quick_with_fixed_asset_creates_both(self, client):
        pid = _product_id(client)
        asset_code = uniq("FA-QUICK")
        payload = _in_payload(pid)
        payload["fixed_asset"] = {
            "asset_code": asset_code, "asset_name": "测试设备",
            "category": "电子设备", "salvage_rate": "0.05",
            "useful_life": 60, "depreciation_method": "年限平均法",
            "start_date": "2026-06-01", "accumulated_depreciation": "0", "asset_status": "在用",
        }
        r = client.post("/api/invoices/quick", json=payload, headers=HEADERS)
        assert r.status_code == 200, r.text
        data = r.json()["data"]
        assert data["related_order_type"] == "fixed_asset"
        assert data["related_order_id"] is not None
        assert data["fixed_asset"]["id"] > 0
        assert data["fixed_asset"]["asset_code"] == asset_code
        assert data["fixed_asset"]["original_value"] == "11300.00"

    def test_quick_with_fixed_asset_persisted(self, db, client):
        pid = _product_id(client)
        inv_no = uniq("INV-PERSIST")
        asset_code = uniq("FA-PERSIST")
        payload = _in_payload(pid)
        payload["invoice_no"] = inv_no
        payload["fixed_asset"] = {
            "asset_code": asset_code, "asset_name": "持久化测试设备",
            "category": "电子设备", "salvage_rate": "0.05",
            "useful_life": 36, "depreciation_method": "年限平均法",
            "start_date": "2026-06-01", "accumulated_depreciation": "0", "asset_status": "在用",
        }
        r = client.post("/api/invoices/quick", json=payload, headers=HEADERS)
        assert r.status_code == 200, r.text
        asset_id = r.json()["data"]["fixed_asset"]["id"]
        inv = db.query(Invoice).filter(Invoice.invoice_no == inv_no).first()
        assert inv is not None
        assert inv.related_order_type == "fixed_asset"
        assert inv.related_order_id == asset_id
        asset = db.query(FixedAsset).filter(FixedAsset.id == asset_id).first()
        assert asset is not None
        assert asset.asset_code == asset_code
        assert asset.name == "持久化测试设备"

    def test_quick_without_fixed_asset_creates_invoice_only(self, client):
        pid = _product_id(client)
        payload = _in_payload(pid)
        r = client.post("/api/invoices/quick", json=payload, headers=HEADERS)
        assert r.status_code == 200, r.text
        data = r.json()["data"]
        assert data["related_order_type"] == "purchase_order"
        assert "fixed_asset" not in data

    def test_quick_image_url_passthrough(self, db, client):
        pid = _product_id(client)
        inv_no = uniq("INV-IMG")
        payload = _in_payload(pid)
        payload["invoice_no"] = inv_no
        payload["image_url"] = "/uploads/invoice/test.png"
        r = client.post("/api/invoices/quick", json=payload, headers=HEADERS)
        assert r.status_code == 200, r.text
        inv = db.query(Invoice).filter(Invoice.invoice_no == inv_no).first()
        assert inv is not None
        assert inv.image_url == "/uploads/invoice/test.png"

    def test_with_fixed_asset_endpoint_removed(self, client):
        r = client.post("/api/invoices/with-fixed-asset", json={
            "invoice_no": uniq("INV-GONE"), "direction": "in", "invoice_type": "ordinary",
            "tax_rate": "0.13", "amount_with_tax": "1000.00",
            "counterparty_name": "x", "issue_date": "2026-06-01",
            "asset_code": uniq("FA-GONE"), "asset_name": "x",
            "useful_life": 12, "start_date": "2026-06-01",
        }, headers=HEADERS)
        assert r.status_code in (404, 405)

    def test_invoice_amount_equals_asset_original_value(self, client):
        pid = _product_id(client)
        payload = _in_payload(pid)
        payload["amount_with_tax"] = 11300
        payload["fixed_asset"] = {
            "asset_code": uniq("FA-001"), "asset_name": "测试设备",
            "category": "电子设备", "salvage_rate": "0.05",
            "useful_life": 60, "depreciation_method": "年限平均法",
            "start_date": "2026-06-19", "accumulated_depreciation": "0", "asset_status": "在用",
        }
        r = client.post("/api/invoices/quick", json=payload, headers=HEADERS)
        assert r.status_code == 200, r.text
        data = r.json()["data"]
        inv_amt = Decimal(str(data["amount_with_tax"]))
        asset_val = Decimal(data["fixed_asset"]["original_value"])
        assert inv_amt == asset_val == Decimal("11300.00")

    def test_invoice_amounts_auto_calculated_and_balanced(self, client):
        pid = _product_id(client)
        payload = _in_payload(pid)
        # BR-27: tax_amount 为外部输入，系统按 amount_with_tax - tax_amount 推导不含税金额
        payload["amount_with_tax"] = 22600
        payload["tax_amount"] = 2600
        payload["fixed_asset"] = {
            "asset_code": uniq("FA-002"), "asset_name": "测试设备B",
            "category": "电子设备", "salvage_rate": "0.05",
            "useful_life": 120, "depreciation_method": "年限平均法",
            "start_date": "2026-06-19", "accumulated_depreciation": "0", "asset_status": "在用",
        }
        r = client.post("/api/invoices/quick", json=payload, headers=HEADERS)
        assert r.status_code == 200, r.text
        inv = r.json()["data"]
        assert Decimal(str(inv["amount_without_tax"])) == Decimal("20000.00")
        assert Decimal(str(inv["tax_amount"])) == Decimal("2600.00")
        assert Decimal(str(inv["amount_without_tax"])) + Decimal(str(inv["tax_amount"])) == Decimal(str(inv["amount_with_tax"]))

    def test_invoice_calculation_uses_accounting_engine(self, client):
        pid = _product_id(client)
        # BR-27: tax_amount 为外部输入，系统不再调用 AccountingEngine 推导税额；
        # 本用例改为验证系统按传入的 tax_amount 正确计算 amount_without_tax。
        payload = _in_payload(pid)
        payload["amount_with_tax"] = 11300
        payload["tax_amount"] = 1300
        payload["fixed_asset"] = {
            "asset_code": uniq("FA-ENGINE"), "asset_name": "引擎测试设备",
            "category": "电子设备", "salvage_rate": "0.05",
            "useful_life": 60, "depreciation_method": "年限平均法",
            "start_date": "2026-06-19", "accumulated_depreciation": "0", "asset_status": "在用",
        }
        r = client.post("/api/invoices/quick", json=payload, headers=HEADERS)
        assert r.status_code == 200, r.text
        inv = r.json()["data"]
        assert Decimal(str(inv["amount_without_tax"])) == Decimal("10000.00")
        assert Decimal(str(inv["tax_amount"])) == Decimal("1300.00")
        assert Decimal(str(inv["amount_with_tax"])) == Decimal("11300.00")


class Test校验拒绝场景:
    """校验拒绝场景"""

    def test_out_invoice_missing_items_rejected(self, client):
        pid = _product_id(client)
        payload = _out_payload(pid)
        del payload["items"]
        r = client.post("/api/invoices/quick", json=payload, headers=HEADERS)
        assert r.status_code == 422, f"缺items应返回422, 实际{r.status_code}: {r.text}"

    def test_out_invoice_missing_seller_name_rejected(self, client):
        pid = _product_id(client)
        payload = _out_payload(pid)
        del payload["seller_name"]
        r = client.post("/api/invoices/quick", json=payload, headers=HEADERS)
        assert r.status_code == 422, f"缺seller_name应返回422, 实际{r.status_code}: {r.text}"

    def test_out_invoice_missing_buyer_name_rejected(self, client):
        pid = _product_id(client)
        payload = _out_payload(pid)
        del payload["buyer_name"]
        r = client.post("/api/invoices/quick", json=payload, headers=HEADERS)
        assert r.status_code == 422, f"缺buyer_name应返回422, 实际{r.status_code}: {r.text}"

    def test_out_invoice_missing_sale_order_action_rejected(self, client):
        pid = _product_id(client)
        payload = _out_payload(pid)
        del payload["sale_order_action"]
        r = client.post("/api/invoices/quick", json=payload, headers=HEADERS)
        assert r.status_code == 422, f"缺sale_order_action应返回422, 实际{r.status_code}: {r.text}"

    def test_out_invoice_link_existing_missing_related_order_id_rejected(self, client):
        pid = _product_id(client)
        payload = _out_payload(pid)
        payload["sale_order_action"] = "link_existing"
        r = client.post("/api/invoices/quick", json=payload, headers=HEADERS)
        assert r.status_code == 422, f"link_existing缺related_order_id应返回422, 实际{r.status_code}: {r.text}"
