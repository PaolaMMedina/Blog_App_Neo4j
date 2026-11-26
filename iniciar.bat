@echo off
cd /d "%~dp0"

if exist ".venv\Scripts\python.exe" (
    ".venv\Scripts\python.exe" blog.py
    if errorlevel 1 pause
    exit /b
)

where py >nul 2>nul
if %errorlevel% equ 0 (
    py -3 blog.py
) else (
    python blog.py
)

if errorlevel 1 pause
