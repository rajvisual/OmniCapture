import os
import sys
import json
import time
import argparse
import subprocess
from pathlib import Path
from typing import Optional, Dict, Any, Tuple

# Enable UTF-8 encoding on Windows terminal
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

# Add project root to sys.path
BASE_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE_DIR))

from core.adb_manager import ADBManager
from core.scrcpy_engine import ScrcpyEngine
from core.recorder import RecordingManager
from core.drive_uploader import DriveUploader

CONFIG_PATH = BASE_DIR / "config.json"

def load_config() -> dict:
    default_cfg = {
        "scrcpy_dir": "bin",
        "recordings_dir": "recordings",
        "default_record_format": "mp4",
        "default_camera_facing": "back",
        "default_camera_fps": 30,
        "default_camera_size": "",
        "max_size": 1200,
        "video_bit_rate": "8M",
        "max_fps": 60,
        "screen_off_during_capture": True,
        "stay_awake": False,
        "audio_source": "mic",
        "google_drive": {
            "enabled": False,
            "method": "desktop",
            "folder_id": "",
            "credentials_file": "client_secrets.json",
            "token_file": "drive_token.json",
            "desktop_sync_path": ""
        }
    }
    if CONFIG_PATH.exists():
        try:
            with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                user_cfg = json.load(f)
                default_cfg.update(user_cfg)
        except Exception:
            pass
    return default_cfg

def save_config(cfg: dict):
    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(cfg, f, indent=2)

def print_banner():
    print("OmniCapture 1.2.0")
    print("Android & PC Desktop Capture Suite\n")

def get_system_status(adb: ADBManager, scrcpy: ScrcpyEngine) -> dict:
    devices = adb.list_devices()
    active_dev = None
    battery = {"level": "N/A", "status": "N/A", "powered": "N/A"}
    if devices:
        # Prefer ready USB connected device for ultra-low latency
        usb_devs = [d for d in devices if not d.get("is_wireless") and d.get("state") == "device"]
        active_dev = usb_devs[0] if usb_devs else devices[0]
        if active_dev.get("state") == "device":
            battery = adb.get_battery_info(active_dev["id"])
    return {
        "devices": devices,
        "active_device": active_dev,
        "battery": battery,
        "scrcpy_ready": scrcpy.scrcpy_path.exists()
    }

def resolve_target_device(adb: ADBManager, explicit_id: Optional[str] = None, interactive: bool = False) -> Optional[str]:
    """
    Resolve the intended target Android device.
    If multiple devices are detected and interactive=True, prompts the user to select.
    Otherwise, auto-selects the first authorized USB device, or first ready device.
    """
    devices = adb.list_devices()
    if not devices:
        return None

    if explicit_id:
        for d in devices:
            if d["id"] == explicit_id:
                return explicit_id
        return explicit_id

    if len(devices) == 1:
        return devices[0]["id"]

    # Multiple devices attached
    if interactive:
        print("\n\033[1;33m[!] Multiple Android devices detected:\033[0m")
        for i, d in enumerate(devices, 1):
            conn = "Wi-Fi 📶" if d["is_wireless"] else "USB 🔌"
            state = f"\033[92m[{d['state'].upper()}]\033[0m" if d['state'] == "device" else f"\033[91m[{d['state'].upper()}]\033[0m"
            print(f"  [{i}] {d['model']} ({d['id']}) - {conn} {state}")
        sel = input(f"Select target device [1-{len(devices)}, default 1]: ").strip()
        try:
            idx = int(sel) - 1
            if 0 <= idx < len(devices):
                return devices[idx]["id"]
        except Exception:
            pass

    # Non-interactive fallback: prioritize ready USB device
    ready_usb = [d for d in devices if not d.get("is_wireless") and d.get("state") == "device"]
    if ready_usb:
        return ready_usb[0]["id"]

    ready_any = [d for d in devices if d.get("state") == "device"]
    if ready_any:
        return ready_any[0]["id"]

    return devices[0]["id"]

