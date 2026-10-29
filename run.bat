@echo off
setlocal EnableExtensions
cd /d "%~dp0"
title AEL Competitor Price Dashboard

set "PORT=8501"
set "PY=.venv\Scripts\python.exe"

echo ============================================================
echo   AEL Trading - Khatunganj Competitor Price Dashboard
echo ============================================================
echo.

rem ---------------------------------------------------------------
rem 1. Stop any older dashboard still holding the port.  This is the
rem    usual reason a browser keeps showing the previous version.
rem ---------------------------------------------------------------
for /f "tokens=5" %%P in ('netstat -ano ^| findstr /R /C:":%PORT% .*LISTENING"') do (
    echo Stopping old dashboard process %%P on port %PORT% ...
    taskkill /PID %%P /F >nul 2>&1
)

rem ---------------------------------------------------------------
rem 2. Use a local environment so the same packages are used every run.
rem ---------------------------------------------------------------
if not exist "%PY%" (
    echo Creating the local Python environment...
    python -m venv .venv
    if errorlevel 1 goto :setup_failed
)

"%PY%" -c "import streamlit, pandas, plotly, openpyxl, requests, gspread, google.oauth2" >nul 2>&1
if errorlevel 1 (
    echo Installing dashboard requirements...
    "%PY%" -m pip install --upgrade pip
    "%PY%" -m pip install -r requirements.txt
    if errorlevel 1 goto :setup_failed
)

rem ---------------------------------------------------------------
rem 3. Open the browser after the server has had time to start.
rem ---------------------------------------------------------------
echo.
echo Starting dashboard on http://localhost:%PORT% ...
echo Keep this window open while you use the dashboard.
echo.
start "" powershell -NoProfile -WindowStyle Hidden -Command "Start-Sleep -Seconds 4; Start-Process 'http://localhost:%PORT%'"

"%PY%" -m streamlit run app.py --server.port %PORT% --server.headless true

goto :eof

:setup_failed
echo.
echo Setup failed. Install Python 3.10+ from python.org, then run this file again.
pause
