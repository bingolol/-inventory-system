import httpx
import json
from datetime import datetime

API = "http://127.0.0.1:8000/api"
headers = {"X-Account-ID": "1"}

print("=" * 60)
print("进销存系统 - 发票录入和税务报表测试")
print("=" * 60)

# 1. 创建测试发票
print("\n--- 1. 创建测试发票 ---")

invoices_to_create = [
    {
        "invoice_no": f"OUT-TEST-{datetime.now().strftime('%Y%m%d%H%M%S')}-1",
        "direction": "out",
        "invoice_type": "专票",
        "tax_rate": 0.13,
        "amount_without_tax": 10000,
        "tax_amount": 1300,
        "amount_with_tax": 11300,
        "counterparty_name": "测试客户A",
        "issue_date": "2026-04-15"
    },
    {
        "invoice_no": f"OUT-TEST-{datetime.now().strftime('%Y%m%d%H%M%S')}-2",
        "direction": "out",
        "invoice_type": "普票",
        "tax_rate": 0.03,
        "amount_without_tax": 5000,
        "tax_amount": 150,
        "amount_with_tax": 5150,
        "counterparty_name": "测试客户B",
        "issue_date": "2026-04-20"
    }
]

created_invoices = []
for inv_data in invoices_to_create:
    try:
        resp = httpx.post(f"{API}/invoices", json=inv_data, headers=headers)
        if resp.status_code == 200:
            print(f"  [OK] 发票 {inv_data['invoice_no']} 创建成功")
            created_invoices.append(resp.json())
        else:
            print(f"  [FAIL] 发票 {inv_data['invoice_no']} 创建失败: {resp.text}")
    except Exception as e:
        print(f"  [ERROR] 发票 {inv_data['invoice_no']} 创建异常: {e}")

# 2. 列出所有发票
print("\n--- 2. 列出所有发票 ---")
try:
    resp = httpx.get(f"{API}/invoices", headers=headers)
    if resp.status_code == 200:
        data = resp.json()
        print(f"  总发票数: {data['total']}")
        for inv in data['items'][-3:]:  # 显示最后3个
            print(f"    - {inv['invoice_no']}: {inv['direction']} {inv['invoice_type']} 价税合计 {inv['amount_with_tax']}")
    else:
        print(f"  [FAIL] 获取发票列表失败: {resp.text}")
except Exception as e:
    print(f"  [ERROR] 获取发票列表异常: {e}")

# 3. 测试报表接口
print("\n--- 3. 测试报表接口 ---")

report_endpoints = [
    ("/api/reports/overview", "总览报表"),
    ("/api/reports/purchase", "采购报表"),
    ("/api/reports/sale", "销售报表"),
    ("/api/reports/profit", "利润报表"),
    ("/api/reports/tax-report?year=2026&quarter=2", "增值税报表"),
]

for endpoint, name in report_endpoints:
    try:
        resp = httpx.get(f"http://127.0.0.1:8000{endpoint}", headers=headers)
        if resp.status_code == 200:
            print(f"  [OK] {name} 接口正常")
        else:
            print(f"  [FAIL] {name} 接口返回 {resp.status_code}: {resp.text[:100]}")
    except Exception as e:
        print(f"  [ERROR] {name} 接口异常: {e}")

# 4. 测试项目相关接口（如果存在）
print("\n--- 4. 测试项目接口 ---")

# 检查发票列表中是否有项目相关接口
print("  项目相关接口需要通过 MCP Server 或直接访问数据库测试")

# 5. 清理测试数据
print("\n--- 5. 清理测试数据 ---")
for inv in created_invoices:
    try:
        resp = httpx.delete(f"{API}/invoices/{inv['id']}", headers=headers)
        if resp.status_code == 200:
            print(f"  [OK] 发票 {inv['invoice_no']} 已删除")
        else:
            print(f"  [WARN] 发票 {inv['invoice_no']} 删除失败: {resp.text}")
    except Exception as e:
        print(f"  [ERROR] 删除发票异常: {e}")

print("\n" + "=" * 60)
print("测试完成")
print("=" * 60)
