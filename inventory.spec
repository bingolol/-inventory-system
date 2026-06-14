# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller 打包配置 - 进销存管理系统

构建命令: pyinstaller inventory.spec
输出目录: dist/进销存管理系统/
"""

import os
import sys
from PyInstaller.utils.hooks import collect_all, collect_submodules

block_cipher = None

# 项目根目录
ROOT = os.path.abspath('.')

# 后端代码目录
BACKEND = os.path.join(ROOT, 'backend')

# 前端构建产物目录
FRONTEND_DIST = os.path.join(ROOT, 'frontend', 'dist')

# 收集所有隐式依赖
hidden_imports = [
    'uvicorn.logging',
    'uvicorn.loops',
    'uvicorn.loops.auto',
    'uvicorn.protocols',
    'uvicorn.protocols.http',
    'uvicorn.protocols.http.auto',
    'uvicorn.protocols.websockets',
    'uvicorn.protocols.websockets.auto',
    'uvicorn.lifespan',
    'uvicorn.lifespan.on',
    'sqlalchemy.dialects.sqlite',
    'sqlalchemy.sql.default_comparator',
    'pydantic',
    'pydantic.deprecated.decorator',
    'openpyxl',
    'multipart',
]

# 收集 backend 下所有子模块
for mod in collect_submodules('sqlalchemy'):
    if 'sqlite' in mod or 'dialects' in mod:
        hidden_imports.append(mod)

a = Analysis(
    [os.path.join(ROOT, 'launcher.py')],
    pathex=[BACKEND],
    binaries=[],
    datas=[
        # 后端 Python 代码（作为数据文件收集，运行时从 _MEIPASS 加载）
        (os.path.join(BACKEND, '*.py'), 'backend'),
        (os.path.join(BACKEND, 'routers'), 'backend/routers'),
        (os.path.join(BACKEND, 'schemas'), 'backend/schemas'),
        (os.path.join(BACKEND, 'crud'), 'backend/crud'),
        (os.path.join(BACKEND, 'domain'), 'backend/domain'),
        (os.path.join(BACKEND, 'commands'), 'backend/commands'),
        # 前端构建产物
        (FRONTEND_DIST, 'frontend/dist'),
    ],
    hiddenimports=hidden_imports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'tkinter', 'matplotlib', 'numpy', 'pandas', 'scipy',
        'PIL', 'pytest', 'IPython', 'jupyter',
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='进销存管理系统',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    icon=os.path.join(ROOT, 'app_icon.ico'),
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='进销存管理系统',
)