import os
import sys
import time
import ctypes
from ctypes import wintypes
from pathlib import Path
from PIL import Image

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import customtkinter as ctk
from gui.dashboard import OmniCaptureApp
from gui.dialogs.component_gallery import ComponentGalleryWindow
from gui.theme import OmniTheme

ARTIFACTS_DIR = Path(os.environ.get("OMNICAPTURE_ARTIFACTS_DIR", str(REPO_ROOT / "docs" / "qa_shots")))

class BITMAPINFOHEADER(ctypes.Structure):
    _fields_ = [
        ('biSize', wintypes.DWORD),
        ('biWidth', wintypes.LONG),
        ('biHeight', wintypes.LONG),
        ('biPlanes', wintypes.WORD),
        ('biBitCount', wintypes.WORD),
        ('biCompression', wintypes.DWORD),
        ('biSizeImage', wintypes.DWORD),
        ('biXPelsPerMeter', wintypes.LONG),
        ('biYPelsPerMeter', wintypes.LONG),
        ('biClrUsed', wintypes.DWORD),
        ('biClrImportant', wintypes.DWORD)
    ]

def capture_real_window(tk_widget, filename: str) -> Path:
    """
    Capture the real on-screen Win32 window (including native caption and DWM frame).
    Uses PrintWindow(parent_hwnd, hdc_mem, PW_RENDERFULLCONTENT).
    """
    tk_widget.update_idletasks()
    tk_widget.update()
    time.sleep(0.2)

    hwnd = tk_widget.winfo_id()
    parent_hwnd = ctypes.windll.user32.GetAncestor(hwnd, 2) or hwnd

    rect = wintypes.RECT()
    ctypes.windll.user32.GetWindowRect(parent_hwnd, ctypes.byref(rect))
    w = rect.right - rect.left
    h = rect.bottom - rect.top

    hdc_win = ctypes.windll.user32.GetWindowDC(parent_hwnd)
    hdc_mem = ctypes.windll.gdi32.CreateCompatibleDC(hdc_win)
    hbm = ctypes.windll.gdi32.CreateCompatibleBitmap(hdc_win, w, h)
    ctypes.windll.gdi32.SelectObject(hdc_mem, hbm)

    # Render full window content including DWM titlebar & client area
    ctypes.windll.user32.PrintWindow(parent_hwnd, hdc_mem, 2)

    bmi = BITMAPINFOHEADER()
    bmi.biSize = ctypes.sizeof(BITMAPINFOHEADER)
    bmi.biWidth = w
    bmi.biHeight = -h
    bmi.biPlanes = 1
    bmi.biBitCount = 32
    bmi.biCompression = 0

    buf = ctypes.create_string_buffer(w * h * 4)
    ctypes.windll.gdi32.GetDIBits(hdc_mem, hbm, 0, h, buf, ctypes.byref(bmi), 0)

    img = Image.frombuffer('RGBA', (w, h), buf, 'raw', 'BGRA', 0, 1)

    # Save to artifacts directory
    out_path = ARTIFACTS_DIR / filename
    img.save(out_path)
    print(f"Captured {filename} -> {out_path} (size: {w}x{h})")

    ctypes.windll.gdi32.DeleteObject(hbm)
    ctypes.windll.gdi32.DeleteDC(hdc_mem)
    ctypes.windll.user32.ReleaseDC(parent_hwnd, hdc_win)

    return out_path

def main():
    print("Starting Milestone 3 Live Window Captures...")
    cfg = {"theme": "dark", "recordings_dir": str(REPO_ROOT / "recordings")}

    # 1. Main Studio Window (Dark Liquid Glass)
    app = OmniCaptureApp(cfg)
    app.geometry("1180x800+80+60")
    app.set_active_theme("dark")
    app.update()
    time.sleep(0.3)
    capture_real_window(app, "m3_dark_liquid_glass.png")

    # 2. Main Studio Window (Light Minimal)
    app.set_active_theme("light")
    app.update()
    time.sleep(0.3)
    capture_real_window(app, "m3_light_minimal.png")

    # 3. Dock at Minimum Window Size (1160x760)
    app.geometry("1160x760+80+60")
    app.update()
    time.sleep(0.3)
    capture_real_window(app, "m3_dock_min_size.png")

    # 4. Window Snapped to Half-Screen (960x900)
    app.geometry("960x900+80+60")
    app.update()
    time.sleep(0.3)
    capture_real_window(app, "m3_window_snapped.png")

    # 5. Window Maximized
    app.state("zoomed")
    app.update()
    time.sleep(0.3)
    capture_real_window(app, "m3_window_maximized.png")
    app.state("normal")
    app.geometry("1180x800+80+60")
    app.update()

    # 6. Tools Menu Dropdown Open
    app.top_bar.open_menu_by_name("tools")
    app.update()
    time.sleep(0.3)
    capture_real_window(app, "m3_menu_dropdown.png")
    if app.top_bar.active_dropdown:
        app.top_bar.active_dropdown.close()

    app.destroy()

    # 7. Component Gallery (Dark Liquid Glass)
    gallery_root = ctk.CTk()
    gallery_root.withdraw()

    OmniTheme.set_theme("dark")
    gallery = ComponentGalleryWindow(gallery_root)
    gallery.geometry("960x820+120+60")
    gallery.update()
    time.sleep(0.3)
    capture_real_window(gallery, "m3_component_gallery_dark.png")

    # 8. Component Gallery (Light Minimal)
    OmniTheme.set_theme("light")
    gallery.update()
    time.sleep(0.3)
    capture_real_window(gallery, "m3_component_gallery_light.png")

    gallery.destroy()
    gallery_root.destroy()

    print("All Milestone 3 live window captures completed successfully!")

if __name__ == "__main__":
    main()
