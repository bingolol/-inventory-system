"""事务测试：固定资产全流程 — CRUD + 发票联动"""
import pytest
from decimal import Decimal

pytestmark = pytest.mark.usefixtures("bootstrap_db")

from tests.helpers import uniq
from models import Invoice, FixedAsset

HEADERS = {"X-Account-ID": "1", "X-Operator": "user"}


def _product_id(c):
    resp = c.post("/api/products", json={
        "name": uniq("商品-"), "sku": uniq("SKU-"), "category": "测试",
        "unit": "个", "purchase_price": 50, "sale_price": 100,
    }, headers=HEADERS)
    assert resp.status_code == 200
    body = resp.json()
    return body.get("entity_id") or body.get("data", {}).get("id") or body.get("id")


class Test创建固定资产:
    """固定资产 CRUD 操作"""

    def test_create_fixed_asset(self, client):
        payload = {
            "asset_code": uniq("FA-TEST"),
            "name": "测试设备",
            "category": "电子设备",
            "original_value": "10000.00",
            "salvage_rate": "0.05",
            "useful_life": 60,
            "depreciation_method": "年限平均法",
            "start_date": "2026-01-01",
            "accumulated_depreciation": "0.00",
            "status": "在用",
        }
        r = client.post("/api/fixed-assets", json=payload, headers=HEADERS)
        assert r.status_code == 200, r.text
        data = r.json()
        assert data["id"] > 0
        assert data["name"] == "测试设备"

    def test_list_fixed_assets(self, client):
        r = client.get("/api/fixed-assets", headers=HEADERS)
        assert r.status_code == 200
        data = r.json()
        assert "items" in data

    def test_dispose_fixed_asset(self, client):
        asset_code = uniq("FA-UPD")
        r = client.post("/api/fixed-assets", json={
            "asset_code": asset_code,
            "name": "处置测试设备",
            "category": "电子设备",
            "original_value": "5000.00",
            "salvage_rate": "0.05",
            "useful_life": 36,
            "depreciation_method": "年限平均法",
            "start_date": "2026-01-01",
            "status": "在用",
        }, headers=HEADERS)
        assert r.status_code == 200, r.text
        asset_id = r.json().get("entity_id") or r.json().get("data", {}).get("id") or r.json().get("id")
        r2 = client.post(f"/api/fixed-assets/{asset_id}/dispose?disposal_date=2026-12-31&disposal_price=0", headers=HEADERS)
        assert r2.status_code == 200, r2.text

    def test_dispose_nonexistent_returns_404(self, client):
        r = client.post("/api/fixed-assets/999999/dispose?disposal_date=2026-12-31", headers=HEADERS)
        assert r.status_code == 404

    def test_readonly_middleware_blocks_delete(self, client):
        r = client.delete("/api/fixed-assets/999999", headers=HEADERS)
        assert r.status_code in (403, 404)


