"""测试全局配置 — 仅添加 backend 到 sys.path"""
import sys
import os

BACKEND_DIR = os.path.join(os.path.dirname(__file__), "..", "backend")
BACKEND_DIR = os.path.abspath(BACKEND_DIR)
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)

import workspace
workspace.ensure_workspace()
