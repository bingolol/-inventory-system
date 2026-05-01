#!/usr/bin/env python3
"""全面暴力测试后端API"""

import httpx
import json

BASE_URL = "http://localhost:8000/api"
ACCOUNT_ID = 2  # 巧游电子科技有限公司

headers = {"X-Account-ID": str(ACCOUNT_ID)}

def test_api(name, method, path, data=None, params=None):
    """测试单个API"""
    url = f"{BASE_URL}{path}"
    try:
        with httpx.Client(timeout=30) as client:
            if method == "GET":
                resp = client.get(url, params=params, headers=headers)
            elif method == "POST":
                resp = client.post(url, json=data, headers=headers)
            elif method == "PUT":
                resp = client.put(url, json=data, headers=headers)
            elif method == "DELETE":
                resp = client.delete(url, headers=headers)
            else:
                return "INVALID METHOD", None

            status = "✅" if resp.status_code < 400 else "❌"
            detail = resp.json() if resp.status_code < 400 else resp.text[:100]
            return status, resp.status_code, detail
    except Exception as e:
        return "❌", None, str(e)[:100]

def main():
    print("=" * 80)
    print("全面暴力测试后端API - 巧游电子科技有限公司 (account_id=2)")
    print("=" * 80)

    # 测试所有主要API端点
    tests = [
        # 账套
        ("获取账套列表", "GET", "/accounts"),

        # 商品管理
        ("获取商品列表", "GET", "/products/", {"limit": 5}),
        ("获取商品分类", "GET", "/products/categories/list"),

        # 供应商管理
        ("获取供应商列表", "GET", "/suppliers/", {"limit": 5}),

        # 客户管理
        ("获取客户列表", "GET", "/customers/", {"limit": 5}),

        # 库存管理
        ("获取库存列表", "GET", "/inventory/", {"limit": 5}),
        ("获取库存预警", "GET", "/inventory/alerts"),

        # 销售管理
        ("获取销售列表", "GET", "/sales/", {"limit": 5}),

        # 采购管理
        ("获取采购列表", "GET", "/purchases/", {"limit": 5}),

        # 发票管理
        ("获取发票列表", "GET", "/invoices/", {"limit": 5}),

        # 项目管理
        ("获取项目列表", "GET", "/projects/", {"limit": 5}),

        # 费用管理
        ("获取费用列表", "GET", "/expenses/", {"limit": 5}),

        # 报表统计
        ("获取经营概览", "GET", "/reports/overview"),
        ("获取采购报表", "GET", "/reports/purchase"),
        ("获取销售报表", "GET", "/reports/sale"),
        ("获取利润报表", "GET", "/reports/profit"),
        ("获取趋势报表", "GET", "/reports/trend", {"days": 7}),

        # 税务报表
        ("获取增值税报表", "GET", "/tax-report/", {"year": 2025, "quarter": 1}),
        ("获取企业所得税报表", "GET", "/income-tax-report/", {"year": 2025}),

        # 个人流水账
        ("获取个人流水汇总", "GET", "/personal/summary"),
        ("获取个人流水列表", "GET", "/personal/", {"limit": 5}),

        # 操作日志
        ("获取操作日志", "GET", "/logs/", {"limit": 5}),

        # 健康检查
        ("健康检查", "GET", "/health"),
    ]

    print("\n【查询类API测试】")
    print("-" * 80)
    passed = 0
    failed = 0
    for name, method, path, *args in tests:
        params = args[0] if args and isinstance(args[0], dict) else None
        data = args[1] if len(args) > 1 else None

        status, code, detail = test_api(name, method, path, data, params)
        if status == "✅":
            passed += 1
        else:
            failed += 1
        print(f"{status} [{code}] {name} - {path}")

    print("-" * 80)
    print(f"查询类API: {passed} 通过, {failed} 失败")

    # 测试写入类API
    print("\n【写入类API测试】")
    print("-" * 80)

    # 测试创建费用
    status, code, detail = test_api(
        "创建费用",
        "POST",
        "/expenses/",
        {
            "category": "other",
            "amount": 200.0,
            "expense_date": "2026-04-23",
            "has_invoice": False,
            "payment_method": "company",
            "description": "暴力测试费用"
        }
    )
    print(f"{status} [{code}] 创建费用 - {detail[:80] if isinstance(detail, str) else detail}")

    # 测试创建项目
    status, code, detail = test_api(
        "创建项目",
        "POST",
        "/projects/",
        {
            "name": "暴力测试项目",
            "status": "ongoing"
        }
    )
    print(f"{status} [{code}] 创建项目 - {detail[:80] if isinstance(detail, str) else detail}")

    # 测试创建销售单（先获取商品）
    print("\n" + "-" * 80)
    print("【测试完成】")
    print("=" * 80)

if __name__ == "__main__":
    main()
