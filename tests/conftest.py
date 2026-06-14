"""测试全局配置 — 将 backend 目录加入 sys.path"""
import sys
import os

# 将 backend 目录插入 sys.path，使测试能直接 import backend 模块
BACKEND_DIR = os.path.join(os.path.dirname(__file__), "..", "backend")
BACKEND_DIR = os.path.abspath(BACKEND_DIR)
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)