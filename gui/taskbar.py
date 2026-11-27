import sys
import io
import ctypes
from ctypes import wintypes
from typing import Optional
from PIL import Image, ImageDraw
from core.version import APP_USER_MODEL_ID

class TaskbarManager:
    """
    Windows 7+ Taskbar Integration via ITaskbarList3 COM Interface.
    Features:
    - Taskbar overlay icons (red recording badge) via SetOverlayIcon (vtable[18])
    - Taskbar progress bar (TBPF_NORMAL green for file uploads only)
    - Explicit AppUserModelID registration for taskbar pinning and grouping
    """

    TBPF_NOPROGRESS = 0
    TBPF_INDETERMINATE = 1
    TBPF_NORMAL = 2      # Green (Used strictly for file uploads)
    TBPF_ERROR = 4       # Red
    TBPF_PAUSED = 8      # Yellow

    _app_user_model_id_set = False

    @classmethod
    def set_app_user_model_id(cls, app_id: Optional[str] = None):
        """Register explicit AppUserModelID for taskbar pinning and grouping."""
        app_id = app_id or APP_USER_MODEL_ID
        if sys.platform == "win32" and not cls._app_user_model_id_set:
            try:
                ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(app_id)
                cls._app_user_model_id_set = True
            except Exception:
                pass

    def __init__(self, hwnd: Optional[int] = None):
        self.hwnd = hwnd
        self.pTaskbar = None
        self._rec_hicon = None
        self._init_com()
        if sys.platform == "win32":
            self._rec_hicon = self._create_recording_hicon()

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

    def _create_recording_hicon(self) -> Optional[int]:
        """Dynamically generate a crisp 16x16 red recording overlay icon in memory."""
        try:
            img = Image.new("RGBA", (16, 16), (0, 0, 0, 0))
            draw = ImageDraw.Draw(img)
            # Red recording badge with crisp white specular outline
            draw.ellipse([2, 2, 13, 13], fill="#DC2626", outline="#FFFFFF", width=1)
            buf = io.BytesIO()
            img.save(buf, format="ICO")
            ico_bytes = buf.getvalue()
            if len(ico_bytes) > 22:
                hicon = ctypes.windll.user32.CreateIconFromResourceEx(
                    ico_bytes[22:],
                    len(ico_bytes) - 22,
                    True,
                    0x00030000,
                    16, 16,
                    0
                )
                return hicon
        except Exception:
            pass
        return None

    def set_overlay_icon(self, hicon: Optional[int], description: Optional[str] = None):
        """Set or clear the taskbar thumbnail overlay badge (vtable index 18)."""
        if not self.pTaskbar or not self.hwnd or sys.platform != "win32":
            return
        try:
            vtable = ctypes.cast(self.pTaskbar, ctypes.POINTER(ctypes.POINTER(ctypes.c_void_p))).contents
            proto_SetOverlayIcon = ctypes.WINFUNCTYPE(
                ctypes.c_long,
                ctypes.c_void_p,
                wintypes.HWND,
                wintypes.HICON,
                wintypes.LPCWSTR
            )
            proto_SetOverlayIcon(vtable[18])(
                self.pTaskbar,
                self.hwnd,
                hicon or 0,
                description or ""
            )
        except Exception:
            pass

    def set_recording_overlay(self, active: bool):
        """Toggle the red recording overlay icon on the taskbar."""
        if active:
            if not self._rec_hicon:
                self._rec_hicon = self._create_recording_hicon()
            self.set_overlay_icon(self._rec_hicon, "OmniCapture — Recording Active")
        else:
            self.set_overlay_icon(None, None)

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

    def cleanup(self):
        """Release cached icon resource."""
        if self._rec_hicon and sys.platform == "win32":
            try:
                ctypes.windll.user32.DestroyIcon(self._rec_hicon)
            except Exception:
                pass
            self._rec_hicon = None
