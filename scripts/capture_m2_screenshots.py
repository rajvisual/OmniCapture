import os
import sys
import time
import shutil
import ctypes
from ctypes import wintypes
from pathlib import Path
from PIL import Image

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from gui.dashboard import OmniCaptureApp
from gui.theme import OmniTheme

user32 = ctypes.windll.user32
gdi32 = ctypes.windll.gdi32

class BITMAPINFOHEADER(ctypes.Structure):
    _fields_ = [
        ("biSize", wintypes.DWORD),
        ("biWidth", wintypes.LONG),
        ("biHeight", wintypes.LONG),
        ("biPlanes", wintypes.WORD),
        ("biBitCount", wintypes.WORD),
        ("biCompression", wintypes.DWORD),
        ("biSizeImage", wintypes.DWORD),
        ("biXPelsPerMeter", wintypes.LONG),
        ("biYPelsPerMeter", wintypes.LONG),
        ("biClrUsed", wintypes.DWORD),
        ("biClrImportant", wintypes.DWORD),
    ]

class BITMAPINFO(ctypes.Structure):
    _fields_ = [
        ("bmiHeader", BITMAPINFOHEADER),
        ("bmiColors", wintypes.DWORD * 3),
    ]

def capture_hwnd(hwnd, out_path: Path):
    rect = wintypes.RECT()
    user32.GetWindowRect(hwnd, ctypes.byref(rect))
    w = rect.right - rect.left
    h = rect.bottom - rect.top

    hdc_win = user32.GetWindowDC(hwnd)
    hdc_mem = gdi32.CreateCompatibleDC(hdc_win)
    hbmp = gdi32.CreateCompatibleBitmap(hdc_win, w, h)
    gdi32.SelectObject(hdc_mem, hbmp)

    # PW_RENDERFULLCONTENT = 2
    user32.PrintWindow(hwnd, hdc_mem, 2)

    bmi = BITMAPINFO()
    bmi.bmiHeader.biSize = ctypes.sizeof(BITMAPINFOHEADER)
    bmi.bmiHeader.biWidth = w
    bmi.bmiHeader.biHeight = -h  # top-down
    bmi.bmiHeader.biPlanes = 1
    bmi.bmiHeader.biBitCount = 32
    bmi.bmiHeader.biCompression = 0  # BI_RGB

    buf = ctypes.create_string_buffer(w * h * 4)
    gdi32.GetDIBits(hdc_mem, hbmp, 0, h, buf, ctypes.byref(bmi), 0)

    im = Image.frombuffer("RGBA", (w, h), buf, "raw", "BGRA", 0, 1)
    im_rgb = im.convert("RGB")
    im_rgb.save(str(out_path), "PNG")

    gdi32.DeleteObject(hbmp)
    gdi32.DeleteDC(hdc_mem)
    user32.ReleaseDC(hwnd, hdc_win)
    print(f"[✓] Captured: {out_path.name} ({w}x{h})")

def main():
    SCREENSHOT_DIR = BASE_DIR / "assets" / "screenshots"
    SCREENSHOT_DIR.mkdir(parents=True, exist_ok=True)
    BRAIN_DIR = Path(os.environ.get("OMNICAPTURE_ARTIFACTS_DIR", str(BASE_DIR / "docs" / "qa_shots")))

    cfg = {
        "scrcpy_dir": "bin",
        "recordings_dir": "recordings",
        "default_record_format": "mp4",
        "max_fps": 60,
    }

    print("[+] Launching OmniCapture Studio for M2 visual capture...")
    app = OmniCaptureApp(cfg)
    app.geometry("1180x820+50+50")
    app.update()
    time.sleep(0.5)
    app.update()

    hwnd = app.winfo_id()

    # 1. Capture Dark Liquid Glass Theme
    app.set_active_theme("dark")
    app.update()
    time.sleep(0.5)
    p_dark = SCREENSHOT_DIR / "m2_dark_liquid_glass.png"
    capture_hwnd(hwnd, p_dark)

    # 2. Capture With Menu Dropdown Open
    app.top_bar.open_menu_by_name("Capture")
    app.update()
    time.sleep(0.4)
    p_menu = SCREENSHOT_DIR / "m2_menu_dropdown.png"
    capture_hwnd(hwnd, p_menu)
    if app.top_bar.active_dropdown:
        try:
            app.top_bar.active_dropdown.close()
        except Exception:
            pass
        app.top_bar.active_dropdown = None

    # 3. Capture Active Recording State
    app.cv_recording_hud.place(relx=0.5, rely=0.08, anchor="n")
    app.cv_tally_timer.configure(text="00:01:42")
    app.cv_tally_stats.configure(text="PC: 98.4 MB  ·  Cam: 84.6 MB")
    app.master_record_btn.configure(text="Stop Recording", fg_color=OmniTheme.get_tokens().status_recording)
    app.foot_status_chip.set_status("RECORDING", state="recording")
    app.foot_rec_time.configure(text="REC: 00:01:42")
    app.update()
    time.sleep(0.4)
    p_rec = SCREENSHOT_DIR / "m2_recording_active.png"
    capture_hwnd(hwnd, p_rec)

    # 4. Capture Light Minimal Theme
    app.cv_recording_hud.place_forget()
    app.set_active_theme("light")
    app.foot_status_chip.set_status("STUDIO READY", state="ready")
    app.foot_rec_time.configure(text="REC: 00:00:00")
    app.update()
    time.sleep(0.5)
    p_light = SCREENSHOT_DIR / "m2_light_minimal.png"
    capture_hwnd(hwnd, p_light)

    # Copy all to brain artifact directory
    if BRAIN_DIR.is_dir():
        for p in [p_dark, p_menu, p_rec, p_light]:
            dst = BRAIN_DIR / p.name
            shutil.copy2(str(p), str(dst))
            print(f"[✓] Copied to artifact: {dst.name}")

    # Cleanup
    app._recording_pulse_active = False
    app._meter_timer_active = False
    app.controller.stop_device_poller()
    app.hotkeys.stop()
    app.tray.stop()
    app.single_instance.release()
    app.destroy()
    print("[✓] All M2 screenshots successfully generated and saved.")

if __name__ == "__main__":
    main()
