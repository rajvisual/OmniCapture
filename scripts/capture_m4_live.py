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

ARTIFACTS_DIR = Path(r"C:\Users\alone\.gemini\antigravity\brain\81f53aa8-40d6-48c9-aad0-dcdc3f658a18")

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
    """Capture on-screen window including native Win32 DWM frame."""
    tk_widget.update_idletasks()
    tk_widget.update()
    time.sleep(0.3)

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
    out_path = ARTIFACTS_DIR / filename
    img.save(out_path)
    print(f"Captured {filename} -> {out_path} ({w}x{h})")

    ctypes.windll.gdi32.DeleteObject(hbm)
    ctypes.windll.gdi32.DeleteDC(hdc_mem)
    ctypes.windll.user32.ReleaseDC(parent_hwnd, hdc_win)

    return out_path

def sample_seam_pixel(image_path: Path):
    """
    Sample pixels across the seam between the native DWM caption and in-app top bar.
    Reports the pixel colors to verify continuous band.
    """
    img = Image.open(image_path).convert("RGB")
    w, h = img.size
    cx = w // 2 # Center column

    # Sample vertically from y=10 (native titlebar) to y=50 (in-app topbar)
    # Native titlebar is typically top 32px on Windows 11
    print("\n--- Pixel Seam Color Audit ---")
    y_caption = 15 # Inside native caption
    y_seam = 32 # At caption / client border
    y_topbar = 45 # Inside in-app top bar

    c_caption = img.getpixel((cx, y_caption))
    c_seam = img.getpixel((cx, y_seam))
    c_topbar = img.getpixel((cx, y_topbar))

    hex_caption = f"#{c_caption[0]:02X}{c_caption[1]:02X}{c_caption[2]:02X}"
    hex_seam = f"#{c_seam[0]:02X}{c_seam[1]:02X}{c_seam[2]:02X}"
    hex_topbar = f"#{c_topbar[0]:02X}{c_topbar[1]:02X}{c_topbar[2]:02X}"

    print(f"Native Titlebar (y={y_caption}): RGB{c_caption} -> {hex_caption}")
    print(f"Seam Boundary   (y={y_seam}): RGB{c_seam} -> {hex_seam}")
    print(f"In-App Top Bar  (y={y_topbar}): RGB{c_topbar} -> {hex_topbar}")

    return hex_caption, hex_seam, hex_topbar

def main():
    print("Beginning Milestone 4 Live Window Captures...")
    cfg = {"theme": "light", "recordings_dir": str(REPO_ROOT / "recordings")}

    # 1. Main Studio Window: Light Minimal Default (100% DPI)
    app = OmniCaptureApp(cfg)
    app.geometry("1180x800+80+60")
    app.set_active_theme("light")
    app.update()
    time.sleep(0.4)
    p_default = capture_real_window(app, "m4_light_default_100.png")
    sample_seam_pixel(p_default)

    # 2. Main Studio Window: With Menu Open (Tools menu)
    try:
        app.top_bar.open_menu_by_name("tools")
        app.update()
        time.sleep(0.4)
        capture_real_window(app, "m4_light_menu_open.png")
        if app.top_bar.active_dropdown:
            app.top_bar.active_dropdown.close()
            app.update()
    except Exception as e:
        print(f"Failed to open menu: {e}")

    # 3. Main Studio Window: Active Recording State
    try:
        # Simulate active recording HUD and button states
        app.controller._dual_recording = True
        app.controller._rec_start_time = time.time() - 42.5 # 42s recorded
        tokens = OmniTheme.get_tokens()
        app.master_record_btn.configure(
            text="Stop Recording",
            fg_color=tokens.status_recording,
            hover_color=tokens.status_recording_hover,
            text_color="#FFFFFF"
        )
        app.foot_status_chip.set_status("RECORDING", "recording")
        app.cv_recording_hud.place(relx=0.5, rely=0.15, anchor="center")
        app.cv_tally_timer.configure(text="00:00:42")
        app.foot_rec_time.configure(text="00:00:42", text_color=tokens.status_recording)
        app.update()
        time.sleep(0.4)
        capture_real_window(app, "m4_light_recording_active.png")

        # Revert simulated recording
        app.controller._dual_recording = False
        app.cv_recording_hud.place_forget()
        app.master_record_btn.configure(
            text="Start Recording",
            fg_color=tokens.accent_primary,
            hover_color=tokens.accent_hover,
            text_color="#FFFFFF"
        )
        app.foot_status_chip.set_status("STUDIO READY", "ready")
        app.foot_rec_time.configure(text="00:00:00", text_color=tokens.text_muted)
        app.update()
    except Exception as e:
        print(f"Failed recording capture: {e}")

    if hasattr(app, "single_instance") and app.single_instance:
        app.single_instance.release()
    app.destroy()

    # 4. Main Studio Window: 150% Scaling
    try:
        ctk.set_widget_scaling(1.5)
        app_150 = OmniCaptureApp(cfg)
        app_150.geometry("1400x900+40+40")
        app_150.set_active_theme("light")
        app_150.update()
        time.sleep(0.5)
        capture_real_window(app_150, "m4_light_default_150.png")
        if hasattr(app_150, "single_instance") and app_150.single_instance:
            app_150.single_instance.release()
        app_150.destroy()
        # Reset scaling back to 1.0
        ctk.set_widget_scaling(1.0)
    except Exception as e:
        print(f"Failed 150% capture: {e}")
        ctk.set_widget_scaling(1.0)

    # 5. Component Gallery Window (Light Theme)
    root = ctk.CTk()
    root.withdraw()
    OmniTheme.set_theme("light")
    gallery = ComponentGalleryWindow(root)
    gallery.geometry("960x780+120+80")
    gallery.update()
    time.sleep(0.5)
    capture_real_window(gallery, "m4_light_component_gallery.png")
    gallery.destroy()
    root.destroy()

    print("\nMilestone 4 Live Captures Completed Successfully.")

if __name__ == "__main__":
    main()
