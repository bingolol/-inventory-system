@echo off
chcp 65001 >nul 2>&1
title Inventory Services

set "LOG=%~dp0service.log"
set "BE_LOG=%~dp0service-backend.log"
set "FE_LOG=%~dp0service-frontend.log"
set "BACKEND_DIR=%~dp0backend"
set "FRONTEND_DIR=%~dp0frontend"

if exist "%BE_LOG%" del /f "%BE_LOG%" >nul 2>&1
if exist "%FE_LOG%" del /f "%FE_LOG%" >nul 2>&1

echo ======================================== > "%LOG%"
echo [%date% %time%] Services starting... >> "%LOG%"
echo ======================================== >> "%LOG%"

cd /d "%BACKEND_DIR%"
echo [%time%] [BACKEND] Starting python main.py... >> "%BE_LOG%"
start /B cmd /c python main.py >> "%BE_LOG%" 2>&1

cd /d "%FRONTEND_DIR%"
echo [%time%] [FRONTEND] Starting npm run dev... >> "%FE_LOG%"
npm run dev >> "%FE_LOG%" 2>&1