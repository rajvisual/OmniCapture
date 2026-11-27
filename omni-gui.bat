@echo off
setlocal
cd /d "%~dp0"
title OmniCapture Windows 11 GUI Dashboard
start "" pythonw.exe omni.py gui
if %errorlevel% neq 0 (
    python.exe omni.py gui
)
