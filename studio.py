"""
OmniCapture Studio — Native Desktop Application Launcher
=======================================================
Direct zero-terminal entry point for the OmniCapture Studio desktop application.
Running this file directly (or double-clicking studio.pyw) opens the Windows 11
Studio GUI with zero command-line console or terminal windows.
"""

import os
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE_DIR))

from omni import load_config
from gui.dashboard import OmniCaptureApp


def run_studio():
    # Ensure Windows AppUserModelID is registered for taskbar grouping
    try:
        import ctypes
        from core.version import APP_USER_MODEL_ID
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(APP_USER_MODEL_ID)
    except Exception:
        pass

    cfg = load_config()
    app = OmniCaptureApp(cfg)
    app.mainloop()


if __name__ == "__main__":
    run_studio()
