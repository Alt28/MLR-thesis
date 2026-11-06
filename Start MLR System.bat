@echo off
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
    echo Run setup.ps1 first to install the local Python environment.
    pause
    exit /b 1
)
echo Starting Transit Lab in your web browser...
".venv\Scripts\python.exe" main.py web
if errorlevel 1 pause
