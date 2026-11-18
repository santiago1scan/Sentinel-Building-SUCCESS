@echo off
setlocal
cd /d "%~dp0"
title Sentinel Building Beta

where py >nul 2>nul
if %errorlevel%==0 (
    py -3 start_beta.py
    goto :end
)

where python >nul 2>nul
if %errorlevel%==0 (
    python start_beta.py
    goto :end
)

echo.
echo ERROR: Python 3.11 or newer was not found.
echo Install Python or run: docker compose up --build
echo.
pause

:end
endlocal
