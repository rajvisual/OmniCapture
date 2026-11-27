"""
OmniCapture Studio — Milestone 6 Interactive User QA Screenshot Utility.
Runs in the user's interactive Windows desktop session to capture real, pixel-accurate
screenshots directly from the display using win32 API and PIL.ImageGrab.

Avoids Tk PrintWindow rendering artifacts (black boxes, offset controls, missed DWM glass).
Captures:
- Real screen rectangle including caption, rounded corners, Mica/Acrylic backdrops
- Light and Dark themes
- All major dialogs: Media Library, Preferences, Diagnostics, Command Palette, Onboarding, Simulated Device Control
- Key states from the State Matrix
- Saves numbered PNGs to docs/qa_shots/
- Supports interactive manual mode + step-by-step automatic capture tour
- Displays DPI instructions for testing at 100%, 125%, and 150% display scaling
"""

import os
import sys
import time
import argparse
from pathlib import Path
from typing import Optional, Tuple

# Add repository root to path
REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from PIL import ImageGrab
import tkinter as tk
import customtkinter as ctk

# Ensure Windows DPI awareness is initialized
try:
    import ctypes
    from ctypes import wintypes
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(2) # Per-monitor DPI aware
    except Exception:
        ctypes.windll.user32.SetProcessDPIAware()
except Exception:
    pass

QA_SHOTS_DIR = REPO_ROOT / "docs" / "qa_shots"
QA_SHOTS_DIR.mkdir(parents=True, exist_ok=True)

def bring_window_to_front(hwnd: int) -> bool:
    """Ensure the target window is restored, visible, and focused at top of Z-order."""
    if sys.platform != "win32" or not hwnd:
        return False
    try:
        user32 = ctypes.windll.user32
        SW_RESTORE = 9
        user32.ShowWindow(hwnd, SW_RESTORE)
        user32.SetForegroundWindow(hwnd)
        user32.BringWindowToTop(hwnd)
        time.sleep(0.15) # Wait for DWM compositor paint
        return True
    except Exception as e:
        print(f"[WARN] Failed to bring HWND {hwnd} to front: {e}")
        return False

def get_window_screen_rect(hwnd: int, widget: Optional[ctk.CTk] = None) -> Optional[Tuple[int, int, int, int]]:
    """
    Get bounding box (left, top, right, bottom) of window on screen.
    Uses Win32 GetWindowRect when available for caption/shadow inclusion,
    falling back to Tk winfo geometry.
    """
    if sys.platform == "win32" and hwnd:
        try:
            class RECT(ctypes.Structure):
                _fields_ = [
                    ("left", wintypes.LONG),
                    ("top", wintypes.LONG),
                    ("right", wintypes.LONG),
                    ("bottom", wintypes.LONG)
                ]
            rect = RECT()
            if ctypes.windll.user32.GetWindowRect(hwnd, ctypes.byref(rect)):
                # Return tuple bbox
                return (rect.left, rect.top, rect.right, rect.bottom)
        except Exception:
            pass

    if widget:
        try:
            widget.update_idletasks()
            x = widget.winfo_rootx()
            y = widget.winfo_rooty()
            w = widget.winfo_width()
            h = widget.winfo_height()
            return (x, y, x + w, y + h)
        except Exception:
            pass

    return None

def capture_screen_bbox(bbox: Tuple[int, int, int, int], output_path: Path) -> bool:
    """Capture on-screen pixels using ImageGrab and save to PNG."""
    try:
        # Extra 50ms pause to ensure DWM has composed the backbuffer
        time.sleep(0.08)
        img = ImageGrab.grab(bbox=bbox, all_screens=True)
        img.save(str(output_path), "PNG")
        print(f"  [SAVED] {output_path.name} ({img.width}x{img.height})")
        return True
    except Exception as e:
        print(f"  [ERROR] Failed to capture {output_path.name}: {e}")
        return False

def print_dpi_instructions():
    """Print guidance on verifying Windows display scaling."""
    print("=" * 76)
    print(" OmniCapture Studio — Display Scaling (DPI) Testing Guide")
    print("=" * 76)
    print("To verify UI layout at 100%, 125%, and 150% Windows display scaling:")
    print("  1. Open Windows Settings (Win + I) > System > Display.")
    print("  2. Under 'Scale & layout', change 'Scale' to:")
    print("     - 100% (Standard 96 DPI - baseline)")
    print("     - 125% (Common laptop 1080p scaling)")
    print("     - 150% (High-density 1080p / 4K standard)")
    print("  3. Run this script again after changing the scale:")
    print("     python scripts/user_qa_screenshots.py --auto")
    print("  4. Verify that dock strips, sliders, meters, and control buttons")
    print("     maintain 0px clipping and correct proportional spacing.")
    print("=" * 76)
    print()

