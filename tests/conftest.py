"""测试全局配置 — 将 backend 与 tests 目录加入 sys.path"""
import sys
import os

BACKEND_DIR = os.path.join(os.path.dirname(__file__), "..", "backend")
BACKEND_DIR = os.path.abspath(BACKEND_DIR)
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)

# tests 目录本身需在 sys.path，使 tests/integration、tests/transaction 等
# 子目录中 `from helpers import ...` / `from factories import ...` 这类
# 裸导入可被解析（tests/helpers.py、tests/factories.py 位于此目录）。
TESTS_DIR = os.path.dirname(os.path.abspath(__file__))
if TESTS_DIR not in sys.path:
    sys.path.insert(0, TESTS_DIR)

import workspace
workspace.ensure_workspace()
