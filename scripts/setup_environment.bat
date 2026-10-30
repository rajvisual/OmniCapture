@echo off
setlocal enabledelayedexpansion

echo ========================================================
echo        OmniCapture Environment Setup Script
echo ========================================================
echo.

cd /d "%~dp0\.."

:: 1. Verify Python availability
python --version >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo [ERROR] Python was not found in your PATH.
    echo Please install Python 3.10 or higher from https://python.org
    echo Ensure you check 'Add python.exe to PATH' during installation.
    pause
    exit /b 1
)

echo [1/3] Python detected:
python --version

:: 2. Create Virtual Environment if not present
if not exist ".venv" (
    echo [2/3] Creating virtual environment (.venv)...
    python -m venv .venv
    if %ERRORLEVEL% NEQ 0 (
        echo [ERROR] Failed to create virtual environment.
        pause
        exit /b 1
    )
    echo       Virtual environment created successfully.
) else (
    echo [2/3] Existing virtual environment found (.venv).
)

:: 3. Install optional dependencies
echo [3/3] Installing dependencies from requirements.txt...
call .venv\Scripts\activate.bat
python -m pip install --upgrade pip >nul 2>&1
pip install -r requirements.txt
if %ERRORLEVEL% NEQ 0 (
    echo [WARNING] Could not install all packages. Cloud features may require manual install.
) else (
    echo       Dependencies installed successfully.
)

echo.
echo ========================================================
echo Setup complete! Launch OmniCapture with:
echo    .\omni.bat
echo ========================================================
echo.
pause