def check_device_ready_interactive(adb: ADBManager, dev_id: Optional[str]) -> Optional[str]:
    """
    Run preflight check on target device before launching interactive operations.
    Returns resolved device_id if ready, or None if unavailable/unauthorized.
    """
    check = adb.preflight_check(dev_id)
    if check["status"] != "DEVICE CONNECTED":
        adb.print_preflight_card(check)
        input("\033[90mPress Enter to return to main menu...\033[0m")
        return None
    return check["device_id"]

def print_status_bar(status: dict):
    if not status["scrcpy_ready"]:
        print("Status: scrcpy not found in bin/ or system PATH\n")
    elif not status["devices"]:
        print("Device: No device detected (connect via USB with USB Debugging enabled)\n")
    else:
        dev = status["active_device"]
        model = dev.get("model", "Android Device")
        dev_id = dev.get("id", "")
        conn_type = "Wi-Fi" if dev.get("is_wireless") else "USB"
        state = dev.get("state", "unknown")

        if state == "unauthorized":
            print(f"Device: {model} ({dev_id}) — unauthorized (unlock phone and allow debugging)\n")
        elif state == "offline":
            print(f"Device: {model} ({dev_id}) — offline (reconnect USB cable)\n")
        else:
            batt = status["battery"]
            b_str = f" · Battery {batt['level']}" if batt.get("level") and batt["level"] != "N/A" else ""
            print(f"Device: ● {model} ({conn_type}){b_str}\n")

def show_hotkeys_guide():
    print("""Shortcuts (Left Alt + key when window is focused):
  Alt + Z          Pause stream
  Alt + Shift + Z  Resume stream
  Alt + O          Turn phone screen off
  Alt + Shift + O  Turn phone screen on
  Alt + F          Toggle fullscreen
  Alt + H          Home button
  Alt + B          Back button
  Alt + S          Recent apps
  Alt + P          Power button
  Alt + Up / Down  Volume up / down
  Alt + R          Rotate display
  Ctrl + C         Stop recording
""")

def launch_gui_app(cfg: dict):
    """Launch the CustomTkinter Modern Windows 11 GUI Dashboard."""
    try:
        from gui.dashboard import OmniCaptureApp
        app = OmniCaptureApp(cfg)
        app.mainloop()
    except Exception as e:
        print(f"\n\033[1;31m[!] Error launching GUI dashboard: {e}\033[0m")
        print("\033[90mEnsure customtkinter, pillow, and pystray are installed:\033[0m")
        print("  pip install -r requirements.txt\n")

