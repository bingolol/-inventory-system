"""模板 04：客户管理"""
import sys
sys.path.insert(0, r"C:\Users\Administrator\Desktop\-inventory-system\docs\操作模板")
from _client import post, get, extract_id


def create_customer(name, contact_person=None, phone=None, address=None, taxpayer_id=None):
    """创建客户。

    参数：
        name: 客户名称
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
    return post("/api/customers", body)


def list_customers():
    """查询全部客户。"""
    return get("/api/customers")


def get_customer(customer_id):
    """查询单个客户。"""
    return get(f"/api/customers/{customer_id}")


# === 端到端示例 ===
if __name__ == "__main__":
    from _client import set_account
    set_account(1)

    print("创建客户")
    cus = create_customer(name="客户乙", contact_person="李四", phone="13900000000")
    print(f"   {cus}")
    cus_id = extract_id(cus)
    print(f"   ID: {cus_id}")
