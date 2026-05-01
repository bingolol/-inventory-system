import requests

API_BASE = 'http://127.0.0.1:8000/api'
headers = {'Content-Type': 'application/json', 'X-Account-ID': '1'}

def test():
    created_ids = []

    # 1. 创建 收入+工资 -> 应通过
    r1 = requests.post(f'{API_BASE}/personal/', json={
        'type': 'income', 'amount': 100, 'category': '工资', 'date': '2026-04-30'
    }, headers=headers)
    print('1. income+工资:', r1.status_code, 'PASS' if r1.status_code == 200 else 'FAIL')
    if r1.status_code == 200:
        created_ids.append(r1.json()['id'])

    # 2. 创建 支出+餐饮 -> 应通过
    r2 = requests.post(f'{API_BASE}/personal/', json={
        'type': 'expense', 'amount': 50, 'category': '餐饮', 'date': '2026-04-30'
    }, headers=headers)
    print('2. expense+餐饮:', r2.status_code, 'PASS' if r2.status_code == 200 else 'FAIL')
    if r2.status_code == 200:
        created_ids.append(r2.json()['id'])

    # 3. 创建 支出+工资 -> 应422（工资是收入分类）
    r3 = requests.post(f'{API_BASE}/personal/', json={
        'type': 'expense', 'amount': 50, 'category': '工资', 'date': '2026-04-30'
    }, headers=headers)
    print('3. expense+工资 (应422):', r3.status_code, 'PASS' if r3.status_code == 422 else 'FAIL')

    # 4. 创建 支出+吃饭 -> 应422（吃饭不在枚举中）
    r4 = requests.post(f'{API_BASE}/personal/', json={
        'type': 'expense', 'amount': 50, 'category': '吃饭', 'date': '2026-04-30'
    }, headers=headers)
    print('4. expense+吃饭 (应422):', r4.status_code, 'PASS' if r4.status_code == 422 else 'FAIL')

    # 5. 更新：支出记录改为收入，保留餐饮分类（餐饮不在收入枚举）-> 应422
    if r2.status_code == 200:
        tx_id = r2.json()['id']
        r5 = requests.put(f'{API_BASE}/personal/{tx_id}', json={
            'type': 'income', 'category': '餐饮'
        }, headers=headers)
        print('5. update->income+餐饮 (应422):', r5.status_code, 'PASS' if r5.status_code == 422 else 'FAIL')

    # 6. 更新：只改金额，不改分类 -> 应通过
    if r2.status_code == 200:
        tx_id = r2.json()['id']
        r6 = requests.put(f'{API_BASE}/personal/{tx_id}', json={
            'amount': 60
        }, headers=headers)
        print('6. update amount only (应200):', r6.status_code, 'PASS' if r6.status_code == 200 else 'FAIL')

    # 7. 清理：所有创建的合法记录
    for tid in created_ids:
        d = requests.delete(f'{API_BASE}/personal/{tid}', headers=headers)
        print(f'  删除 id={tid}:', d.status_code, 'ok' if d.status_code == 200 else 'FAIL')

    # 8. 验证无残留：检查最新记录
    r_check = requests.get(f'{API_BASE}/personal/', params={'page': 1, 'page_size': 5}, headers=headers)
    if r_check.status_code == 200:
        items = r_check.json().get('items', [])
        test_ids = set(created_ids)
        residual = [item for item in items if item['id'] in test_ids]
        print('8. 残留检查:', 'PASS (无残留)' if not residual else f'FAIL (残留 {len(residual)} 条)')
    else:
        print('8. 残留检查: SKIP')

    # 统计
    results = [
        r1.status_code == 200,
        r2.status_code == 200,
        r3.status_code == 422,
        r4.status_code == 422,
        (r5.status_code == 422 if r2.status_code == 200 else True),
        (r6.status_code == 200 if r2.status_code == 200 else True),
        not residual if r_check.status_code == 200 else True
    ]
    passed = sum(results)
    total = len(results)
    print(f'\n结果: {passed}/{total} 通过')

if __name__ == '__main__':
    test()