def interactive_menu(
    cfg: dict,
    adb: ADBManager,
    scrcpy: ScrcpyEngine,
    recorder: RecordingManager,
    uploader: DriveUploader
):
    while True:
        os.system("cls" if os.name == "nt" else "clear")
        print_banner()
        status = get_system_status(adb, scrcpy)
        print_status_bar(status)

        dev_id = status["active_device"]["id"] if status["active_device"] else None

        print("""Actions:
  [g] Launch Desktop GUI Dashboard
  [1] Display Mirror & PC Controller
  [2] Back Camera Stream
  [3] Front Camera Stream
  [4] Record Mobile Screen
  [5] Record Mobile Camera
  [6] Dual Live Preview
  [7] Dual Simultaneous Recording
  [8] Keyboard Shortcuts
  [9] Switch to Wi-Fi ADB
  [10] Google Drive Cloud Settings
  [11] Diagnostics
  [0] Exit
""")
        choice = input("Select an option [0-11, g]: ").strip().lower()

        if choice in ("g", "gui"):
            launch_gui_app(cfg)
            continue

        if choice == "1":
            target = check_device_ready_interactive(adb, dev_id)
            if not target:
                continue
            print("\n\033[96m[+] Launching Display Mirror & Controller...\033[0m")
            in_mode = input("Input Mode: [1] Standard Touch (Default) | [2] Hardware Mouse (Xiaomi/POCO bypass): ").strip()
            use_uhid = (in_mode == "2")
            screen_off = input("Turn phone screen OFF to save battery? (y/n, default n): ").strip().lower() == "y"
            opts = {
                "device_id": target,
                "screen_off": screen_off,
                "stay_awake": cfg.get("stay_awake", False),
                "uhid": use_uhid,
                "max_size": cfg.get("max_size", 1200),
                "bit_rate": cfg.get("video_bit_rate", "8M"),
                "max_fps": cfg.get("max_fps", 60)
            }
            cmd = scrcpy.build_command("mirror", opts)
            scrcpy.run_live(cmd)

        elif choice == "2":
            target = check_device_ready_interactive(adb, dev_id)
            if not target:
                continue
            print("\n\033[96m[+] Launching Stealth Back Camera Stream...\033[0m")
            print("\033[90mNote: Mobile camera app will NOT open. Phone screen stays dark.\033[0m")
            screen_off = input("Turn phone screen OFF? (y/n, default y): ").strip().lower() != "n"
            if screen_off:
                adb.turn_screen_off(target)
            opts = {
                "device_id": target,
                "camera_facing": "back",
                "audio_source": "mic"
            }
            cmd = scrcpy.build_command("camera", opts)
            scrcpy.run_live(cmd)

        elif choice == "3":
            target = check_device_ready_interactive(adb, dev_id)
            if not target:
                continue
            print("\n\033[96m[+] Launching Stealth Front Camera Stream...\033[0m")
            screen_off = input("Turn phone screen OFF? (y/n, default y): ").strip().lower() != "n"
            if screen_off:
                adb.turn_screen_off(target)
            opts = {
                "device_id": target,
                "camera_facing": "front",
                "audio_source": "mic"
            }
            cmd = scrcpy.build_command("camera", opts)
            scrcpy.run_live(cmd)

        elif choice == "4":
            target = check_device_ready_interactive(adb, dev_id)
            if not target:
                continue
            print("\n\033[96m[+] Setup Unlimited Screen Recording\033[0m")
            auto_up = input("Auto-upload to Google Drive after recording? (y/n, default y): ").strip().lower() != "n"
            fmt = input("Format: [1] MP4 (default) | [2] MKV (crash-safe): ").strip()
            fmt_ext = "mkv" if fmt == "2" else "mp4"
            opts = {
                "device_id": target,
                "record_format": fmt_ext,
                "stay_awake": True,
                "audio_source": "playback"
            }
            recorder.record_session("record_screen", opts, auto_upload=auto_up)
            input("\nPress Enter to return to menu...")

        elif choice == "5":
            target = check_device_ready_interactive(adb, dev_id)
            if not target:
                continue
            print("\n\033[96m[+] Setup Unlimited Stealth Camera Recording\033[0m")
            facing_in = input("Select Camera: [1] Back (default) | [2] Front: ").strip()
            facing = "front" if facing_in == "2" else "back"
            audio_in = input("Capture Microphone Audio? (y/n, default y): ").strip().lower() != "n"
            preview_in = input("Show live preview window on PC? (y/n, default y): ").strip().lower() != "n"
            auto_up = input("Auto-upload to Google Drive after recording? (y/n, default y): ").strip().lower() != "n"
            fmt = input("Format: [1] MP4 (default) | [2] MKV (crash-safe): ").strip()
            fmt_ext = "mkv" if fmt == "2" else "mp4"

            opts = {
                "device_id": target,
                "camera_facing": facing,
                "record_format": fmt_ext,
                "screen_off": True,
                "no_playback": not preview_in,
                "audio_source": "mic" if audio_in else None
            }
            recorder.record_session("record_camera", opts, auto_upload=auto_up)
            input("\nPress Enter to return to menu...")

        elif choice == "6":
            target = check_device_ready_interactive(adb, dev_id)
            if not target:
                continue
            print("\n\033[96m[+] Launching Dual Live Preview (Screen + Camera Side-by-Side)...\033[0m")
            cmd_screen = scrcpy.build_command("mirror", {"device_id": target, "window_title": "OmniCapture - Phone Screen"})
            cmd_cam = scrcpy.build_command("camera", {"device_id": target, "camera_facing": "back", "window_title": "OmniCapture - Camera Feed"})
            env = scrcpy.get_scrcpy_env(adb.adb_path)
            p1 = subprocess.Popen(cmd_screen, env=env)
            p2 = subprocess.Popen(cmd_cam, env=env)
            p1.wait()
            p2.wait()

        elif choice == "7":
            # Dual Simultaneous Recording (PC Screen + Mobile Camera)
            if not recorder.pc_recorder.is_available():
                print("\n\033[1;31m" + "=" * 70)
                print("  ❌ DUAL RECORDING ERROR: FFMPEG IS REQUIRED FOR PC SCREEN CAPTURE")
                print("=" * 70 + "\033[0m")
                print("  FFmpeg was not found in your system PATH or bin/ folder.")
                print("  Install via PowerShell: \033[1;33mwinget install Gyan.FFmpeg\033[0m\n")
                input("\033[90mPress Enter to return to menu...\033[0m")
                continue

            target = check_device_ready_interactive(adb, dev_id)
            if not target:
                continue

            print("\n\033[1;36m========================================================================\033[0m")
            print("  🎬 \033[1mSETUP DUAL SIMULTANEOUS RECORDING (PC Screen + Mobile Camera)\033[0m")
            print("  \033[90mBoth feeds record concurrently into 2 separate files in recordings/\033[0m")
            print("\033[1;36m========================================================================\033[0m\n")

            facing_in = input("Select Mobile Camera: [1] Back (default) | [2] Front: ").strip()
            facing = "front" if facing_in == "2" else "back"

            pc_fps_in = input("PC Screen Capture FPS [default 30, max 60]: ").strip()
            pc_fps = int(pc_fps_in) if pc_fps_in.isdigit() and int(pc_fps_in) > 0 else 30

            cam_fps_in = input("Mobile Camera FPS [default 30]: ").strip()
            cam_fps = int(cam_fps_in) if cam_fps_in.isdigit() and int(cam_fps_in) > 0 else 30

            preview_in = input("Show live mobile camera preview window on PC? (y/n, default y): ").strip().lower() != "n"
            auto_up = input("Auto-upload both recordings to Google Drive after recording? (y/n, default n): ").strip().lower() == "y"
            fmt = input("Format: [1] MP4 (default) | [2] MKV (crash-safe): ").strip()
            fmt_ext = "mkv" if fmt == "2" else "mp4"

            dual_opts = {
                "device_id": target,
                "camera_facing": facing,
                "record_format": fmt_ext,
                "pc_fps": pc_fps,
                "camera_fps": cam_fps,
                "screen_off": True,
                "no_playback": not preview_in,
                "audio_source": "mic"
            }
            recorder.record_dual_pc_and_mobile_camera(dual_opts, auto_upload=auto_up)
            input("\nPress Enter to return to menu...")

        elif choice == "8":
            show_hotkeys_guide()
            input("Press Enter to return to menu...")

        elif choice == "9":
            target = check_device_ready_interactive(adb, dev_id)
            if not target:
                continue
            print(f"\n\033[96m[+] Setting up Wireless ADB for [{target}]...\033[0m")
            ok, msg = adb.enable_wireless(target)
            if ok:
                print(f"\033[92m[✓] {msg}\033[0m")
            else:
                print(f"\033[91m[✗] {msg}\033[0m")
            input("\nPress Enter to continue...")

        elif choice == "10":
            drive_menu(cfg, uploader)

        elif choice == "11":
            show_diagnostics(adb, scrcpy, dev_id, recorder.pc_recorder)
            input("\nPress Enter to return to menu...")

        elif choice == "0":
            print("\n\033[93mGoodbye! Exiting OmniCapture.\033[0m")
            sys.exit(0)

