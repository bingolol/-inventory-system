# -*- mode: python ; coding: utf-8 -*-
"""安装向导打包配置 - 生成单文件安装器 exe

输出: dist/进销存管理系统安装包.exe
"""

import os

block_cipher = None

ROOT = os.path.abspath('.')
APP_FILES_DIR = os.path.join(ROOT, 'dist2', APP_NAME := '进销存管理系统')

a = Analysis(
    [os.path.join(ROOT, 'installer.py')],
    pathex=[],
    binaries=[],
    datas=[
        # 将应用文件嵌入安装器
        (os.path.join(APP_FILES_DIR, EXE_NAME := '进销存管理系统.exe'), 'app_files'),
        (os.path.join(APP_FILES_DIR, 'app_icon.ico'), 'app_files'),
        (os.path.join(APP_FILES_DIR, '_internal'), 'app_files/_internal'),
    ],
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'matplotlib', 'numpy', 'scipy', 'PIL', 'pytest',
        'IPython', 'jupyter', 'uvicorn', 'fastapi', 'sqlalchemy',
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
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='进销存管理系统安装包',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=os.path.join(ROOT, 'app_icon.ico'),
)