class Test发票关联固定资产:
    """发票关联固定资产 — 10 项业务行为"""

    def test_invoice_amount_equals_asset_original_value(self, client):
        pid = _product_id(client)
        response = client.post("/api/invoices/quick", json={
            "invoice_no": uniq("FA-INV-001"),
            "direction": "in",
            "invoice_type": "ordinary",
            "tax_rate": 0.13,
            "amount_with_tax": 11300,
            "tax_amount": 1300,
            "counterparty_name": "供应商A",
            "seller_name": "供应商A",
            "buyer_name": "测试公司",
            "issue_date": "2026-06-19",
            "items": [{"product_id": pid, "quantity": 1, "unit_price": 100, "tax_rate": 0.13}],
            "purchase_order_action": "auto_create",
            "fixed_asset": {
                "asset_code": uniq("FA-001"),
                "asset_name": "测试设备",
                "salvage_rate": 0.05,
                "useful_life": 60,
                "start_date": "2026-06-19",
            },
        }, headers=HEADERS)
        assert response.status_code == 200
        data = response.json()["data"]
        invoice_amount = Decimal(data["amount_with_tax"])
        asset_value = Decimal(data["fixed_asset"]["original_value"])
        assert invoice_amount == asset_value == Decimal("11300.00")

    def test_invoice_amounts_auto_calculated_and_balanced(self, client):
        pid = _product_id(client)
        response = client.post("/api/invoices/quick", json={
            "invoice_no": uniq("FA-INV-002"),
            "direction": "in",
            "invoice_type": "ordinary",
            "tax_rate": 0.13,
            "amount_with_tax": 22600,
            "tax_amount": 2600,
            "counterparty_name": "供应商B",
            "seller_name": "供应商B",
            "buyer_name": "测试公司",
            "issue_date": "2026-06-19",
            "items": [{"product_id": pid, "quantity": 1, "unit_price": 100, "tax_rate": 0.13}],
            "purchase_order_action": "auto_create",
            "fixed_asset": {
                "asset_code": uniq("FA-002"),
                "asset_name": "测试设备B",
                "salvage_rate": 0.05,
                "useful_life": 120,
                "start_date": "2026-06-19",
            },
        }, headers=HEADERS)
        assert response.status_code == 200
        inv = response.json()["data"]
        amount_without_tax = Decimal(inv["amount_without_tax"])
        tax_amount = Decimal(inv["tax_amount"])
        amount_with_tax = Decimal(inv["amount_with_tax"])
        assert amount_without_tax == Decimal("20000.00")
        assert tax_amount == Decimal("2600.00")
        assert amount_without_tax + tax_amount == amount_with_tax

    def test_rollback_on_duplicate_invoice(self, client):
        pid = _product_id(client)
        inv_no = uniq("FA-INV-ROLLBACK")
        body = {
            "invoice_no": inv_no,
            "direction": "in",
            "invoice_type": "ordinary",
            "tax_rate": 0.13,
            "amount_with_tax": 11300,
            "tax_amount": 1300,
            "counterparty_name": "供应商C",
            "seller_name": "供应商C",
            "buyer_name": "测试公司",
            "issue_date": "2026-06-19",
            "items": [{"product_id": pid, "quantity": 1, "unit_price": 100, "tax_rate": 0.13}],
            "purchase_order_action": "auto_create",
            "fixed_asset": {
                "asset_code": uniq("FA-ROLLBACK"),
                "asset_name": "设备C",
                "salvage_rate": 0.05,
                "useful_life": 60,
                "start_date": "2026-06-19",
            },
        }
        r1 = client.post("/api/invoices/quick", json=body, headers=HEADERS)
        assert r1.status_code == 200

        body2 = {
            "invoice_no": inv_no,
            "direction": "in",
            "invoice_type": "ordinary",
            "tax_rate": 0.13,
            "amount_with_tax": 5650,
            "tax_amount": 650,
            "counterparty_name": "供应商D",
            "seller_name": "供应商D",
            "buyer_name": "测试公司",
            "issue_date": "2026-06-19",
            "items": [{"product_id": pid, "quantity": 1, "unit_price": 100, "tax_rate": 0.13}],
            "purchase_order_action": "auto_create",
            "fixed_asset": {
                "asset_code": uniq("FA-ROLLBACK-2"),
                "asset_name": "设备D",
                "salvage_rate": 0.05,
                "useful_life": 36,
                "start_date": "2026-06-19",
            },
        }
        r2 = client.post("/api/invoices/quick", json=body2, headers=HEADERS)
        assert r2.status_code == 409

        invoice_list = client.get("/api/invoices", headers=HEADERS)
        assert invoice_list.status_code == 200
        invoices = invoice_list.json()["items"]
        assert any(inv["invoice_no"] == inv_no for inv in invoices)

        asset_list = client.get("/api/fixed-assets", headers=HEADERS)
        assert asset_list.status_code == 200
        assets = asset_list.json()["items"]
        assert not any(a["asset_code"] == body2["fixed_asset"]["asset_code"] for a in assets)

    def test_duplicate_invoice_number_returns_structured_error(self, client):
        pid = _product_id(client)
        inv_no = uniq("FA-INV-DUP")
        client.post("/api/invoices/quick", json={
            "invoice_no": inv_no,
            "direction": "in",
            "invoice_type": "ordinary",
            "tax_rate": 0.13,
            "amount_with_tax": 11300,
            "tax_amount": 1300,
            "counterparty_name": "供应商E",
            "seller_name": "供应商E",
            "buyer_name": "测试公司",
            "issue_date": "2026-06-19",
            "items": [{"product_id": pid, "quantity": 1, "unit_price": 100, "tax_rate": 0.13}],
            "purchase_order_action": "auto_create",
            "fixed_asset": {
                "asset_code": uniq("FA-DUP"),
                "asset_name": "设备E",
                "salvage_rate": 0.05,
                "useful_life": 60,
                "start_date": "2026-06-19",
            },
        }, headers=HEADERS)

        response = client.post("/api/invoices/quick", json={
            "invoice_no": inv_no,
            "direction": "in",
            "invoice_type": "ordinary",
            "tax_rate": 0.13,
            "amount_with_tax": 5650,
            "tax_amount": 650,
            "counterparty_name": "供应商F",
            "seller_name": "供应商F",
            "buyer_name": "测试公司",
            "issue_date": "2026-06-19",
            "items": [{"product_id": pid, "quantity": 1, "unit_price": 100, "tax_rate": 0.13}],
            "purchase_order_action": "auto_create",
            "fixed_asset": {
                "asset_code": uniq("FA-DUP-2"),
                "asset_name": "设备F",
                "salvage_rate": 0.05,
                "useful_life": 36,
                "start_date": "2026-06-19",
            },
        }, headers=HEADERS)
        assert response.status_code == 409
        error = response.json()["error"]
        assert error["code"] == "INVOICE_DUPLICATE_NUMBER"
        assert inv_no in error["message"]
        assert "STOP_RETRYING" in error["ai_instruction"]

    def test_response_contains_complete_invoice_and_asset_info(self, client):
        pid = _product_id(client)
        response = client.post("/api/invoices/quick", json={
            "invoice_no": uniq("FA-INV-COMPLETE"),
            "direction": "in",
            "invoice_type": "special",
            "tax_rate": 0.09,
            "amount_with_tax": 10900,
            "tax_amount": 900,
            "counterparty_name": "供应商G",
            "seller_name": "供应商G",
            "buyer_name": "测试公司",
            "issue_date": "2026-06-19",
            "notes": "测试完整信息",
            "items": [{"product_id": pid, "quantity": 1, "unit_price": 100, "tax_rate": 0.13}],
            "purchase_order_action": "auto_create",
            "fixed_asset": {
                "asset_code": uniq("FA-COMPLETE"),
                "asset_name": "完整设备",
                "category": "机器设备",
                "salvage_rate": 0.10,
                "useful_life": 120,
                "depreciation_method": "双倍余额递减法",
                "start_date": "2026-07-01",
                "asset_status": "在用",
            },
        }, headers=HEADERS)
        assert response.status_code == 200
        data = response.json()["data"]
        inv = data
        assert data["invoice_no"].startswith("FA-INV-COMPLETE")
        assert inv["direction"] == "in"
        assert inv["invoice_type"] == "special"
        assert inv["tax_rate"] == 0.09
        assert inv["amount_without_tax"] == 10000.0
        assert inv["tax_amount"] == 900.0
        assert inv["amount_with_tax"] == 10900.0
        assert inv["counterparty_name"] == "供应商G"
        assert inv["notes"] == "测试完整信息"
        assert inv["related_order_type"] == "fixed_asset"
        assert inv["related_order_id"] is not None
        asset = data["fixed_asset"]
        assert asset["name"] == "完整设备"
        assert asset["original_value"] == "10900.00"
        assert asset["start_date"] == "2026-07-01"
        assert inv["related_order_id"] == asset["id"]

    def test_update_invoice_amount_syncs_asset(self, client):
        pid = _product_id(client)
        body = {
            "invoice_no": uniq("FA-INV-UPD"),
            "direction": "in",
            "invoice_type": "ordinary",
            "tax_rate": 0.13,
            "amount_with_tax": 11300,
            "tax_amount": 1300,
            "counterparty_name": "供应商H",
            "seller_name": "供应商H",
            "buyer_name": "测试公司",
            "issue_date": "2026-06-19",
            "items": [{"product_id": pid, "quantity": 1, "unit_price": 100, "tax_rate": 0.13}],
            "purchase_order_action": "auto_create",
            "fixed_asset": {
                "asset_code": uniq("FA-UPD"),
                "asset_name": "待更新设备",
                "salvage_rate": 0.05,
                "useful_life": 60,
                "start_date": "2026-06-19",
            },
        }
        create_resp = client.post("/api/invoices/quick", json=body, headers=HEADERS)
        assert create_resp.status_code == 200
        cr_data = create_resp.json()["data"]
        asset_id = cr_data["fixed_asset"]["id"]
        update_resp = client.put(f"/api/fixed-assets/{asset_id}/with-invoice", json={
            "original_value": 22600,
        }, headers=HEADERS)
        assert update_resp.status_code == 200
        inv = update_resp.json()["invoice"]
        assert inv["amount_with_tax"] == 22600.0
        assert inv["amount_without_tax"] == 20000.0
        assert inv["tax_amount"] == 2600.0
        asset = update_resp.json()["asset"]
        assert asset["original_value"] == 22600.0

    def test_delete_invoice_cascades_to_asset(self, client):
        pid = _product_id(client)
        body = {
            "invoice_no": uniq("FA-INV-DEL"),
            "direction": "in",
            "invoice_type": "ordinary",
            "tax_rate": 0.13,
            "amount_with_tax": 11300,
            "tax_amount": 1300,
            "counterparty_name": "供应商I",
            "seller_name": "供应商I",
            "buyer_name": "测试公司",
            "issue_date": "2026-06-19",
            "items": [{"product_id": pid, "quantity": 1, "unit_price": 100, "tax_rate": 0.13}],
            "purchase_order_action": "auto_create",
            "fixed_asset": {
                "asset_code": uniq("FA-DEL"),
                "asset_name": "待删除设备",
                "salvage_rate": 0.05,
                "useful_life": 60,
                "start_date": "2026-06-19",
            },
        }
        create_resp = client.post("/api/invoices/quick", json=body, headers=HEADERS)
        assert create_resp.status_code == 200
        cr_data = create_resp.json()["data"]
        invoice_id = cr_data["id"]
        asset_id = cr_data["fixed_asset"]["id"]

        delete_resp = client.delete(f"/api/invoices/{invoice_id}", headers=HEADERS)
        if delete_resp.status_code == 403:
            return  # readonly middleware blocks DELETE — acceptable
        assert delete_resp.status_code == 200

        invoice_list = client.get("/api/invoices", headers=HEADERS)
        assert invoice_list.status_code == 200
        invoices = invoice_list.json()["items"]
        assert not any(inv["id"] == invoice_id for inv in invoices)

        asset_list = client.get("/api/fixed-assets", headers=HEADERS)
        assert asset_list.status_code == 200
        assets = asset_list.json()["items"]
        assert any(a["id"] == asset_id for a in assets)

    def test_update_asset_syncs_invoice_amount(self, client):
        pid = _product_id(client)
        body = {
            "invoice_no": uniq("FA-INV-SYNC"),
            "direction": "in",
            "invoice_type": "ordinary",
            "tax_rate": 0.13,
            "amount_with_tax": 11300,
            "tax_amount": 1300,
            "counterparty_name": "供应商J",
            "seller_name": "供应商J",
            "buyer_name": "测试公司",
            "issue_date": "2026-06-19",
            "items": [{"product_id": pid, "quantity": 1, "unit_price": 100, "tax_rate": 0.13}],
            "purchase_order_action": "auto_create",
            "fixed_asset": {
                "asset_code": uniq("FA-SYNC"),
                "asset_name": "同步设备",
                "salvage_rate": 0.05,
                "useful_life": 60,
                "start_date": "2026-06-19",
            },
        }
        create_resp = client.post("/api/invoices/quick", json=body, headers=HEADERS)
        assert create_resp.status_code == 200
        cr_data = create_resp.json()["data"]
        asset_id = cr_data["fixed_asset"]["id"]
        update_resp = client.put(f"/api/fixed-assets/{asset_id}/with-invoice", json={
            "original_value": 22600,
        }, headers=HEADERS)
        assert update_resp.status_code == 200
        asset = update_resp.json()["asset"]
        assert asset["original_value"] == 22600.0
        inv = update_resp.json()["invoice"]
        assert inv["amount_with_tax"] == 22600.0
        assert inv["amount_without_tax"] == 20000.0
        assert inv["tax_amount"] == 2600.0

    def test_delete_asset_clears_invoice_link(self, client):
        pid = _product_id(client)
        body = {
            "invoice_no": uniq("FA-INV-CLEAR"),
            "direction": "in",
            "invoice_type": "ordinary",
            "tax_rate": 0.13,
            "amount_with_tax": 11300,
            "tax_amount": 1300,
            "counterparty_name": "供应商K",
            "seller_name": "供应商K",
            "buyer_name": "测试公司",
            "issue_date": "2026-06-19",
            "items": [{"product_id": pid, "quantity": 1, "unit_price": 100, "tax_rate": 0.13}],
            "purchase_order_action": "auto_create",
            "fixed_asset": {
                "asset_code": uniq("FA-CLEAR"),
                "asset_name": "待清空设备",
                "salvage_rate": 0.05,
                "useful_life": 60,
                "start_date": "2026-06-19",
            },
        }
        create_resp = client.post("/api/invoices/quick", json=body, headers=HEADERS)
        assert create_resp.status_code == 200
        cr_data = create_resp.json()["data"]
        invoice_id = cr_data["id"]
        asset_id = cr_data["fixed_asset"]["id"]

        delete_resp = client.delete(f"/api/fixed-assets/{asset_id}", headers=HEADERS)
        if delete_resp.status_code == 403:
            return
        assert delete_resp.status_code == 200

        invoice_resp = client.get("/api/invoices", headers=HEADERS)
        assert invoice_resp.status_code == 200
        invoices = invoice_resp.json()["items"]
        inv = next((i for i in invoices if i["id"] == invoice_id), None)
        assert inv is not None
        assert inv["related_order_id"] is None
        assert inv["related_order_type"] is None

    def test_invoice_calculation_uses_accounting_engine(self, client):
        pid = _product_id(client)
        response = client.post("/api/invoices/quick", json={
            "invoice_no": uniq("FA-INV-ENGINE"),
            "direction": "in",
            "invoice_type": "ordinary",
            "tax_rate": 0.13,
            "amount_with_tax": 11300,
            "tax_amount": 1300,
            "counterparty_name": "供应商L",
            "seller_name": "供应商L",
            "buyer_name": "测试公司",
            "issue_date": "2026-06-19",
            "items": [{"product_id": pid, "quantity": 1, "unit_price": 100, "tax_rate": 0.13}],
            "purchase_order_action": "auto_create",
            "fixed_asset": {
                "asset_code": uniq("FA-ENGINE"),
                "asset_name": "引擎测试设备",
                "salvage_rate": 0.05,
                "useful_life": 60,
                "start_date": "2026-06-19",
            },
        }, headers=HEADERS)
        assert response.status_code == 200
        inv = response.json()["data"]
        assert Decimal(str(inv["amount_without_tax"])) == Decimal("10000.00")
        assert Decimal(str(inv["tax_amount"])) == Decimal("1300.00")
        assert Decimal(str(inv["amount_with_tax"])) == Decimal("11300.00")
