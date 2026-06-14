"""进销存管理系统 - 一键构建脚本

功能：
1. 构建前端 (npm run build)
2. 创建数据库模板
3. 运行 PyInstaller 打包
4. 创建安装脚本（含桌面快捷方式）

使用方法：
    python build.py
"""

import os
import sys
import subprocess
import shutil

ROOT = os.path.dirname(os.path.abspath(__file__))
FRONTEND = os.path.join(ROOT, 'frontend')
BACKEND = os.path.join(ROOT, 'backend')
DIST = os.path.join(ROOT, 'dist', '进销存管理系统')


def run(cmd, cwd=None, check=True):
    """执行命令并实时输出"""
    print(f"\n>>> {cmd}")
    result = subprocess.run(
        cmd, shell=True, cwd=cwd, check=check,
        stdout=sys.stdout, stderr=sys.stderr
    )
    return result


def build_frontend():
    """构建前端"""
    print("\n" + "=" * 50)
    print("步骤 1/4: 构建前端...")
    print("=" * 50)

    # 检查 node_modules
    if not os.path.exists(os.path.join(FRONTEND, 'node_modules')):
        print("安装前端依赖...")
        run("npm install", cwd=FRONTEND)

    # 构建
    run("npm run build", cwd=FRONTEND)

    dist_dir = os.path.join(FRONTEND, 'dist')
    if not os.path.exists(dist_dir):
        print(f"[错误] 前端构建失败，{dist_dir} 不存在")
        sys.exit(1)
    print("[OK] 前端构建完成")


def create_db_template():
    """创建空数据库模板（首次安装时使用）"""
    print("\n" + "=" * 50)
    print("步骤 2/4: 创建数据库模板...")
    print("=" * 50)

    template_path = os.path.join(BACKEND, 'inventory.db.template')
    # 用 Python 初始化一个空数据库
    script = (
        "import sys; sys.path.insert(0, r'%s'); "
        "from database import init_db; init_db(); "
        "print('数据库模板创建成功')"
    ) % BACKEND

    # 如果已有 inventory.db，直接复制为模板；否则创建新的
    existing_db = os.path.join(BACKEND, 'inventory.db')
    if os.path.exists(existing_db):
        shutil.copy2(existing_db, template_path)
        print(f"[OK] 从现有数据库复制模板: {template_path}")
    else:
        try:
            run(f'python -c "{script}"', cwd=BACKEND)
            if os.path.exists(existing_db):
                shutil.copy2(existing_db, template_path)
                print(f"[OK] 数据库模板已创建: {template_path}")
        except Exception as e:
            print(f"[警告] 创建数据库模板失败（不影响打包）: {e}")
            print("  首次运行时将通过 init_db() 自动创建")


def run_pyinstaller():
    """运行 PyInstaller 打包"""
    print("\n" + "=" * 50)
    print("步骤 3/4: PyInstaller 打包...")
    print("=" * 50)

    # 检查 PyInstaller
    try:
        import PyInstaller
        print(f"PyInstaller 版本: {PyInstaller.__version__}")
    except ImportError:
        print("安装 PyInstaller...")
        run("pip install pyinstaller")

    # 清理旧构建
    for d in ['build', 'dist']:
        dpath = os.path.join(ROOT, d)
        if os.path.exists(dpath):
            shutil.rmtree(dpath, ignore_errors=True)
            print(f"已清理: {dpath}")

    # 运行打包
    run("pyinstaller inventory.spec", cwd=ROOT)

    # 检查输出
    exe_path = os.path.join(DIST, '进销存管理系统.exe')
    if not os.path.exists(exe_path):
        print(f"[错误] 打包失败，exe 不存在: {exe_path}")
        sys.exit(1)
    print(f"[OK] 打包完成: {exe_path}")


