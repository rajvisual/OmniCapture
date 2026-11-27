import sys
import ctypes
from ctypes import c_int, byref, sizeof
from typing import Optional

class DWMManager:
    """
    Windows 11 Desktop Window Manager (DWM) Integration.
    Applies native immersive dark/light mode, titlebar color matching, rounded corners,
    and Mica/Acrylic system backdrops via DwmSetWindowAttribute.
    Gracefully degrades on non-Windows or older OS builds.
    """

    # DWM Window Attributes (Windows 10 20H1+ and Windows 11)
    DWMWA_USE_IMMERSIVE_DARK_MODE = 20
    DWMWA_WINDOW_CORNER_PREFERENCE = 33
    DWMWA_BORDER_COLOR = 34
    DWMWA_CAPTION_COLOR = 35
    DWMWA_TEXT_COLOR = 36
    DWMWA_SYSTEMBACKDROP_TYPE = 38

    # Corner preferences
    DWMWCP_DEFAULT = 0
    DWMWCP_DONOTROUND = 1
    DWMWCP_ROUND = 2
    DWMWCP_ROUNDSMALL = 3

    # Backdrop types (Windows 11 22H2+)
    DWMSBT_AUTO = 0
    DWMSBT_NONE = 1
    DWMSBT_MAINWINDOW = 2      # Mica
    DWMSBT_TRANSIENTWINDOW = 3  # Acrylic
    DWMSBT_TABBEDWINDOW = 4     # Tabbed / Mica Alt

    @classmethod
    def get_hwnd(cls, window) -> Optional[int]:
        """Resolve the OS window handle (HWND) for a Tk/CustomTkinter window."""
        if sys.platform != "win32":
            return None
        try:
            window.update_idletasks()
            hwnd = ctypes.windll.user32.GetParent(window.winfo_id())
            if not hwnd:
                hwnd = window.winfo_id()
            return hwnd
        except Exception:
            return None

    @classmethod
    def apply_theme(
        cls,
        window,
        dark_mode: bool = True,
        caption_color_hex: str = "#0B0C10",
        text_color_hex: str = "#F9FAFB",
        backdrop_type: int = 2
    ):
        """
        Apply complete DWM styling to match the application theme:
        - Immersive dark or light titlebar
        - Exact caption color synchronization
        - Rounded window corners (DWMWCP_ROUND)
        - Windows 11 Mica / Acrylic backdrop
        """
        if sys.platform != "win32":
            return

        hwnd = cls.get_hwnd(window)
        if not hwnd:
            return

        dwmapi = ctypes.windll.dwmapi

        # 1. Immersive Dark Mode
        try:
            val = c_int(1 if dark_mode else 0)
            dwmapi.DwmSetWindowAttribute(
                hwnd,
                cls.DWMWA_USE_IMMERSIVE_DARK_MODE,
                byref(val),
                sizeof(val)
            )
        except Exception:
            pass

        # 2. Window Corner Preference (Rounded corners on Win11)
        try:
            corner_val = c_int(cls.DWMWCP_ROUND)
            dwmapi.DwmSetWindowAttribute(
                hwnd,
                cls.DWMWA_WINDOW_CORNER_PREFERENCE,
                byref(corner_val),
                sizeof(corner_val)
            )
        except Exception:
            pass

        # 3. Caption Color (HEX -> BGR format: 0x00BBGGRR)
        try:
            r = int(caption_color_hex[1:3], 16)
            g = int(caption_color_hex[3:5], 16)
            b = int(caption_color_hex[5:7], 16)
            bgr_color = c_int((b << 16) | (g << 8) | r)
            dwmapi.DwmSetWindowAttribute(
                hwnd,
                cls.DWMWA_CAPTION_COLOR,
                byref(bgr_color),
                sizeof(bgr_color)
            )
        except Exception:
            pass

        # 4. Caption Text Color
        try:
            tr = int(text_color_hex[1:3], 16)
            tg = int(text_color_hex[3:5], 16)
            tb = int(text_color_hex[5:7], 16)
            bgr_text = c_int((tb << 16) | (tg << 8) | tr)
            dwmapi.DwmSetWindowAttribute(
                hwnd,
                cls.DWMWA_TEXT_COLOR,
                byref(bgr_text),
                sizeof(bgr_text)
            )
        except Exception:
            pass

        # 5. System Backdrop Type (Mica / Acrylic)
        try:
            bd_val = c_int(backdrop_type)
            dwmapi.DwmSetWindowAttribute(
                hwnd,
                cls.DWMWA_SYSTEMBACKDROP_TYPE,
                byref(bd_val),
                sizeof(bd_val)
            )
        except Exception:
            pass
