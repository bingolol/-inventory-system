@echo off
setlocal enabledelayedexpansion
chcp 65001 >nul 2>&1 || chcp 936 >nul
title 进销存管理系统 - 控制台
cls

echo ========================================
echo    进销存管理系统 - 一键启动
echo ========================================
echo.

:: ========================================
:: 环境检查
:: ========================================
python --version >nul 2>&1
if errorlevel 1 (
    echo [错误] 未找到 Python
    pause
    exit /b 1
)

node --version >nul 2>&1
if errorlevel 1 (
    echo [错误] 未找到 Node.js
    pause
    exit /b 1
)

echo [OK] Python 和 Node.js 已就绪
echo.

:: ========================================
:: 准备
:: ========================================
set "PROJECT=%~dp0inventory-system"
set "BACKEND_URL=http://localhost:8000"
set "FRONTEND_URL=http://localhost:5173"
set "SERVICE_LOG=%~dp0service.log"
set "PS_TAIL=%~dp0_tail.ps1"

:: 清理旧日志
if exist "%SERVICE_LOG%" del /f "%SERVICE_LOG%" >nul 2>&1

:: 清理残留端口
echo [清理] 检查端口占用...
for /f "tokens=5" %%p in ('netstat -ano ^| findstr ":8000 " ^| findstr "LISTENING"') do taskkill /PID %%p >nul 2>&1
for /f "tokens=5" %%p in ('netstat -ano ^| findstr ":5173 " ^| findstr "LISTENING"') do taskkill /PID %%p >nul 2>&1
timeout /t 1 /nobreak >nul
echo [OK] 端口已释放
echo.

:: ========================================
:: 启动服务窗口（自动最小化）
:: ========================================
echo [启动] 正在启动服务窗口（自动最小化）...
start /MIN "进销存服务" cmd /c "%~dp0Start-Services.bat"
echo [OK] 服务窗口已启动
echo.

:: ========================================
:: 等待后端就绪
:: ========================================
echo [等待] 等待后端服务...
set /a count=0
:wait_be
timeout /t 1 /nobreak >nul
curl -s -o nul %BACKEND_URL%/api/health >nul 2>&1
if not errorlevel 1 goto be_ok
set /a count+=1
if !count! geq 30 (
    echo [错误] 后端启动超时，请查看日志：%SERVICE_LOG%
    pause
    exit /b 1
)
echo    等待后端... (!count!/30)
goto wait_be
:be_ok
echo [OK] 后端已就绪
echo.

:: ========================================
:: 等待前端就绪
:: ========================================
echo [等待] 等待前端服务...
set /a count=0
:wait_fe
timeout /t 1 /nobreak >nul
curl -s -o nul %FRONTEND_URL% >nul 2>&1
if not errorlevel 1 goto fe_ok
set /a count+=1
if !count! geq 30 (
    echo [错误] 前端启动超时，请查看日志：%SERVICE_LOG%
    pause
    exit /b 1
)
echo    等待前端... (!count!/30)
goto wait_fe
:fe_ok
echo [OK] 前端已就绪
echo.

:: ========================================
:: 启动完成
:: ========================================
start "" "%FRONTEND_URL%"

echo ========================================
echo    所有服务已启动！
echo ========================================
echo  后端 API : %BACKEND_URL%
echo  前端界面 : %FRONTEND_URL%
echo  日志文件 : %SERVICE_LOG%
echo ========================================
echo.

:: ========================================
:: 实时日志流
:: ========================================
:show_logs
echo [日志] 实时输出中... 按任意键进入菜单
echo.

(
echo $ErrorActionPreference = 'SilentlyContinue'
echo $f = '%SERVICE_LOG:\=\\%'
echo $pos = 0
echo while ($true) {
echo     if (Test-Path $f) {
echo         $fs = [IO.File]::Open($f,'Open','Read','ReadWrite')
echo         if ($fs.Length -gt $pos) {
echo             $fs.Seek($pos,'Begin') ^| Out-Null
echo             $sr = New-Object IO.StreamReader($fs)
echo             while ($null -ne ($line = $sr.ReadLine())) {
echo                 if ($line -match '^\[BACKEND\]') { Write-Host $line -Fore Cyan }
echo                 elseif ($line -match '^\[FRONTEND\]') { Write-Host $line -Fore Yellow }
echo                 else { Write-Host $line }
echo             }
echo             $sr.Close(); $fs.Close()
echo             $pos = (Get-Item $f).Length
echo         } else { $fs.Close() }
echo     }
echo     Start-Sleep -Milliseconds 500
echo }
) > "%PS_TAIL%"

powershell -NoProfile -ExecutionPolicy Bypass -File "%PS_TAIL%"
pause >nul

:: ========================================
:: 控制菜单
:: ========================================
:menu
echo.
echo ========================================
echo    控制菜单
echo ========================================
echo  1 - 停止所有服务并退出
echo  2 - 重新打开浏览器
echo  3 - 返回日志查看
echo ========================================
set /p opt="请选择 [1/2/3]: "

if "!opt!"=="1" goto stop
if "!opt!"=="2" goto browser
if "!opt!"=="3" goto show_logs

echo [错误] 无效输入
goto menu

:: ========================================
:: 停止服务
:: ========================================
:stop
echo.
echo [停止] 正在停止所有服务...
taskkill /FI "WINDOWTITLE eq 进销存服务*" >nul 2>&1
for /f "tokens=5" %%p in ('netstat -ano ^| findstr ":8000 " ^| findstr "LISTENING"') do taskkill /PID %%p >nul 2>&1
for /f "tokens=5" %%p in ('netstat -ano ^| findstr ":5173 " ^| findstr "LISTENING"') do taskkill /PID %%p >nul 2>&1
timeout /t 1 /nobreak >nul
echo [完成] 所有服务已停止
if exist "%PS_TAIL%" del /f "%PS_TAIL%" >nul 2>&1
timeout /t 2 /nobreak >nul
exit /b 0

:: ========================================
:: 打开浏览器
:: ========================================
:browser
start "" "%FRONTEND_URL%"
echo [OK] 浏览器已打开
goto menu

:: ========================================
:: 退出但保留服务
:: ========================================
:exit_keep
echo.
echo [提示] 服务在后台继续运行
echo   访问前端: %FRONTEND_URL%
echo   查看日志: 运行此脚本并选择"3"
if exist "%PS_TAIL%" del /f "%PS_TAIL%" >nul 2>&1
timeout /t 2 /nobreak >nul
exit /b 0
