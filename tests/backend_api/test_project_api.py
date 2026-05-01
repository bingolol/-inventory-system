import httpx
import json

API = "http://127.0.0.1:8000/api"
headers = {"X-Account-ID": "1"}

print("=== 测试项目归集逻辑 ===")

# Test /api/projects endpoint (correct path)
print("\n--- 1. 测试项目列表接口 ---")
try:
    resp = httpx.get(f"{API}/projects", headers=headers)
    print(f"Status: {resp.status_code}")
    print(f"Response: {resp.text}")
except Exception as e:
    print(f"Error: {e}")

# Test /api/reports/project endpoint
print("\n--- 2. 测试项目报表接口 ---")
try:
    resp = httpx.get(f"{API}/reports/project", headers=headers)
    print(f"Status: {resp.status_code}")
    print(f"Response: {resp.text}")
except Exception as e:
    print(f"Error: {e}")
