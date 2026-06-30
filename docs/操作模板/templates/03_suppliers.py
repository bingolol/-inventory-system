"""模板 03：供应商管理"""
import sys
sys.path.insert(0, r"C:\Users\Administrator\Desktop\-inventory-system\docs\操作模板")
from _client import post, get, extract_id


def create_supplier(name, contact_person=None, phone=None, address=None, taxpayer_id=None):
    """创建供应商。

    参数：
        name: 供应商名称
        contact_person: 联系人（可选）
        phone: 电话（可选）
        address: 地址（可选）
        taxpayer_id: 纳税人识别号（可选，开发票时可用）
    """
    body = {"name": name}
    if contact_person: body["contact_person"] = contact_person
    if phone: body["phone"] = phone
    if address: body["address"] = address
    if taxpayer_id: body["taxpayer_id"] = taxpayer_id
    return post("/api/suppliers", body)


def list_suppliers():
    """查询全部供应商。"""
    return get("/api/suppliers")


def get_supplier(supplier_id):
    """查询单个供应商。"""
    return get(f"/api/suppliers/{supplier_id}")


# === 端到端示例 ===
if __name__ == "__main__":
    from _client import set_account
    set_account(1)

    print("创建供应商")
    sup = create_supplier(name="供应商甲", contact_person="张三", phone="13800000000")
    print(f"   {sup}")
    sup_id = extract_id(sup)
    print(f"   ID: {sup_id}")

    print("\n查询全部")
    print(f"   {list_suppliers()}")
