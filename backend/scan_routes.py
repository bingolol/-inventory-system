import sys, re, os

routers_dir = r'C:\Users\Administrator\Desktop\inventory-system\backend\routers'
for fname in sorted(os.listdir(routers_dir)):
    if not fname.endswith('.py') or fname.startswith('__'):
        continue
    fpath = os.path.join(routers_dir, fname)
    with open(fpath, encoding='utf-8') as f:
        content = f.read()
    routes = re.findall(r'@router\.(get|post|put|delete|patch)\(["\']([^"\']+)', content)
    if routes:
        print(f'\n=== {fname} ===')
        for method, path in routes:
            print(f'  {method.upper():6s} {path}')
