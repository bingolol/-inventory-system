@echo off
setlocal enabledelayedexpansion
chcp 65001 >nul 2>&1
title Inventory Services

set "LOG=%~dp0service.log"
set "BE_LOG=%~dp0service-backend.log"
set "FE_LOG=%~dp0service-frontend.log"
set "PID_FILE=%~dp0.pids"
set "BACKEND_DIR=%~dp0backend"
set "FRONTEND_DIR=%~dp0frontend"

echo DEBUG: LOG=%LOG%
echo DEBUG: BE_LOG=%BE_LOG%
echo DEBUG: FE_LOG=%FE_LOG%
echo DEBUG: PID_FILE=%PID_FILE%
echo DEBUG: BACKEND_DIR=%BACKEND_DIR%
echo DEBUG: FRONTEND_DIR=%FRONTEND_DIR%

if exist "%BE_LOG%" del /f "%BE_LOG%" >nul 2>&1
if exist "%FE_LOG%" del /f "%FE_LOG%" >nul 2>&1
if exist "%PID_FILE%" del /f "%PID_FILE%" >nul 2>&1

echo ======================================== > "%LOG%"
echo [%date% %time%] Services starting... >> "%LOG%"
echo ======================================== >> "%LOG%"

rem --- Backend ---
set "TMP_PS=%TEMP%\inv_be_%RANDOM%.ps1"
(
echo $p = Start-Process -FilePath "cmd" -ArgumentList "/c cd /d ""%BACKEND_DIR%"" ^&^& set DEV=1 ^&^& python main.py ^>^> ""%BE_LOG%"" 2^>^&1" -WindowStyle Minimized -PassThru
echo $p.Id
) > "%TMP_PS%"
echo DEBUG: Backend PS1 = %TMP_PS%
type "%TMP_PS%"

for /f "usebackq tokens=*" %%p in (`powershell -NoProfile -ExecutionPolicy Bypass -File "%TMP_PS%" 2^>^&1`) do set "BE_PID=%%p"
echo DEBUG: BE_PID=[!BE_PID!]
echo [%time%] [BACKEND] PID=!BE_PID! >> "%LOG%"

rem --- Frontend ---
set "TMP_PS=%TEMP%\inv_fe_%RANDOM%.ps1"
(
echo $p = Start-Process -FilePath "cmd" -ArgumentList "/c cd /d ""%FRONTEND_DIR%"" ^&^& npm run dev ^>^> ""%FE_LOG%"" 2^>^&1" -WindowStyle Minimized -PassThru
echo $p.Id
) > "%TMP_PS%"
echo DEBUG: Frontend PS1 = %TMP_PS%
type "%TMP_PS%"

for /f "usebackq tokens=*" %%p in (`powershell -NoProfile -ExecutionPolicy Bypass -File "%TMP_PS%" 2^>^&1`) do set "FE_PID=%%p"
echo DEBUG: FE_PID=[!FE_PID!]
echo [%time%] [FRONTEND] PID=!FE_PID! >> "%LOG%"

rem Save PIDs
echo !BE_PID! > "%PID_FILE%"
echo !FE_PID! >> "%PID_FILE%"
echo [%time%] PIDs saved to %PID_FILE% >> "%LOG%"
echo DEBUG: PID file content:
type "%PID_FILE%"

echo DEBUG: Script done. Check temp PS1 files:
echo DEBUG:   backend ps1 exists? 
if exist "%TEMP%\inv_be_*.ps1" (dir "%TEMP%\inv_be_*.ps1")
echo DEBUG:   frontend ps1 exists?
if exist "%TEMP%\inv_fe_*.ps1" (dir "%TEMP%\inv_fe_*.ps1")
