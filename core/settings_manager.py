import os
import sys
import json
import ctypes
from ctypes import wintypes
from pathlib import Path
from typing import Dict, Any, Tuple

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
    "default_record_format": "mp4",
    "video_bit_rate": "8M",
    "max_fps": 60,
    "camera_facing": "back",
    "touch_mode": "touch"
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

def clamp_window_geometry(
    x: int,
    y: int,
    w: int,
    h: int,
    min_w: int = 1100,
    min_h: int = 720
) -> Tuple[int, int, int, int]:
    """
    Ensure the window coordinates (x, y, w, h) are fully clamped inside
    the visible virtual desktop. If a monitor was disconnected, the window
    is safely centered on the primary display.
    """
    if sys.platform != "win32":
        return max(min_w, w), max(min_h, h), max(0, x), max(0, y)

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

    clamped_w = max(min_w, min(w, vw))
    clamped_h = max(min_h, min(h, vh))

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
