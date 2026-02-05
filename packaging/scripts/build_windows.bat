@echo off
REM Windows build script for Docmaker desktop application
REM Run from the repository root: packaging\scripts\build_windows.bat

setlocal

REM Get the script directory and project root
set SCRIPT_DIR=%~dp0
set PROJECT_ROOT=%SCRIPT_DIR%..\..

REM Change to project root
cd /d "%PROJECT_ROOT%"

echo Building Docmaker for Windows
echo ==============================

REM Check if Python is available
python --version >nul 2>&1
if errorlevel 1 (
    echo Error: Python not found in PATH
    exit /b 1
)

REM Run the build script
python packaging\scripts\build.py %*

endlocal