def create_installer():
    """创建安装脚本和桌面快捷方式"""
    print("\n" + "=" * 50)
    print("步骤 4/4: 创建安装脚本...")
    print("=" * 50)

    # 创建安装脚本
    install_bat = os.path.join(DIST, '安装.bat')
    install_content = r'''@echo off
chcp 65001 >nul 2>&1
title 进销存管理系统 - 安装

echo ========================================
echo    进销存管理系统 - 安装程序
echo ========================================
echo.

:: 获取当前目录
set "APP_DIR=%~dp0"
set "EXE_PATH=%APP_DIR%进销存管理系统.exe"

:: 检查 exe 是否存在
if not exist "%EXE_PATH%" (
    echo [错误] 找不到 进销存管理系统.exe
    pause
    exit /b 1
)

:: 创建桌面快捷方式
echo [1/2] 创建桌面快捷方式...
powershell -NoProfile -ExecutionPolicy Bypass -File "%APP_DIR%create_shortcut.ps1"

if errorlevel 1 (
    echo [警告] 创建桌面快捷方式失败，请手动创建
) else (
    echo [OK] 桌面快捷方式已创建
)

echo.
echo [2/2] 安装完成！
echo.
echo  桌面快捷方式: 进销存管理系统
echo  数据存储位置: %APPDATA%\进销存管理系统
echo.
echo  双击桌面图标即可启动系统
echo ========================================
pause
'''
    with open(install_bat, 'w', encoding='utf-8') as f:
        f.write(install_content)
    print(f"[OK] 安装脚本已创建: {install_bat}")

    # 创建 PowerShell 快捷方式脚本
    ps1_path = os.path.join(DIST, 'create_shortcut.ps1')
    ps1_content = '''$ws = New-Object -ComObject WScript.Shell
$desktop = [Environment]::GetFolderPath('Desktop')
$s = $ws.CreateShortcut("$desktop\\进销存管理系统.lnk")
$s.TargetPath = Join-Path $PSScriptRoot '进销存管理系统.exe'
$s.WorkingDirectory = $PSScriptRoot
$s.IconLocation = Join-Path $PSScriptRoot 'app_icon.ico'
$s.Save()
'''
    # 使用 UTF-8 BOM 编码，避免 PowerShell 中文乱码
    with open(ps1_path, 'w', encoding='utf-8-sig') as f:
        f.write(ps1_content)
    print(f"[OK] 快捷方式脚本已创建: {ps1_path}")

    # 创建卸载脚本
    uninstall_bat = os.path.join(DIST, '卸载.bat')
    uninstall_content = r'''@echo off
chcp 65001 >nul 2>&1
title 进销存管理系统 - 卸载

echo ========================================
echo    进销存管理系统 - 卸载
echo ========================================
echo.
echo [警告] 此操作将：
echo   1. 删除桌面快捷方式
echo   2. 删除程序文件
echo.
echo [注意] 您的业务数据保存在:
echo   %APPDATA%\进销存管理系统
echo   不会被删除，可手动清理
echo.
set /p confirm="确认卸载？(y/N): "
if /i not "%confirm%"=="y" exit /b 0

:: 删除桌面快捷方式
del "%USERPROFILE%\Desktop\进销存管理系统.lnk" 2>nul

echo [OK] 卸载完成
echo 如需删除数据，请手动删除: %APPDATA%\进销存管理系统
pause
'''
    with open(uninstall_bat, 'w', encoding='utf-8') as f:
        f.write(uninstall_content)
    print(f"[OK] 卸载脚本已创建: {uninstall_bat}")

    # 复制图标到 dist 目录（用于手动创建快捷方式）
    icon_src = os.path.join(ROOT, 'app_icon.ico')
    if os.path.exists(icon_src):
        shutil.copy2(icon_src, os.path.join(DIST, 'app_icon.ico'))
        print(f"[OK] 图标已复制到发布目录")

    print(f"\n发布目录: {DIST}")
    print("将此目录打包成 zip 即可分发给用户")


def build_installer_exe():
    """构建一键安装器 exe（内嵌应用文件）"""
    print("\n" + "=" * 50)
    print("步骤 5/5: 构建一键安装器...")
    print("=" * 50)

    # 检查 dist2 目录是否存在（应用文件）
    app_dist = os.path.join(ROOT, 'dist2', '进销存管理系统')
    if not os.path.exists(app_dist):
        # 如果 dist2 不存在，把 dist/进销存管理系统 复制过来
        src = DIST
        if os.path.exists(src):
            os.makedirs(os.path.join(ROOT, 'dist2'), exist_ok=True)
            dst = app_dist
            if os.path.exists(dst):
                shutil.rmtree(dst, ignore_errors=True)
            shutil.copytree(src, dst)
            print(f"[OK] 已复制应用文件到 {dst}")

    run("pyinstaller --noconfirm installer.spec", cwd=ROOT)

    installer_exe = os.path.join(ROOT, 'dist', '进销存管理系统安装包.exe')
    if os.path.exists(installer_exe):
        size_mb = os.path.getsize(installer_exe) / (1024 * 1024)
        print(f"[OK] 安装器构建完成: {installer_exe} ({size_mb:.1f}MB)")
    else:
        print("[错误] 安装器构建失败")
        sys.exit(1)


def main():
    print("=" * 50)
    print("  进销存管理系统 - 一键构建")
    print("=" * 50)

    # 检查前端 dist 是否已存在
    frontend_dist = os.path.join(FRONTEND, 'dist')
    if not os.path.exists(frontend_dist):
        build_frontend()
    else:
        print("[跳过] 前端 dist 已存在，如需重新构建请先删除 frontend/dist")

    create_db_template()
    run_pyinstaller()
    create_installer()
    build_installer_exe()

    print("\n" + "=" * 50)
    print("  构建全部完成！")
    print("=" * 50)
    print(f"  安装包: dist/进销存管理系统安装包.exe")
    print(f"  应用目录: {DIST}")
    print("=" * 50)


if __name__ == '__main__':
    main()