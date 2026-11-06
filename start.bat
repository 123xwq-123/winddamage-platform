@echo off
REM Wind Damage Detection Platform - Windows launcher
REM Usage: double-click this file, or run "start.bat" in cmd

setlocal
set PYTHON=D:\ANACONDA\envs\winddamage\python.exe
set PORT=7860
cd /d "%~dp0"

echo ============================================================
echo   WindDamage Platform V1.0
echo   Wind turbine structural damage detection ^& assessment
echo ============================================================

if not exist "%PYTHON%" (
    echo [ERROR] Python env not found: %PYTHON%
    pause
    exit /b 1
)

if not exist "qwen3.5-4b\config.json" (
    echo [ERROR] Model files not found: qwen3.5-4b\config.json
    pause
    exit /b 1
)

echo   Python : %PYTHON%
echo   Model  : %~dp0qwen3.5-4b\
echo   URL    : http://localhost:%PORT%
echo   First load takes about 1 minute, please wait.
echo ============================================================

"%PYTHON%" app.py
pause
