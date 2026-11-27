import sys
import ctypes
from ctypes import wintypes
from typing import Optional

class TaskbarManager:
    """
    Windows 7+ Taskbar Integration via ITaskbarList3 COM Interface.
    Provides overlay badges during recording and green/yellow/red progress bars
    during uploads and background tasks.
    """

    TBPF_NOPROGRESS = 0
    TBPF_INDETERMINATE = 1
    TBPF_NORMAL = 2      # Green
    TBPF_ERROR = 4       # Red
    TBPF_PAUSED = 8      # Yellow

    _app_user_model_id_set = False

    @classmethod
    def set_app_user_model_id(cls, app_id: str = "OmniCapture.Studio.Desktop.1.3"):
        """Register explicit AppUserModelID for taskbar pinning and grouping."""
        if sys.platform == "win32" and not cls._app_user_model_id_set:
            try:
                ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(app_id)
                cls._app_user_model_id_set = True
            except Exception:
                pass

    def __init__(self, hwnd: Optional[int] = None):
        self.hwnd = hwnd
        self.pTaskbar = None
        self._init_com()

    def _init_com(self):
        if sys.platform != "win32":
            return
        try:
            ole32 = ctypes.windll.ole32
            ole32.CoInitialize(None)

            class GUID(ctypes.Structure):
                _fields_ = [
                    ('Data1', wintypes.DWORD),
                    ('Data2', wintypes.WORD),
                    ('Data3', wintypes.WORD),
                    ('Data4', ctypes.c_byte * 8)
                ]

            clsid = GUID()
            iid = GUID()
            ole32.CLSIDFromString(ctypes.c_wchar_p('{56FDF344-FD6D-11d0-958A-006097C9A090}'), ctypes.byref(clsid))
            ole32.CLSIDFromString(ctypes.c_wchar_p('{ea1afb91-9e28-4b86-90e9-9e9f8a5eefaf}'), ctypes.byref(iid))

            pTaskbar = ctypes.c_void_p()
            hr = ole32.CoCreateInstance(ctypes.byref(clsid), None, 1, ctypes.byref(iid), ctypes.byref(pTaskbar))
            if hr == 0 and pTaskbar.value:
                self.pTaskbar = pTaskbar
                vtable = ctypes.cast(pTaskbar, ctypes.POINTER(ctypes.POINTER(ctypes.c_void_p))).contents
                proto_HrInit = ctypes.WINFUNCTYPE(ctypes.c_long, ctypes.c_void_p)
                proto_HrInit(vtable[3])(self.pTaskbar)
        except Exception:
            self.pTaskbar = None

    def set_progress_state(self, state: int):
        """Set taskbar progress state: TBPF_NORMAL, TBPF_ERROR, TBPF_PAUSED, or TBPF_NOPROGRESS."""
        if not self.pTaskbar or not self.hwnd:
            return
        try:
            vtable = ctypes.cast(self.pTaskbar, ctypes.POINTER(ctypes.POINTER(ctypes.c_void_p))).contents
            proto_SetProgressState = ctypes.WINFUNCTYPE(ctypes.c_long, ctypes.c_void_p, wintypes.HWND, ctypes.c_int)
            proto_SetProgressState(vtable[10])(self.pTaskbar, self.hwnd, state)
        except Exception:
            pass

    def set_progress_value(self, completed: int, total: int = 100):
        """Set taskbar numeric progress percentage."""
        if not self.pTaskbar or not self.hwnd:
            return
        try:
            vtable = ctypes.cast(self.pTaskbar, ctypes.POINTER(ctypes.POINTER(ctypes.c_void_p))).contents
            proto_SetProgressValue = ctypes.WINFUNCTYPE(ctypes.c_long, ctypes.c_void_p, wintypes.HWND, ctypes.c_uint64, ctypes.c_uint64)
            proto_SetProgressValue(vtable[9])(self.pTaskbar, self.hwnd, completed, total)
        except Exception:
            pass
