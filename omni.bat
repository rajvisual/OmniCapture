@echo off
setlocal
cd /d "%~dp0"

if exist ".venv\Scripts\python.exe" (
    ".venv\Scripts\python.exe" "%~dp0omni.py" %*
) else (
    python "%~dp0omni.py" %*
)

if %ERRORLEVEL% neq 0 (
    echo.
    echo [OmniCapture process ended with code %ERRORLEVEL%]
)
