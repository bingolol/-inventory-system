import httpx
import json

API = "http://127.0.0.1:8000/api"
headers = {"X-Account-ID": "1"}

print("=" * 70)
print("进销存系统 - 综合功能测试")
print("=" * 70)

results = []

# 1. 健康检查
print("\n--- 1. 健康检查 ---")
try:
    resp = httpx.get(f"{API}/health", headers=headers)
    if resp.status_code == 200:
        print("  [PASS] 后端服务正常运行")
        results.append(("健康检查", True))
    else:
        print(f"  [FAIL] 健康检查失败: {resp.status_code}")
        results.append(("健康检查", False))
except Exception as e:
    print(f"  [ERROR] 健康检查异常: {e}")
    results.append(("健康检查", False))

# 2. 账本列表
print("\n--- 2. 账本列表 ---")
try:
    resp = httpx.get(f"{API}/accounts", headers=headers)
    if resp.status_code == 200:
        accounts = resp.json()
        print(f"  [PASS] 账本数量: {len(accounts)}")
        results.append(("账本列表", True))
    else:
        print(f"  [FAIL] 获取账本失败: {resp.status_code}")
        results.append(("账本列表", False))
except Exception as e:
    print(f"  [ERROR] 获取账本异常: {e}")
    results.append(("账本列表", False))

# 3. 商品管理
print("\n--- 3. 商品管理 ---")
try:
    resp = httpx.get(f"{API}/products/", headers=headers)
    if resp.status_code == 200:
        data = resp.json()
        print(f"  [PASS] 商品数量: {data.get('total', 0)}")
        results.append(("商品列表", True))
    else:
        print(f"  [FAIL] 获取商品失败: {resp.status_code}")
        results.append(("商品列表", False))
except Exception as e:
    print(f"  [ERROR] 获取商品异常: {e}")
    results.append(("商品列表", False))

# 4. 库存管理
print("\n--- 4. 库存管理 ---")
try:
    resp = httpx.get(f"{API}/inventory/", headers=headers)
    if resp.status_code == 200:
        data = resp.json()
        print(f"  [PASS] 库存商品数量: {data.get('total', 0)}")
        results.append(("库存列表", True))
    else:
        print(f"  [FAIL] 获取库存失败: {resp.status_code}")
        results.append(("库存列表", False))
except Exception as e:
    print(f"  [ERROR] 获取库存异常: {e}")
    results.append(("库存列表", False))

# 5. 库存预警
print("\n--- 5. 库存预警 ---")
try:
    resp = httpx.get(f"{API}/inventory/alerts", headers=headers)
    if resp.status_code == 200:
        alerts = resp.json()
        print(f"  [PASS] 预警数量: {len(alerts)}")
        results.append(("库存预警", True))
    else:
        print(f"  [FAIL] 获取预警失败: {resp.status_code}")
        results.append(("库存预警", False))
except Exception as e:
    print(f"  [ERROR] 获取预警异常: {e}")
    results.append(("库存预警", False))

# 6. 总览报表
print("\n--- 6. 总览报表 ---")
try:
    resp = httpx.get(f"{API}/reports/overview", headers=headers)
    if resp.status_code == 200:
        data = resp.json()
        print(f"  [PASS] 总览报表获取成功")
        results.append(("总览报表", True))
    else:
        print(f"  [FAIL] 获取总览报表失败: {resp.status_code}")
        results.append(("总览报表", False))
except Exception as e:
    print(f"  [ERROR] 获取总览报表异常: {e}")
    results.append(("总览报表", False))

# 7. 采购报表
print("\n--- 7. 采购报表 ---")
try:
    resp = httpx.get(f"{API}/reports/purchase", headers=headers)
    if resp.status_code == 200:
        print(f"  [PASS] 采购报表获取成功")
        results.append(("采购报表", True))
    else:
        print(f"  [FAIL] 获取采购报表失败: {resp.status_code}")
        results.append(("采购报表", False))
except Exception as e:
    print(f"  [ERROR] 获取采购报表异常: {e}")
    results.append(("采购报表", False))

# 8. 销售报表
print("\n--- 8. 销售报表 ---")
try:
    resp = httpx.get(f"{API}/reports/sale", headers=headers)
    if resp.status_code == 200:
        print(f"  [PASS] 销售报表获取成功")
        results.append(("销售报表", True))
    else:
        print(f"  [FAIL] 获取销售报表失败: {resp.status_code}")
        results.append(("销售报表", False))
