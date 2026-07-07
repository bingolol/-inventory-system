@echo off
setlocal enabledelayedexpansion
chcp 65001 >nul 2>&1
title 进销存管理系统 - 一键安装

echo ========================================
echo    进销存管理系统 - 一键安装
echo ========================================
echo.
echo  此脚本将完成以下操作：
echo    1. 检查运行环境（Python / Node.js / Git）
echo    2. 克隆项目代码
echo    3. 安装后端 Python 依赖
echo    4. 安装前端依赖并构建
echo    5. 创建桌面快捷方式
echo.
echo  安装完成后，双击桌面图标即可使用。
echo ========================================
echo.

set "INSTALL_DIR=%USERPROFILE%\Desktop\inventory-system"
set "REPO_URL=https://github.com/bingolol/-inventory-system.git"

rem ── 如果已存在目录，询问是否覆盖 ──
if exist "%INSTALL_DIR%\.git" (
    echo [提示] 检测到已安装，建议使用「一键更新.bat」更新。
    echo        如需重新安装，请先删除 %INSTALL_DIR%
    echo.
    set /p confirm="是否覆盖重新安装？(y/N): "
    if /i not "!confirm!"=="y" (
        echo 已取消。
        pause
        exit /b 0
    )
    echo [1/7] 删除旧版本...
    rmdir /s /q "%INSTALL_DIR%" 2>nul
)

rem ── 1. 检查 Git ──
echo [1/7] 检查 Git...
git --version >nul 2>&1
if errorlevel 1 (
    echo [错误] 未找到 Git，请先安装 Git：https://git-scm.com/download/win
    pause
    exit /b 1
)
echo [OK] Git 已安装

rem ── 2. 检查 Python ──
echo [2/7] 检查 Python...
python --version >nul 2>&1
if errorlevel 1 (
    echo [错误] 未找到 Python，请先安装 Python 3.10+：https://www.python.org/downloads/
    echo        安装时请勾选 "Add Python to PATH"
    pause
    exit /b 1
)
echo [OK] Python 已安装

rem ── 3. 检查 Node.js ──
echo [3/7] 检查 Node.js...
node --version >nul 2>&1
if errorlevel 1 (
    echo [错误] 未找到 Node.js，请先安装 Node.js 18+：https://nodejs.org/
    pause
    exit /b 1
)
echo [OK] Node.js 已安装

rem ── 4. 克隆代码 ──
echo [4/7] 克隆项目代码...
cd /d "%USERPROFILE%\Desktop"
if exist "%INSTALL_DIR%" rmdir /s /q "%INSTALL_DIR%" 2>nul
git clone "%REPO_URL%" "%INSTALL_DIR%"
if errorlevel 1 (
    echo [错误] 克隆失败，请检查网络或仓库地址
    pause
    exit /b 1
)
echo [OK] 代码克隆完成

cd /d "%INSTALL_DIR%"

rem ── 5. 安装后端依赖 ──
echo [5/7] 安装后端 Python 依赖...
pip install -r backend\requirements.txt -q
if errorlevel 1 (
    echo [错误] 后端依赖安装失败
    pause
    exit /b 1
)
echo [OK] 后端依赖安装完成

rem ── 6. 安装前端依赖并构建 ──
echo [6/7] 安装前端依赖并构建...
cd frontend
call npm install --silent 2>nul
if errorlevel 1 (
    echo [警告] npm install 可能有问题，尝试继续...
)
call npm run build
if errorlevel 1 (
    echo [错误] 前端构建失败
    echo        请手动执行：cd frontend ^&^& npm install ^&^& npm run build
    pause
    exit /b 1
)
cd ..
echo [OK] 前端构建完成

rem ── 7. 创建桌面快捷方式 ──
echo [7/7] 创建桌面快捷方式...
python "创建桌面快捷方式.py"
if errorlevel 1 (
    echo [警告] 快捷方式创建失败，可手动运行 创建桌面快捷方式.py
)

echo.
echo ========================================
echo    安装完成！
echo ========================================
echo.
echo  桌面已创建「进销存管理系统」快捷方式
echo  双击即可启动系统
echo.
echo  如需更新代码，双击「一键更新.bat」
echo ========================================
echo.
pause
