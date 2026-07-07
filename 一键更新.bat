@echo off
setlocal enabledelayedexpansion
chcp 65001 >nul 2>&1
title 进销存管理系统 - 一键更新

echo ========================================
echo    进销存管理系统 - 一键更新
echo ========================================
echo.

set "INSTALL_DIR=%~dp0"
cd /d "%INSTALL_DIR%"

rem ── 0. 停止正在运行的系统 ──
echo [0/5] 停止正在运行的系统...
rem 杀掉占用 8000 端口的进程
for /f "tokens=5" %%p in ('netstat -ano ^| findstr ":8000 " ^| findstr "LISTENING" 2^>nul') do (
    taskkill /F /T /PID %%p >nul 2>&1
)
rem 杀掉 pythonw 启动器进程（通过窗口标题）
taskkill /FI "WINDOWTITLE eq 进销存管理系统*" >nul 2>&1
timeout /t 2 /nobreak >nul
echo [OK] 已停止

rem ── 1. 拉取最新代码 ──
echo [1/5] 拉取最新代码...
git pull origin master
if errorlevel 1 (
    echo [错误] 拉取失败，请检查网络或手动执行 git pull
    echo        如果有本地修改冲突，可执行: git stash ^&^& git pull
    pause
    exit /b 1
)
echo [OK] 代码已更新

rem ── 2. 更新后端依赖 ──
echo [2/5] 更新后端 Python 依赖...
pip install -r backend\requirements.txt -q
if errorlevel 1 (
    echo [警告] 后端依赖安装可能有警告，尝试继续...
)
echo [OK] 后端依赖已更新

rem ── 3. 更新前端依赖 ──
echo [3/5] 更新前端依赖...
cd frontend
call npm install --silent 2>nul
echo [OK] 前端依赖已更新

rem ── 4. 重新构建前端 ──
echo [4/5] 重新构建前端...
call npm run build
if errorlevel 1 (
    echo [错误] 前端构建失败
    pause
    exit /b 1
)
cd ..
echo [OK] 前端构建完成

rem ── 5. 刷新桌面快捷方式 ──
echo [5/5] 刷新桌面快捷方式...
if exist "创建桌面快捷方式.py" (
    python "创建桌面快捷方式.py" >nul 2>&1
    echo [OK] 快捷方式已刷新
) else (
    echo [跳过] 未找到快捷方式创建脚本
)

echo.
echo ========================================
echo    更新完成！
echo ========================================
echo.
echo  现在可以双击桌面「进销存管理系统」图标启动
echo  或双击 run.pyw 启动
echo ========================================
echo.
pause