except Exception as e:
    print(f"  [ERROR] 获取销售报表异常: {e}")
    results.append(("销售报表", False))

# 9. 利润报表
print("\n--- 9. 利润报表 ---")
try:
    resp = httpx.get(f"{API}/reports/profit", headers=headers)
    if resp.status_code == 200:
        print(f"  [PASS] 利润报表获取成功")
        results.append(("利润报表", True))
    else:
        print(f"  [FAIL] 获取利润报表失败: {resp.status_code}")
        results.append(("利润报表", False))
except Exception as e:
    print(f"  [ERROR] 获取利润报表异常: {e}")
    results.append(("利润报表", False))

# 10. 增值税报表
print("\n--- 10. 增值税报表 ---")
try:
    resp = httpx.get(f"{API}/reports/tax-report", params={"year": 2026, "quarter": 2}, headers=headers)
    if resp.status_code == 200:
        print(f"  [PASS] 增值税报表获取成功")
        results.append(("增值税报表", True))
    else:
        print(f"  [FAIL] 获取增值税报表失败: {resp.status_code}")
        results.append(("增值税报表", False))
except Exception as e:
    print(f"  [ERROR] 获取增值税报表异常: {e}")
    results.append(("增值税报表", False))

# 11. 供应商管理
print("\n--- 11. 供应商管理 ---")
try:
    resp = httpx.get(f"{API}/suppliers/", headers=headers)
    if resp.status_code == 200:
        data = resp.json()
        print(f"  [PASS] 供应商数量: {data.get('total', 0)}")
        results.append(("供应商列表", True))
    else:
        print(f"  [FAIL] 获取供应商失败: {resp.status_code}")
        results.append(("供应商列表", False))
except Exception as e:
    print(f"  [ERROR] 获取供应商异常: {e}")
    results.append(("供应商列表", False))

# 12. 客户管理
print("\n--- 12. 客户管理 ---")
try:
    resp = httpx.get(f"{API}/customers/", headers=headers)
    if resp.status_code == 200:
        data = resp.json()
        print(f"  [PASS] 客户数量: {data.get('total', 0)}")
        results.append(("客户列表", True))
    else:
        print(f"  [FAIL] 获取客户失败: {resp.status_code}")
        results.append(("客户列表", False))
except Exception as e:
    print(f"  [ERROR] 获取客户异常: {e}")
    results.append(("客户列表", False))

# 13. 费用管理
print("\n--- 13. 费用管理 ---")
try:
    resp = httpx.get(f"{API}/expenses/", headers=headers)
    if resp.status_code == 200:
        data = resp.json()
        print(f"  [PASS] 费用数量: {data.get('total', 0)}")
        results.append(("费用列表", True))
    else:
        print(f"  [FAIL] 获取费用失败: {resp.status_code}")
        results.append(("费用列表", False))
except Exception as e:
    print(f"  [ERROR] 获取费用异常: {e}")
    results.append(("费用列表", False))

# 14. 个人流水
print("\n--- 14. 个人流水 ---")
try:
    resp = httpx.get(f"{API}/personal/", headers={"X-Account-ID": "3"})  # 个人账本
    if resp.status_code == 200:
        data = resp.json()
        print(f"  [PASS] 个人流水数量: {data.get('total', 0)}")
        results.append(("个人流水", True))
    else:
        print(f"  [FAIL] 获取个人流水失败: {resp.status_code}")
        results.append(("个人流水", False))
except Exception as e:
    print(f"  [ERROR] 获取个人流水异常: {e}")
    results.append(("个人流水", False))

# 总结
print("\n" + "=" * 70)
print("测试总结")
print("=" * 70)
passed = sum(1 for _, p in results if p)
failed = sum(1 for _, p in results if not p)
print(f"通过: {passed}/{len(results)}")
print(f"失败: {failed}/{len(results)}")
print()
for name, passed in results:
    status = "PASS" if passed else "FAIL"
    print(f"  [{status}] {name}")

if failed > 0:
    print(f"\n注意: {failed} 个测试失败，可能需要进一步调查")
else:
    print("\n所有核心功能测试通过!")
