@echo off
setlocal enabledelayedexpansion
chcp 65001 >nul 2>&1
title Inventory System - Console
cls

echo ========================================
echo    Inventory System - Quick Start
echo ========================================
echo.

python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python not found
    pause
    exit /b 1
)

node --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Node.js not found
    pause
    exit /b 1
)

echo [OK] Python and Node.js ready
echo.

set "BACKEND_URL=http://localhost:8000"
set "FRONTEND_URL=http://localhost:5173"
set "SERVICE_LOG=%~dp0service.log"
set "PS_TAIL=%~dp0_tail.ps1"
set "PID_FILE=%~dp0.pids"

if exist "%SERVICE_LOG%" del /f "%SERVICE_LOG%" >nul 2>&1

if exist "%PID_FILE%" (
    echo [INFO] Cleaning up previous session...
    for /f "usebackq tokens=*" %%p in ("%PID_FILE%") do taskkill /F /T /PID %%p >nul 2>&1
    del /f "%PID_FILE%" >nul 2>&1
    timeout /t 2 /nobreak >nul
)
echo [INFO] Checking ports...
for /f "tokens=5" %%p in ('netstat -ano ^| findstr ":8000 " ^| findstr "LISTENING"') do taskkill /F /T /PID %%p >nul 2>&1
for /f "tokens=5" %%p in ('netstat -ano ^| findstr ":5173 " ^| findstr "LISTENING"') do taskkill /F /T /PID %%p >nul 2>&1
timeout /t 1 /nobreak >nul
echo [OK] Ports cleared
echo.

echo [INFO] Starting services (minimized)...
start /MIN "InventoryServices" cmd /c "%~dp0Start-Services.bat"
echo [OK] Services started
echo.

echo [INFO] Waiting for backend...
set /a count=0
:wait_be
timeout /t 1 /nobreak >nul
curl -s -o nul %BACKEND_URL%/api/health >nul 2>&1
if not errorlevel 1 goto be_ok
set /a count+=1
if !count! geq 30 (
    echo [ERROR] Backend timeout. Check: %SERVICE_LOG%
    pause
    exit /b 1
)
echo    Waiting... (!count!/30)
goto wait_be
:be_ok
echo [OK] Backend ready
echo.

echo [INFO] Waiting for frontend...
set /a count=0
:wait_fe
timeout /t 1 /nobreak >nul
curl -s -o nul %FRONTEND_URL% >nul 2>&1
if not errorlevel 1 goto fe_ok
set /a count+=1
if !count! geq 30 (
    echo [ERROR] Frontend timeout. Check: %SERVICE_LOG%
    pause
    exit /b 1
)
echo    Waiting... (!count!/30)
goto wait_fe
:fe_ok
echo [OK] Frontend ready
echo.

start "" "%FRONTEND_URL%"

echo ========================================
echo    All services started!
echo ========================================
echo  Backend  : %BACKEND_URL%
echo  Frontend : %FRONTEND_URL%
echo  Logs     : %SERVICE_LOG%
echo ========================================
echo.

:show_logs
echo [LOG] Streaming... Press any key for menu
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

:menu
echo.
echo ========================================
echo    Control Menu
echo ========================================
echo  1 - Stop all services and exit
echo  2 - Reopen browser
echo  3 - Back to logs
echo ========================================
set /p opt="Select [1/2/3]: "

if "!opt!"=="1" goto stop
if "!opt!"=="2" goto browser
if "!opt!"=="3" goto show_logs

echo [ERROR] Invalid input
goto menu

:stop
echo.
echo [STOP] Stopping all services...
if exist "%PID_FILE%" (
    for /f "usebackq tokens=*" %%p in ("%PID_FILE%") do taskkill /F /T /PID %%p >nul 2>&1
    del /f "%PID_FILE%" >nul 2>&1
)
taskkill /FI "WINDOWTITLE eq InventoryServices*" >nul 2>&1
for /f "tokens=5" %%p in ('netstat -ano ^| findstr ":8000 " ^| findstr "LISTENING"') do taskkill /F /T /PID %%p >nul 2>&1
for /f "tokens=5" %%p in ('netstat -ano ^| findstr ":5173 " ^| findstr "LISTENING"') do taskkill /F /T /PID %%p >nul 2>&1
timeout /t 1 /nobreak >nul
echo [DONE] All services stopped
if exist "%PS_TAIL%" del /f "%PS_TAIL%" >nul 2>&1
if exist "%PID_FILE%" del /f "%PID_FILE%" >nul 2>&1
timeout /t 2 /nobreak >nul
exit /b 0

:browser
start "" "%FRONTEND_URL%"
echo [OK] Browser opened
goto menu