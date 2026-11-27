import sys
import time
import json
import shutil
import ctypes
from ctypes import wintypes
from pathlib import Path
from PIL import Image

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from gui.dashboard import OmniCaptureApp
from gui.theme import OmniTheme
from gui.dialogs.component_gallery import ComponentGalleryWindow

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

def capture_live_window(hwnd, out_path: Path):
    parent_hwnd = user32.GetAncestor(hwnd, 2) or hwnd # GA_ROOT = 2
    rect = wintypes.RECT()
    user32.GetWindowRect(parent_hwnd, ctypes.byref(rect))
    w = rect.right - rect.left
    h = rect.bottom - rect.top

    hdc_win = user32.GetWindowDC(parent_hwnd)
    hdc_mem = gdi32.CreateCompatibleDC(hdc_win)
    hbmp = gdi32.CreateCompatibleBitmap(hdc_win, w, h)
    old_bmp = gdi32.SelectObject(hdc_mem, hbmp)

    # PW_RENDERFULLCONTENT = 2
    user32.PrintWindow(parent_hwnd, hdc_mem, 2)

    bmi = BITMAPINFO()
    bmi.bmiHeader.biSize = ctypes.sizeof(BITMAPINFOHEADER)
    bmi.bmiHeader.biWidth = w
    bmi.bmiHeader.biHeight = -h  # top-down
    bmi.bmiHeader.biPlanes = 1
    bmi.bmiHeader.biBitCount = 32
    bmi.bmiHeader.biCompression = 0

    buf = ctypes.create_string_buffer(w * h * 4)
    gdi32.GetDIBits(hdc_mem, hbmp, 0, h, buf, ctypes.byref(bmi), 0)

    im = Image.frombuffer("RGBA", (w, h), buf, "raw", "BGRA", 0, 1)
    im_rgb = im.convert("RGB")
    im_rgb.save(str(out_path), "PNG")

    gdi32.SelectObject(hdc_mem, old_bmp)
    gdi32.DeleteObject(hbmp)
    gdi32.DeleteDC(hdc_mem)
    user32.ReleaseDC(parent_hwnd, hdc_win)
    print(f"[✓] Captured: {out_path.name} ({w}x{h})")
    return im_rgb

def audit_pixel_seam(im: Image.Image):
    """Sample colors across native caption and in-app top bar seam."""
    w, h = im.size
    cx = w // 2
    # Sample at y=15 (native titlebar), y=31 (caption boundary), y=45 (in-app header bar)
    pix = im.load()
    c_title = pix[cx, 15]
    c_seam = pix[cx, 31]
    c_inapp = pix[cx, 45]

    hex_title = f"#{c_title[0]:02X}{c_title[1]:02X}{c_title[2]:02X}"
    hex_seam = f"#{c_seam[0]:02X}{c_seam[1]:02X}{c_seam[2]:02X}"
    hex_inapp = f"#{c_inapp[0]:02X}{c_inapp[1]:02X}{c_inapp[2]:02X}"

    print(f"\n--- Pixel Seam Audit (x={cx}) ---")
    print(f"  Native Titlebar (y=15):  RGB{c_title} -> {hex_title}")
    print(f"  Boundary Seam   (y=31):  RGB{c_seam} -> {hex_seam}")
    print(f"  In-App Header   (y=45):  RGB{c_inapp} -> {hex_inapp}")
    return {
        "titlebar": hex_title,
        "seam": hex_seam,
        "in_app": hex_inapp
    }

