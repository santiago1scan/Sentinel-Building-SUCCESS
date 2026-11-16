@echo off
setlocal
cd /d "%~dp0"
title Sentinel Building Beta Tests

where py >nul 2>nul
if %errorlevel%==0 (
    py -3 -m unittest discover -s tests -p "test_*.py" -v
) else (
    python -m unittest discover -s tests -p "test_*.py" -v
)

echo.
pause
endlocal
