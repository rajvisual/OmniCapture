import os
import sys
import ctypes

MUTEX_NAME = "Global\\OmniCapture_Studio_SingleInstance_Mutex"
ERROR_ALREADY_EXISTS = 183

class SingleInstanceManager:
    """
    Enforces a single running instance of OmniCapture Studio on Windows.
    A second launch focuses the first window and exits gracefully.
    """

    def __init__(self, mutex_name: str = MUTEX_NAME):
        self.mutex_name = mutex_name
        self.hMutex = None

    def acquire(self) -> bool:
        """
        Attempt to acquire single-instance mutex.
        Returns True if primary instance; False if secondary instance.
        """
        if sys.platform != "win32":
            return True

        try:
            self.hMutex = ctypes.windll.kernel32.CreateMutexW(None, True, self.mutex_name)
            last_err = ctypes.windll.kernel32.GetLastError()
            if last_err == ERROR_ALREADY_EXISTS:
                self.focus_existing_window()
                return False
            return True
        except Exception:
            return True

    def focus_existing_window(self):
        """Find and bring the existing OmniCapture Studio window to foreground."""
        if sys.platform != "win32":
            return
        try:
            hwnd = ctypes.windll.user32.FindWindowW(None, "OmniCapture Studio")
            if hwnd:
                # SW_RESTORE = 9
                ctypes.windll.user32.ShowWindow(hwnd, 9)
                ctypes.windll.user32.SetForegroundWindow(hwnd)
        except Exception:
            pass

    def release(self):
        """Release the mutex handle on application exit."""
        if self.hMutex and sys.platform == "win32":
            try:
                ctypes.windll.kernel32.CloseHandle(self.hMutex)
            except Exception:
                pass
            self.hMutex = None
