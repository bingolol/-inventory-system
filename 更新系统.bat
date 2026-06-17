@echo off
chcp 65001 >nul 2>&1
title 进销存系统更新
echo ========================================
echo    进销存系统 - 安全更新
echo ========================================
echo.

echo [1/3] 拉取最新代码...
git pull origin master
if errorlevel 1 (
    echo [ERROR] 拉取失败，请检查网络
    pause
    exit /b 1
)
echo [OK] 代码已更新
echo.

echo [2/3] 更新前端依赖...
cd frontend
call npm install --silent
cd ..
echo [OK] 前端依赖已更新
echo.

echo [3/3] 启动系统（数据库自动迁移）...
echo.
echo    数据库将自动迁移，现有数据不会丢失
echo    按 Ctrl+C 可随时停止
echo.
cd backend
python main.py