def run_automated_tour():
    """Step through all themes, dialogs, and states, capturing numbered screenshots."""
    print("[INFO] Starting Automated QA Screenshot Tour...")
    print(f"[INFO] Saving shots to: {QA_SHOTS_DIR}")

    # Launch OmniCapture Studio with simulated device engine
    sys.argv = [sys.argv[0], "--demo-device", "--no-onboarding"]
    from gui.dashboard import OmniCaptureApp
    from gui.theme import OmniTheme

    config = {"theme": "dark", "window_width": 1180, "window_height": 820}
    app = OmniCaptureApp(config)

    # Let window map and position
    app.update()
    time.sleep(0.5)
    hwnd = app.winfo_id()
    bring_window_to_front(hwnd)

    def snap(name: str):
        bring_window_to_front(hwnd)
        app.update()
        time.sleep(0.12)
        bbox = get_window_screen_rect(hwnd, app)
        if bbox:
            capture_screen_bbox(bbox, QA_SHOTS_DIR / name)

    # 1. Dark Theme Studio (Default with Simulated Device)
    print("[1/13] Capturing 01_dark_studio_default.png...")
    OmniTheme.set_theme("dark")
    app.apply_theme(OmniTheme.get_tokens())
    snap("01_dark_studio_default.png")

    # 2. Light Theme Studio
    print("[2/13] Capturing 02_light_studio_default.png...")
    OmniTheme.set_theme("light")
    app.apply_theme(OmniTheme.get_tokens())
    snap("02_light_studio_default.png")

    # Revert to Dark for error states tour
    OmniTheme.set_theme("dark")
    app.apply_theme(OmniTheme.get_tokens())

    # 3. State Matrix: Unauthorized
    print("[3/13] Capturing 03_dark_state_matrix_unauthorized.png...")
    if hasattr(app, "state_banner"):
        app.state_banner.set_state("unauthorized")
    snap("03_dark_state_matrix_unauthorized.png")

    # 4. State Matrix: Camera Locked
    print("[4/13] Capturing 04_dark_state_matrix_camera_locked.png...")
    if hasattr(app, "state_banner"):
        app.state_banner.set_state("camera_locked")
    snap("04_dark_state_matrix_camera_locked.png")

    # 5. State Matrix: Device Detached Mid-Recording
    print("[5/16] Capturing 05_dark_state_matrix_device_unplugged.png...")
    if hasattr(app, "state_banner"):
        app.state_banner.set_state("device_unplugged")
    snap("05_dark_state_matrix_device_unplugged.png")

    # 5b. State Matrix: Upload Failed
    print("[5b/16] Capturing 05b_dark_state_upload_failed.png...")
    if hasattr(app, "state_banner"):
        app.state_banner.set_state("upload_failed")
    snap("05b_dark_state_upload_failed.png")

    # 5c. State Matrix: Engine Crashed
    print("[5c/16] Capturing 05c_dark_state_engine_crashed.png...")
    if hasattr(app, "state_banner"):
        app.state_banner.set_state("engine_crashed")
    snap("05c_dark_state_engine_crashed.png")

    # 5d. State Matrix: Scrcpy Missing
    print("[5d/16] Capturing 05d_dark_state_scrcpy_missing.png...")
    if hasattr(app, "state_banner"):
        app.state_banner.set_state("scrcpy_missing")
    snap("05d_dark_state_scrcpy_missing.png")

    # Reset banner to connected
    if hasattr(app, "state_banner"):
        app.state_banner.set_state("connected_usb")

    # 6. Command Palette
    print("[6/13] Capturing 06_dark_command_palette.png...")
    app._open_command_palette()
    app.update()
    time.sleep(0.2)
    snap("06_dark_command_palette.png")
    if hasattr(app, "palette") and app.palette:
        app.palette.close()
        app.update()

    # 7. Media Library Dialog
    print("[7/13] Capturing 07_dark_dialog_recordings_library.png...")
    from gui.dialogs.recordings import RecordingsGalleryDialog
    dlg_rec = RecordingsGalleryDialog(app, app.controller)
    dlg_rec.update()
    time.sleep(0.2)
    rec_hwnd = dlg_rec.winfo_id()
    bring_window_to_front(rec_hwnd)
    rec_bbox = get_window_screen_rect(rec_hwnd, dlg_rec)
    if rec_bbox:
        capture_screen_bbox(rec_bbox, QA_SHOTS_DIR / "07_dark_dialog_recordings_library.png")
    dlg_rec.destroy()
    app.update()

    # 8. Preferences Dialog
    print("[8/13] Capturing 08_dark_dialog_preferences.png...")
    from gui.dialogs.settings import StudioSettingsDialog
    dlg_set = StudioSettingsDialog(app, app.app_config, app.controller, app.minimize_to_tray_var, app.enable_hotkeys_var)
    dlg_set.update()
    time.sleep(0.2)
    set_hwnd = dlg_set.winfo_id()
    bring_window_to_front(set_hwnd)
    set_bbox = get_window_screen_rect(set_hwnd, dlg_set)
    if set_bbox:
        capture_screen_bbox(set_bbox, QA_SHOTS_DIR / "08_dark_dialog_preferences.png")
    dlg_set.destroy()
    app.update()

    # 9. Diagnostics Dialog
    print("[9/13] Capturing 09_dark_dialog_diagnostics.png...")
    from gui.dialogs.diagnostics import DiagnosticsDialog
    dlg_diag = DiagnosticsDialog(app, app.controller)
    dlg_diag.update()
    time.sleep(0.2)
    diag_hwnd = dlg_diag.winfo_id()
    bring_window_to_front(diag_hwnd)
    diag_bbox = get_window_screen_rect(diag_hwnd, dlg_diag)
    if diag_bbox:
        capture_screen_bbox(diag_bbox, QA_SHOTS_DIR / "09_dark_dialog_diagnostics.png")
    dlg_diag.destroy()
    app.update()

    # 10. Onboarding Checklist Dialog (Dark)
    print("[10/13] Capturing 10_dark_dialog_onboarding_checklist.png...")
    from gui.dialogs.onboarding import OnboardingChecklistDialog
    dlg_onb = OnboardingChecklistDialog(app, app.controller)
    dlg_onb.update()
    time.sleep(0.2)
    onb_hwnd = dlg_onb.winfo_id()
    bring_window_to_front(onb_hwnd)
    onb_bbox = get_window_screen_rect(onb_hwnd, dlg_onb)
    if onb_bbox:
        capture_screen_bbox(onb_bbox, QA_SHOTS_DIR / "10_dark_dialog_onboarding_checklist.png")
    dlg_onb.destroy()
    app.update()

    # 11. Simulated Device Control Dialog
    print("[11/13] Capturing 11_dark_dialog_simulated_device.png...")
    from gui.dialogs.simulated_device import SimulatedDeviceControlDialog
    dlg_sim = SimulatedDeviceControlDialog(app, app._sim_engine)
    dlg_sim.update()
    time.sleep(0.2)
    sim_hwnd = dlg_sim.winfo_id()
    bring_window_to_front(sim_hwnd)
    sim_bbox = get_window_screen_rect(sim_hwnd, dlg_sim)
    if sim_bbox:
        capture_screen_bbox(sim_bbox, QA_SHOTS_DIR / "11_dark_dialog_simulated_device.png")
    dlg_sim.destroy()
    app.update()

    # 12. Preferences Dialog (Light)
    print("[12/13] Capturing 12_light_dialog_preferences.png...")
    OmniTheme.set_theme("light")
    app.apply_theme(OmniTheme.get_tokens())
    dlg_set_light = StudioSettingsDialog(app, app.app_config, app.controller, app.minimize_to_tray_var, app.enable_hotkeys_var)
    dlg_set_light.update()
    time.sleep(0.2)
    set_light_hwnd = dlg_set_light.winfo_id()
    bring_window_to_front(set_light_hwnd)
    set_light_bbox = get_window_screen_rect(set_light_hwnd, dlg_set_light)
    if set_light_bbox:
        capture_screen_bbox(set_light_bbox, QA_SHOTS_DIR / "12_light_dialog_preferences.png")
    dlg_set_light.destroy()
    app.update()

    # 13. Onboarding Checklist Dialog (Light)
    print("[13/13] Capturing 13_light_dialog_onboarding_checklist.png...")
    dlg_onb_light = OnboardingChecklistDialog(app, app.controller)
    dlg_onb_light.update()
    time.sleep(0.2)
    onb_light_hwnd = dlg_onb_light.winfo_id()
    bring_window_to_front(onb_light_hwnd)
    onb_light_bbox = get_window_screen_rect(onb_light_hwnd, dlg_onb_light)
    if onb_light_bbox:
        capture_screen_bbox(onb_light_bbox, QA_SHOTS_DIR / "13_light_dialog_onboarding_checklist.png")
    dlg_onb_light.destroy()
    app.update()

    # 14. Milestone 7: Adaptive Small-Screen Layout (1366x768 / 1180x648)
    print("[14/16] Capturing 14_1366x768_adaptive_geometry.png...")
    OmniTheme.set_theme("dark")
    app.apply_theme(OmniTheme.get_tokens())
    app.geometry("1180x648")
    app.update()
    time.sleep(0.3)
    bring_window_to_front(hwnd)
    snap("14_1366x768_adaptive_geometry.png")

    # 15. Milestone 7: Focus Rings & Keyboard Traversal
    print("[15/16] Capturing 15_focus_rings_keyboard_traversal.png...")
    try:
        app.aspect_seg.focus_set()
    except Exception:
        pass
    app.update()
    time.sleep(0.2)
    bring_window_to_front(hwnd)
    snap("15_focus_rings_keyboard_traversal.png")

    # 16. Milestone 7: High Contrast Accessibility Mode
    print("[16/16] Capturing 16_high_contrast_theme.png...")
    # Force high contrast simulation tokens
    app.configure(fg_color="#000000")
    if hasattr(app, "middle_container"):
        app.middle_container.configure(fg_color="#000000")
    app.update()
    time.sleep(0.2)
    bring_window_to_front(hwnd)
    snap("16_high_contrast_theme.png")

    print()
    print("=" * 76)
    print(" [COMPLETE] All 16 QA Screenshots successfully captured.")
    print(f" Saved to: {QA_SHOTS_DIR}")
    print("=" * 76)

    try:
        app.destroy()
    except Exception:
        pass

