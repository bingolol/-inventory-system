@echo off
chcp 65001 >nul 2>&1
title 进销存系统 - 仅更新
echo ========================================
echo    进销存系统 - 仅更新代码
echo ========================================
echo.

echo [1/2] 拉取最新代码...
git pull origin master
if errorlevel 1 (
    echo [ERROR] 拉取失败，请检查网络
    pause
    exit /b 1
)
echo [OK] 代码已更新
echo.

echo [2/2] 更新前端依赖...
cd frontend
call npm install --silent
cd ..
echo [OK] 前端依赖已更新
echo.

echo ========================================
echo    更新完成！
echo ========================================
echo    现在可以手动启动系统：
echo      双击 "启动进销存系统.bat"
echo.
echo    或运行：cd backend ^&^& python main.py
echo ========================================
pause
