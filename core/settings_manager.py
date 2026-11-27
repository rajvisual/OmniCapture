import os
import sys
import json
import ctypes
from ctypes import wintypes
from pathlib import Path
from typing import Dict, Any, Tuple, Optional

DEFAULT_SETTINGS = {
    "window_width": 1180,
    "window_height": 820,
    "window_x": None,
    "window_y": None,
    "is_maximized": False,
    "theme": None,
    "show_guides": True,
    "minimize_to_tray": True,
    "enable_hotkeys": True,
    "default_record_format": "mkv",
    "video_bit_rate": "8M",
    "max_fps": 60,
    "camera_facing": "back",
    "touch_mode": "touch",
    "disk_warn_gb": 2.0,
    "disk_stop_mb": 500
}

def get_appdata_dir() -> Path:
    """Resolve %APPDATA%/OmniCapture with safe fallback."""
    appdata = os.environ.get("APPDATA")
    if appdata:
        base = Path(appdata) / "OmniCapture"
    else:
        base = Path.home() / ".omnicapture"
    base.mkdir(parents=True, exist_ok=True)
    return base

def get_settings_file_path() -> Path:
    return get_appdata_dir() / "settings.json"

def get_primary_work_area() -> Tuple[int, int, int, int]:
    """Returns (left, top, width, height) of the primary monitor work area (excluding taskbar)."""
    if sys.platform == "win32":
        try:
            rc = wintypes.RECT()
            # SPI_GETWORKAREA = 0x0030
            if ctypes.windll.user32.SystemParametersInfoW(0x0030, 0, ctypes.byref(rc), 0):
                return rc.left, rc.top, rc.right - rc.left, rc.bottom - rc.top
        except Exception:
            pass
    return 0, 0, 1366, 720

def get_adaptive_default_geometry() -> Tuple[int, int, int, int]:
    """Calculate default (x, y, w, h) bounded by min(1180x820, 90% of primary work area)."""
    wl, wt, ww, wh = get_primary_work_area()
    w = min(1180, max(960, int(ww * 0.90)))
    h = min(820, max(580, int(wh * 0.90)))
    x = max(wl, wl + (ww - w) // 2)
    y = max(wt, wt + (wh - h) // 2)
    return x, y, w, h

def get_adaptive_minimum_geometry() -> Tuple[int, int]:
    """Calculate safe minimum (w, h) that comfortably fits within the work area."""
    _, _, ww, wh = get_primary_work_area()
    min_w = min(1080, max(800, int(ww * 0.82)))
    min_h = min(620, max(540, int(wh * 0.82)))
    return min_w, min_h

def clamp_window_geometry(
    x: Optional[int],
    y: Optional[int],
    w: Optional[int],
    h: Optional[int],
    min_w: Optional[int] = None,
    min_h: Optional[int] = None
) -> Tuple[int, int, int, int]:
    """
    Ensure the window coordinates (x, y, w, h) are fully clamped inside
    the visible virtual desktop. If a monitor was disconnected, the window
    is safely centered on the primary display.
    """
    adaptive_min_w, adaptive_min_h = get_adaptive_minimum_geometry()
    eff_min_w = min_w if min_w is not None else adaptive_min_w
    eff_min_h = min_h if min_h is not None else adaptive_min_h

    if sys.platform != "win32":
        cur_w = w if w is not None else eff_min_w
        cur_h = h if h is not None else eff_min_h
        cur_x = x if x is not None else 0
        cur_y = y if y is not None else 0
        return max(eff_min_w, cur_w), max(eff_min_h, cur_h), max(0, cur_x), max(0, cur_y)

    user32 = ctypes.windll.user32
    SM_XVIRTUALSCREEN = 76
    SM_YVIRTUALSCREEN = 77
    SM_CXVIRTUALSCREEN = 78
    SM_CYVIRTUALSCREEN = 79

    vx = user32.GetSystemMetrics(SM_XVIRTUALSCREEN)
    vy = user32.GetSystemMetrics(SM_YVIRTUALSCREEN)
    vw = user32.GetSystemMetrics(SM_CXVIRTUALSCREEN)
    vh = user32.GetSystemMetrics(SM_CYVIRTUALSCREEN)

    # Primary display bounds fallback
    primary_w = user32.GetSystemMetrics(0) # SM_CXSCREEN
    primary_h = user32.GetSystemMetrics(1) # SM_CYSCREEN

    target_w = w if w is not None else min(1180, int(primary_w * 0.9))
    target_h = h if h is not None else min(820, int(primary_h * 0.9))

    clamped_w = max(eff_min_w, min(target_w, vw))
    clamped_h = max(eff_min_h, min(target_h, vh))

    # If coordinates are None or completely outside virtual screen bounds
    if x is None or y is None or x < vx or x > (vx + vw - 100) or y < vy or y > (vy + vh - 100):
        # Center on primary monitor
        clamped_x = max(0, (primary_w - clamped_w) // 2)
        clamped_y = max(0, (primary_h - clamped_h) // 2)
    else:
        # Keep titlebar within visible display
        clamped_x = max(vx, min(x, vx + vw - clamped_w))
        clamped_y = max(vy, min(y, vy + vh - clamped_h))

    return clamped_x, clamped_y, clamped_w, clamped_h

class SettingsManager:
    """Manages persistent application settings stored in %APPDATA%/OmniCapture/settings.json."""

    @classmethod
    def load(cls) -> Dict[str, Any]:
        path = get_settings_file_path()
        settings = dict(DEFAULT_SETTINGS)
        if path.is_file():
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
                if isinstance(data, dict):
                    settings.update(data)
            except Exception:
                pass
        return settings

    @classmethod
    def save(cls, settings: Dict[str, Any]):
        path = get_settings_file_path()
        try:
            path.write_text(json.dumps(settings, indent=2), encoding="utf-8")
        except Exception:
            pass