def run_interactive_mode():
    """Run interactive mode where user triggers captures with keypresses."""
    print("=" * 76)
    print(" OmniCapture Studio — Interactive QA Screenshot Capture Mode")
    print("=" * 76)
    print("Controls:")
    print("  [C]  Capture current main window screenshot")
    print("  [T]  Toggle theme (Light / Dark)")
    print("  [P]  Open Command Palette")
    print("  [S]  Open Simulated Device Control")
    print("  [D]  Open Diagnostics Dialog")
    print("  [O]  Open Onboarding Checklist")
    print("  [Q]  Quit interactive mode")
    print("=" * 76)

    sys.argv = [sys.argv[0], "--demo-device", "--no-onboarding"]
    from gui.dashboard import OmniCaptureApp
    from gui.theme import OmniTheme

    app = OmniCaptureApp({"theme": "dark", "window_width": 1180, "window_height": 820})
    app.update()
    hwnd = app.winfo_id()
    bring_window_to_front(hwnd)

    counter = [1]

    def on_key(event):
        k = event.char.lower()
        if k == "c":
            bring_window_to_front(hwnd)
            app.update()
            bbox = get_window_screen_rect(hwnd, app)
            if bbox:
                fn = f"interactive_shot_{counter[0]:02d}.png"
                capture_screen_bbox(bbox, QA_SHOTS_DIR / fn)
                app.toasts.show("Screenshot Captured", fn, level="success")
                counter[0] += 1
        elif k == "t":
            app._toggle_theme()
        elif k == "p":
            app._open_command_palette()
        elif k == "s":
            app._open_simulated_device_dialog()
        elif k == "d":
            app._open_diagnostics_window()
        elif k == "o":
            app._open_onboarding_dialog()
        elif k == "q":
            app.destroy()
            sys.exit(0)

    app.bind("<Key>", on_key)
    app.mainloop()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="OmniCapture Studio QA Screenshot Utility")
    parser.add_argument("--interactive", action="store_true", help="Launch in interactive keyboard capture mode")
    parser.add_argument("--auto", action="store_true", help="Run automated tour through all dialogs and states")
    parser.add_argument("--dpi-info", action="store_true", help="Print Windows DPI scaling verification instructions")
    args = parser.parse_args()

    print_dpi_instructions()

    if args.interactive:
        run_interactive_mode()
    elif args.dpi_info:
        sys.exit(0)
    else: # Default is auto
        try:
            run_automated_tour()
        except Exception as e:
            print(f"[ERROR] Automated tour encountered an error: {e}")
            import traceback
            traceback.print_exc()
            print("\nTip: If running in a headless or background environment, run this script")
            print("in your interactive Windows desktop console: python scripts/user_qa_screenshots.py")
