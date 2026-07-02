@echo off
cd /d "%~dp0frontend"
npx electron .
taskkill /f /im python.exe >nul 2>&1