def main():
    SCREENSHOT_DIR = BASE_DIR / "assets" / "screenshots"
    SCREENSHOT_DIR.mkdir(parents=True, exist_ok=True)
    BRAIN_DIR = Path(r"C:\Users\alone\.gemini\antigravity\brain\81f53aa8-40d6-48c9-aad0-dcdc3f658a18")

    cfg = {
        "scrcpy_dir": "bin",
        "recordings_dir": "recordings",
        "default_record_format": "mp4",
        "max_fps": 60,
        "theme": "dark"
    }

    print("[+] Launching OmniCapture Studio for M5 Dark Liquid Glass visual capture...")
    app = OmniCaptureApp(cfg)
    app.geometry("1180x820+60+60")
    app.update()
    time.sleep(0.4)
    app.update()

    hwnd = app.winfo_id()

    # 1. Dark Default (100% DPI)
    p_dark_100 = SCREENSHOT_DIR / "m5_dark_default_100.png"
    im_dark = capture_live_window(hwnd, p_dark_100)
    seam_audit = audit_pixel_seam(im_dark)

    # 2. Dark Menu Dropdown Open
    try:
        app.top_bar.open_menu_by_name("tools")
        app.update()
        time.sleep(0.4)
        p_menu = SCREENSHOT_DIR / "m5_dark_menu_open.png"
        capture_live_window(hwnd, p_menu)
        if app.top_bar.active_dropdown:
            try:
                app.top_bar.active_dropdown.close()
            except Exception:
                pass
            app.top_bar.active_dropdown = None
    except Exception as e:
        print("Failed to open menu:", e)

    # 3. Dark Command Palette Open
    p_palette = SCREENSHOT_DIR / "m5_dark_palette_open.png"
    try:
        app._open_command_palette()
        app.update()
        time.sleep(0.4)
        capture_live_window(hwnd, p_palette)
        if hasattr(app, "palette") and app.palette:
            try:
                app.palette.destroy()
            except Exception:
                pass
            app.palette = None
    except Exception as e:
        print("Failed to open command palette:", e)

    # 4. Dark Active Recording State
    try:
        tokens = OmniTheme.get_tokens()
        app.cv_recording_hud.place(relx=0.5, rely=0.08, anchor="n")
        app.cv_tally_timer.configure(text="00:01:42")
        app.cv_tally_stats.configure(text="PC: 98.4 MB  ·  Cam: 84.6 MB")
        app.master_record_btn.configure(text="Stop Recording", fg_color=tokens.status_recording)
        app.foot_status_chip.set_status("RECORDING", state="recording")
        app.foot_rec_time.configure(text="REC: 00:01:42")
        app.update()
        time.sleep(0.4)
        p_rec = SCREENSHOT_DIR / "m5_dark_recording_active.png"
        capture_live_window(hwnd, p_rec)
        app.cv_recording_hud.place_forget()
        app.foot_status_chip.set_status("STUDIO READY", state="ready")
        app.foot_rec_time.configure(text="REC: 00:00:00")
        app.master_record_btn.configure(text="Start Recording", fg_color=tokens.accent_primary)
        app.update()
    except Exception as e:
        print("Failed recording capture:", e)

    # 5. Dark 150% DPI simulation (1386x820)
    app.geometry("1386x820+40+40")
    app.update()
    time.sleep(0.4)
    p_dark_150 = SCREENSHOT_DIR / "m5_dark_default_150.png"
    capture_live_window(hwnd, p_dark_150)

    # Teardown main window
    app._recording_pulse_active = False
    app._meter_timer_active = False
    app.controller.stop_device_poller()
    app.hotkeys.stop()
    app.tray.stop()
    app.single_instance.release()
    app.destroy()
    time.sleep(0.3)

    # 6. Component Gallery in Dark Mode
    print("[+] Launching Component Gallery for Dark capture...")
    gallery = ComponentGalleryWindow()
    gallery.geometry("960x780+80+80")
    gallery.update()
    time.sleep(0.4)
    p_gallery_dark = SCREENSHOT_DIR / "m5_dark_component_gallery.png"
    capture_live_window(gallery.winfo_id(), p_gallery_dark)
    gallery.destroy()
    time.sleep(0.3)

    # 7. Side-by-side Light vs Dark layout proof
    p_light_ref = BRAIN_DIR / "m4_light_default_100.png"
    if p_light_ref.exists() and p_dark_100.exists():
        im_l = Image.open(p_light_ref)
        im_d = Image.open(p_dark_100)
        # Ensure identical sizes
        min_w = min(im_l.width, im_d.width)
        min_h = min(im_l.height, im_d.height)
        im_l_crop = im_l.crop((0, 0, min_w, min_h))
        im_d_crop = im_d.crop((0, 0, min_w, min_h))

        side_by_side = Image.new("RGB", (min_w * 2 + 10, min_h), (30, 32, 40))
        side_by_side.paste(im_l_crop, (0, 0))
        side_by_side.paste(im_d_crop, (min_w + 10, 0))
        p_sbs = SCREENSHOT_DIR / "m5_side_by_side_layout.png"
        side_by_side.save(str(p_sbs), "PNG")
        print(f"[✓] Created side-by-side layout proof: {p_sbs.name}")

    # Copy all to brain artifact dir
    copied_files = [p_dark_100, p_menu, p_palette, p_rec, p_dark_150, p_gallery_dark]
    p_sbs = SCREENSHOT_DIR / "m5_side_by_side_layout.png"
    if p_sbs.exists():
        copied_files.append(p_sbs)

    for p in copied_files:
        if p.exists() and BRAIN_DIR.is_dir():
            shutil.copy2(str(p), str(BRAIN_DIR / p.name))
            print(f"[✓] Copied to artifact: {p.name}")

    # Save seam audit json
    audit_file = BASE_DIR / "docs" / "seam_audit_dark.json"
    with open(audit_file, "w", encoding="utf-8") as f:
        json.dump(seam_audit, f, indent=2)
    print(f"[✓] Seam audit saved to {audit_file.name}")

if __name__ == "__main__":
    main()
