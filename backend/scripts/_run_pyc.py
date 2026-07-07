"""从 pycache 加载并执行 reset_and_run_all"""
import sys, os, importlib.machinery, importlib.util
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

PYCACHE = r"c:\Users\Administrator\Desktop\inventory-system\backend\scripts\qiaoyou_sim\__pycache__"

def load_pyc_module(name):
    """从 pyc 加载模块（无源码）"""
    pyc_path = os.path.join(PYCACHE, f"{name}.cpython-311.pyc")
    loader = importlib.machinery.SourcelessFileLoader(name, pyc_path)
    spec = importlib.util.spec_from_file_location(name, pyc_path, loader=loader)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    loader.exec_module(mod)
    return mod

if __name__ == "__main__":
    # 必须先加载包 __init__
    load_pyc_module("__init__")
    # 加载子模块
    print("=== 加载 reset_and_run_all ===")
    rra = load_pyc_module("reset_and_run_all")
    print(f"  模块属性: {[x for x in dir(rra) if not x.startswith('_')]}")
    if hasattr(rra, "main"):
        rra.main()
    elif hasattr(rra, "run_all"):
        rra.run_all()
    else:
        print("未找到 main 或 run_all")
