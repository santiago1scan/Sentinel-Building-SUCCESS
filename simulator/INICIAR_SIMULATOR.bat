@echo off
setlocal
cd /d "%~dp0"
title Sentinel Building Simulator

where py >nul 2>nul
if %errorlevel%==0 (
    py -3 start_operational.py
    goto :end
)

where python >nul 2>nul
if %errorlevel%==0 (
    python start_operational.py
    goto :end
)

echo.
echo ERROR: Python 3.11 or newer was not found.
echo Install Python or run: docker compose up --build
echo.
pause

:end
endlocal