def drive_menu(cfg: dict, uploader: DriveUploader):
    while True:
        os.system("cls" if os.name == "nt" else "clear")
        print("\n\033[1;36m=== GOOGLE DRIVE CLOUD SETTINGS ===\033[0m")
        drive_cfg = cfg.get("google_drive", {})
        method = drive_cfg.get("method", "desktop")
        desktop_path = uploader.desktop_sync_path
        print(f"  Current Method:      \033[1m{method.upper()}\033[0m")
        print(f"  Desktop Drive Path:  \033[1m{desktop_path or 'Not Detected (e.g. G:\\My Drive)'}\033[0m")
        print(f"  OAuth Credentials:   \033[1m{drive_cfg.get('credentials_file', 'client_secrets.json')}\033[0m")
        print(f"  Token Saved:         \033[1m{'Yes' if Path(BASE_DIR / drive_cfg.get('token_file', 'drive_token.json')).exists() else 'No'}\033[0m")
        print("""
  [1] Switch Method: Google Drive Desktop Sync vs Google Drive API
  [2] Set Custom Google Drive / Sync Folder Path
  [3] Authenticate with Google Drive API (OAuth)
  [4] Test Upload a file
  [0] Return to Main Menu
""")
        c = input("\033[1;33mSelect option [0-4]: \033[0m").strip()
        if c == "1":
            new_m = "desktop" if method == "api" else "api"
            drive_cfg["method"] = new_m
            cfg["google_drive"] = drive_cfg
            save_config(cfg)
            print(f"\033[92m[✓] Switched method to: {new_m}\033[0m")
            input("Press Enter...")
        elif c == "2":
            p = input("Enter full path to your Google Drive folder: ").strip()
            if Path(p).exists():
                drive_cfg["desktop_sync_path"] = p
                cfg["google_drive"] = drive_cfg
                save_config(cfg)
                uploader.desktop_sync_path = Path(p)
                print("\033[92m[✓] Sync path updated!\033[0m")
            else:
                print("\033[91m[!] Path does not exist.\033[0m")
            input("Press Enter...")
        elif c == "3":
            print("\n\033[96mAuthenticating with Google Drive API...\033[0m")
            test_file = BASE_DIR / "auth_test.tmp"
            test_file.write_text("OmniCapture Google Drive Auth")
            ok, msg = uploader._upload_via_api(test_file)
            if test_file.exists():
                test_file.unlink()
            if ok:
                print(f"\033[92m[✓] Authentication successful!\033[0m")
            else:
                print(f"\033[91m[!] Authentication failed: {msg}\033[0m")
            input("Press Enter...")
        elif c == "4":
            test_p = input("Enter path to file to upload: ").strip()
            if test_p:
                ok, msg = uploader.upload_file(test_p)
                print(f"Result: {msg}")
            input("Press Enter...")
        elif c == "0":
            break

