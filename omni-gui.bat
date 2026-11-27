@echo off
setlocal
cd /d "%~dp0"
title OmniCapture Windows 11 GUI Dashboard

if exist ".venv\Scripts\pythonw.exe" (
    start "" ".venv\Scripts\pythonw.exe" "%~dp0omni.py" gui
) else if exist ".venv\Scripts\python.exe" (
    start "" ".venv\Scripts\python.exe" "%~dp0omni.py" gui
) else (
    start "" pythonw.exe "%~dp0omni.py" gui 2>nul || python.exe "%~dp0omni.py" gui
)