def show_diagnostics(adb: ADBManager, scrcpy: ScrcpyEngine, dev_id: Optional[str] = None, pc_recorder: Optional[Any] = None):
    print("\n\033[1;36m=== SYSTEM, RUNTIME & HARDWARE DIAGNOSTICS ===\033[0m\n")

    # [1] Software Binaries
    print("\033[1;33m[1] Runtime Binaries & Engines:\033[0m")
    adb_ver = adb.get_adb_version() or "Not detected"
    print(f"  ADB Binary:    {adb.adb_path} ({adb_ver})")
    print(f"  Scrcpy Engine: {scrcpy.scrcpy_path}")
    if pc_recorder:
        ff_ver = pc_recorder.get_ffmpeg_version() or "Not detected"
        print(f"  FFmpeg Engine: {pc_recorder.ffmpeg_path or 'NOT FOUND'} ({ff_ver})")

    # [2] Preflight Check on Android Device
    print("\n\033[1;33m[2] Android Device Preflight Check:\033[0m")
    check = adb.preflight_check(dev_id)
    target_id = check.get("device_id")
    status_str = check.get("status")

    if status_str == "DEVICE CONNECTED":
        props = check.get("properties", {})
        print(f"  Status:       \033[1;32m{status_str}\033[0m")
        print(f"  Serial ID:    {target_id}")
        print(f"  Model:        {props.get('brand', '').upper()} {props.get('model', 'Android Device')}")
        print(f"  Android OS:   Version {props.get('android_version', 'N/A')} (SDK {props.get('sdk_version', 'N/A')})")
        print(f"  Connection:   {'Wi-Fi (TCP/IP)' if check.get('is_wireless') else 'USB Cable'}")

        # Battery
        batt = adb.get_battery_info(target_id)
        print(f"  Battery:      {batt['level']} ({batt['status']}, Powered: {batt['powered']})")

        # IP
        ip = adb.get_wifi_ip(target_id)
        print(f"  Wi-Fi IP:     {ip or 'Not found / Wi-Fi disconnected'}")

        # [3] Camera Sensors
        print("\n\033[1;33m[3] Camera Sensors (Camera2 API):\033[0m")
        cams = scrcpy.query_cameras(target_id)
        print(cams)

        # [4] Camera Resolutions
        print("\n\033[1;33m[4] Supported Camera Resolutions:\033[0m")
        sizes = scrcpy.query_camera_sizes(target_id)
        print(sizes)
    else:
        adb.print_preflight_card(check)

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="OmniCapture - Display, Stealth Camera & Dual PC Recording Suite")
    parser.add_argument("--gui", action="store_true", help="Launch the modern Windows 11 GUI dashboard")
    subparsers = parser.add_subparsers(dest="command")

    # Command: gui
    subparsers.add_parser("gui", help="Launch the modern Windows 11 GUI dashboard")

    # Command: mirror
    p_mirror = subparsers.add_parser("mirror", help="Mirror phone display with interactive PC control")
    p_mirror.add_argument("--screen-off", action="store_true", help="Turn phone screen off")
    p_mirror.add_argument("--uhid", action="store_true", help="Hardware mouse/keyboard simulation (bypasses Xiaomi/POCO lock)")
    p_mirror.add_argument("--device", help="Specific device ID")

    # Command: camera
    p_cam = subparsers.add_parser("camera", help="Stream camera without opening mobile camera app")
    p_cam.add_argument("--facing", choices=["back", "front", "external"], default="back", help="Camera facing (default: back)")
    p_cam.add_argument("--device", help="Specific device ID")
    p_cam.add_argument("--size", help="Resolution (e.g. 1920x1080)")
    p_cam.add_argument("--fps", type=int, default=30, help="Capture frame rate")

    # Command: record
    p_rec = subparsers.add_parser("record", help="Record display or camera directly to PC")
    p_rec.add_argument("source", choices=["screen", "camera", "dual"], help="What to record: screen (mobile), camera (mobile), or dual (PC screen + mobile camera)")
    p_rec.add_argument("--facing", choices=["back", "front"], default="back", help="Camera facing (if source=camera or dual)")
    p_rec.add_argument("--format", choices=["mp4", "mkv"], default="mp4", help="Video container format")
    p_rec.add_argument("--upload", action="store_true", help="Auto-upload to Google Drive when finished")
    p_rec.add_argument("--no-playback", action="store_true", help="Record silently without opening preview window on PC")
    p_rec.add_argument("--pc-fps", type=int, default=30, help="PC screen frame rate (for source=dual, default: 30)")
    p_rec.add_argument("--camera-fps", type=int, default=30, help="Mobile camera frame rate (default: 30)")
    p_rec.add_argument("--camera-size", help="Mobile camera resolution (e.g. 1920x1080)")
    p_rec.add_argument("--device", help="Specific device ID")

    # Command: dual-record
    p_dual = subparsers.add_parser("dual-record", help="Record PC screen and mobile camera simultaneously to 2 separate files")
    p_dual.add_argument("--facing", choices=["back", "front"], default="back", help="Mobile camera facing (default: back)")
    p_dual.add_argument("--format", choices=["mp4", "mkv"], default="mp4", help="Video container format (default: mp4)")
    p_dual.add_argument("--pc-fps", type=int, default=30, help="PC screen capture frame rate (default: 30)")
    p_dual.add_argument("--camera-fps", type=int, default=30, help="Mobile camera frame rate (default: 30)")
    p_dual.add_argument("--camera-size", help="Mobile camera resolution (e.g. 1920x1080)")
    p_dual.add_argument("--no-camera-playback", action="store_true", help="Record mobile camera silently without preview window")
    p_dual.add_argument("--upload", action="store_true", help="Auto-upload both recordings to Google Drive when finished")
    p_dual.add_argument("--device", help="Specific mobile device ID")

    # Command: hotkeys
    subparsers.add_parser("hotkeys", help="Display all active keyboard shortcuts and hotkeys")

    # Command: wireless
    p_wire = subparsers.add_parser("wireless", help="Switch connected phone to wireless Wi-Fi ADB")
    p_wire.add_argument("--device", help="Specific device ID")

    # Command: upload
    p_up = subparsers.add_parser("upload", help="Upload a video to Google Drive")
    p_up.add_argument("file", help="Path to video file")

    # Command: drive-setup
    subparsers.add_parser("drive-setup", help="Configure Google Drive Auto-Upload settings")

    # Command: info
    p_info = subparsers.add_parser("info", help="Show connected device and camera diagnostics")
    p_info.add_argument("--device", help="Specific device ID")

    return parser

def main():
    cfg = load_config()
    adb = ADBManager(cfg.get("scrcpy_dir", "bin"))
    scrcpy = ScrcpyEngine(cfg.get("scrcpy_dir", "bin"))
    uploader = DriveUploader(cfg)
    recorder = RecordingManager(cfg.get("recordings_dir", str(BASE_DIR / "recordings")), scrcpy, uploader, adb)

    parser = build_parser()
    args = parser.parse_args()

    # If --gui flag or gui subcommand, launch GUI dashboard
    if getattr(args, "gui", False) or args.command == "gui":
        launch_gui_app(cfg)
        return

    # If no command, run interactive menu
    if not args.command:
        interactive_menu(cfg, adb, scrcpy, recorder, uploader)
        return

    # CLI Command Dispatch
    if args.command == "hotkeys":
        show_hotkeys_guide()
        return

    if args.command == "upload":
        ok, msg = uploader.upload_file(args.file)
        print(msg)
        sys.exit(0 if ok else 1)

    if args.command == "drive-setup":
        drive_menu(cfg, uploader)
        return

    # Commands requiring target Android device
    target_dev = resolve_target_device(adb, getattr(args, "device", None), interactive=False)

    if args.command == "info":
        show_diagnostics(adb, scrcpy, target_dev, recorder.pc_recorder)
        return

    if args.command == "wireless":
        check = adb.preflight_check(target_dev)
        if check["status"] != "DEVICE CONNECTED":
            adb.print_preflight_card(check)
            sys.exit(1)
        ok, msg = adb.enable_wireless(check["device_id"])
        print(msg)
        sys.exit(0 if ok else 1)

    if args.command in ("dual-record",) or (args.command == "record" and args.source == "dual"):
        dual_opts = {
            "device_id": target_dev,
            "camera_facing": getattr(args, "facing", "back"),
            "camera_size": getattr(args, "camera_size", None),
            "camera_fps": getattr(args, "camera_fps", 30),
            "pc_fps": getattr(args, "pc_fps", 30),
            "record_format": getattr(args, "format", "mp4"),
            "no_playback": getattr(args, "no_camera_playback", False) or getattr(args, "no_playback", False),
            "screen_off": True,
            "audio_source": "mic"
        }
        res = recorder.record_dual_pc_and_mobile_camera(dual_opts, auto_upload=args.upload)
        sys.exit(0 if res.get("success") else 1)

    # Preflight check for mirror, camera, record
    check = adb.preflight_check(target_dev)
    if check["status"] != "DEVICE CONNECTED":
        adb.print_preflight_card(check)
        sys.exit(1)
    target_dev = check["device_id"]

    if args.command == "mirror":
        opts = {
            "device_id": target_dev,
            "screen_off": args.screen_off,
            "stay_awake": False,
            "uhid": args.uhid,
            "max_size": cfg.get("max_size", 1200),
            "bit_rate": cfg.get("video_bit_rate", "8M"),
            "max_fps": cfg.get("max_fps", 60)
        }
        cmd = scrcpy.build_command("mirror", opts)
        scrcpy.run_live(cmd)

    elif args.command == "camera":
        adb.turn_screen_off(target_dev)
        opts = {
            "device_id": target_dev,
            "camera_facing": args.facing,
            "camera_size": args.size,
            "camera_fps": args.fps,
            "audio_source": "mic"
        }
        cmd = scrcpy.build_command("camera", opts)
        scrcpy.run_live(cmd)

    elif args.command == "record":
        mode = "record_camera" if args.source == "camera" else "record_screen"
        opts = {
            "device_id": target_dev,
            "camera_facing": args.facing,
            "record_format": args.format,
            "screen_off": True if args.source == "camera" else False,
            "no_playback": args.no_playback,
            "stay_awake": True if args.source == "screen" else False,
            "audio_source": "mic" if args.source == "camera" else "playback"
        }
        file_path, dur, sz = recorder.record_session(mode, opts, auto_upload=args.upload)
        sys.exit(0 if file_path else 1)

if __name__ == "__main__":
    main()
