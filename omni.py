#!/usr/bin/env python3
"""
=============================================================================
  OmniCapture CLI - Ultimate Display & Stealth Camera Capture Suite
  Engineered on top of scrcpy 3.3.4 & ADB
=============================================================================
"""

import os
import sys
import json
import argparse
from pathlib import Path

# Ensure UTF-8 console output on Windows
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
        "scrcpy_dir": str(BASE_DIR / "bin"),
        "recordings_dir": str(BASE_DIR / "recordings"),
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
            "enabled": True,
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
    banner = r"""
 [1;36m  ██████╗ ███╗   ███╗███╗   ██╗██╗ ██████╗ █████╗ ██████╗ ████████╗██╗   ██╗██████╗ ███████╗
 ██╔═══██╗████╗ ████║████╗  ██║██║██╔════╝██╔══██╗██╔══██╗╚══██╔══╝██║   ██║██╔══██╗██╔════╝
 ██║   ██║██╔████╔██║██╔██╗ ██║██║██║     ███████║██████╔╝   ██║   ██║   ██║██████╔╝█████╗  
 ██║   ██║██║╚██╔╝██║██║╚██╗██║██║██║     ██╔══██║██╔═══╝    ██║   ██║   ██║██╔══██╗██╔══╝  
 ╚██████╔╝██║ ╚═╝ ██║██║ ╚████║██║╚██████╗██║  ██║██║        ██║   ╚██████╔╝██║  ██║███████╗
  ╚═════╝ ╚═╝     ╚═╝╚═╝  ╚═══╝╚═╝ ╚═════╝╚═╝  ╚═╝╚═╝        ╚═╝    ╚═════╝ ╚═╝  ╚═╝╚══════╝ [0m
 [90m  --- Display Mirror • Stealth Camera • Hotkey Control • Unlimited PC Recording • Drive Sync --- [0m
"""
    print(banner)

def get_system_status(adb: ADBManager, scrcpy: ScrcpyEngine) -> dict:
    devices = adb.list_devices()
    active_dev = None
    battery = {"level": "N/A", "status": "N/A", "powered": "N/A"}
    if devices:
        # Prefer USB connected device for ultra-low latency
        usb_devs = [d for d in devices if not d.get("is_wireless") and d.get("state") == "device"]
        active_dev = usb_devs[0] if usb_devs else devices[0]
        if active_dev["state"] == "device":
            battery = adb.get_battery_info(active_dev["id"])
    return {
        "devices": devices,
        "active_device": active_dev,
        "battery": battery,
        "scrcpy_ready": scrcpy.scrcpy_path.exists()
    }

def print_status_bar(status: dict):
    print("┌" + "─" * 78 + "┐")
    if not status["scrcpy_ready"]:
        print("│  \033[91m[!] SCRCPY NOT FOUND: Check path in config.json\033[0m" + " " * 31 + "│")
    elif not status["devices"]:
        print("│  \033[93m[!] NO PHONE DETECTED: Plug in USB cable & enable 'USB Debugging'\033[0m" + " " * 12 + "│")
    else:
        dev = status["active_device"]
        model = dev.get("model", "Android Device")
        dev_id = dev.get("id", "")
        conn_type = "Wi-Fi 📶" if dev.get("is_wireless") else "USB 🔌"
        batt = status["battery"]
        line = f" 📱  \033[1;32m{model}\033[0m ({dev_id}) [{conn_type}] | 🔋  \033[1;33m{batt['level']}\033[0m ({batt['status']})"
        clean_len = len(f" {model} ({dev_id}) [{conn_type}] | {batt['level']} ({batt['status']})")
        pad = max(0, 78 - clean_len - 4)
        print("│" + line + " " * pad + "│")
    print("└" + "─" * 78 + "┘")

def show_hotkeys_guide():
    print("""
\033[1;36m==============================================================================
  ⌨️  ACTIVE HOTKEYS & KEYBOARD SHORTCUTS GUIDE
==============================================================================\033[0m

  All shortcuts use \033[1;33mLeft Alt\033[0m as the shortcut modifier while the window is focused:

  \033[1m[Alt + Z]\033[0m           ⏸️  \033[93mPAUSE / Freeze\033[0m screen or camera feed
  \033[1m[Alt + Shift + Z]\033[0m   ▶️  \033[92mRESUME\033[0m screen or camera feed
  \033[1m[Alt + O]\033[0m           🌑  \033[97mTurn phone screen OFF\033[0m (keeps streaming & recording!)
  \033[1m[Alt + Shift + O]\033[0m   💡  \033[97mTurn phone screen ON\033[0m
  \033[1m[Alt + F]\033[0m           🖥️  Toggle \033[97mFullscreen\033[0m mode
  \033[1m[Alt + H]\033[0m           🏠  Press phone \033[97mHOME\033[0m button
  \033[1m[Alt + B]\033[0m           🔙  Press phone \033[97mBACK\033[0m button (or Right-Click)
  \033[1m[Alt + S]\033[0m           📑  Open \033[97mApp Switcher / Recent Apps\033[0m
  \033[1m[Alt + P]\033[0m           ⚡  Toggle \033[97mPower / Lock\033[0m button
  \033[1m[Alt + Up / Down]\033[0m   🔊  Increase / Decrease \033[97mVolume\033[0m
  \033[1m[Alt + R]\033[0m           🔄  Rotate device screen
  \033[1m[Alt + Shift + R]\033[0m   🔁  Reset video capture / encoder
  \033[1m[Ctrl + C]\033[0m / Close  🛑  \033[91mSTOP Recording\033[0m & automatically upload to Google Drive

\033[1;36m==============================================================================\033[0m
""")

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

        print("""
\033[1;37mMAIN MENU OPTIONS:\033[0m
  \033[1;36m[1]\033[0m 📱  \033[1mDisplay Mirror & Controller\033[0m     (Interactive PC control, keyboard & mouse)
  \033[1;36m[2]\033[0m 📷  \033[1mStealth Back Camera Stream\033[0m      (\033[92mNO camera app opened\033[0m, raw sensor feed)
  \033[1;36m[3]\033[0m 🤳  \033[1mStealth Front Camera Stream\033[0m     (\033[92mNO camera app opened\033[0m, selfie camera)
  \033[1;36m[4]\033[0m 🔴  \033[1mRecord Screen -> PC (Unlimited)\033[0m (Direct stream with Pause/Resume hotkeys)
  \033[1;36m[5]\033[0m 🎥  \033[1mRecord Camera -> PC (Unlimited)\033[0m (Stealth camera + mic audio -> PC)
  \033[1;36m[6]\033[0m 🔄  \033[1mDual Mode (Screen + Camera PiP)\033[0m (Display + Camera side-by-side)
  \033[1;33m[7]\033[0m ⌨️   \033[1mView Keyboard Hotkeys Guide\033[0m     (Pause, Resume, Screen Off, Stop shortcuts)
  \033[1;36m[8]\033[0m 📶  \033[1mSwitch to Wireless ADB (Wi-Fi)\033[0m  (Unplug USB and capture wirelessly!)
  \033[1;36m[9]\033[0m ☁️   \033[1mGoogle Drive Cloud Settings\033[0m     (Option A Desktop Sync / Drive API)
  \033[1;36m[10]\033[0m 🔍 \033[1mDiagnostics & Camera Details\033[0m    (List all camera IDs, resolutions, battery)
  \033[1;31m[0]\033[0m 🚪  \033[1mExit\033[0m
""")
        choice = input("\033[1;33mSelect an option [0-10]: \033[0m").strip()

        if choice == "1":
            print("\n\033[96m[+] Launching Display Mirror & Controller...\033[0m")
            in_mode = input("Input Mode: [1] Standard Touch (Default) | [2] Hardware Mouse (Xiaomi/POCO bypass): ").strip()
            use_uhid = (in_mode == "2")
            screen_off = input("Turn phone screen OFF to save battery? (y/n, default n): ").strip().lower() == "y"
            opts = {
                "device_id": dev_id,
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
            print("\n\033[96m[+] Launching Stealth Back Camera Stream...\033[0m")
            print("\033[90mNote: Mobile camera app will NOT open. Phone screen stays dark.\033[0m")
            screen_off = input("Turn phone screen OFF? (y/n, default y): ").strip().lower() != "n"
            if screen_off and dev_id:
                adb.turn_screen_off(dev_id)
            opts = {
                "device_id": dev_id,
                "camera_facing": "back",
                "audio_source": "mic"
            }
            cmd = scrcpy.build_command("camera", opts)
            scrcpy.run_live(cmd)

        elif choice == "3":
            print("\n\033[96m[+] Launching Stealth Front Camera Stream...\033[0m")
            screen_off = input("Turn phone screen OFF? (y/n, default y): ").strip().lower() != "n"
            if screen_off and dev_id:
                adb.turn_screen_off(dev_id)
            opts = {
                "device_id": dev_id,
                "camera_facing": "front",
                "audio_source": "mic"
            }
            cmd = scrcpy.build_command("camera", opts)
            scrcpy.run_live(cmd)

        elif choice == "4":
            print("\n\033[96m[+] Setup Unlimited Screen Recording\033[0m")
            auto_up = input("Auto-upload to Google Drive after recording? (y/n, default y): ").strip().lower() != "n"
            fmt = input("Format: [1] MP4 (default) | [2] MKV (crash-safe): ").strip()
            fmt_ext = "mkv" if fmt == "2" else "mp4"
            opts = {
                "device_id": dev_id,
                "record_format": fmt_ext,
                "stay_awake": True,
                "audio_source": "playback"
            }
            recorder.record_session("record_screen", opts, auto_upload=auto_up)
            input("\nPress Enter to return to menu...")

        elif choice == "5":
            print("\n\033[96m[+] Setup Unlimited Stealth Camera Recording\033[0m")
            facing_in = input("Select Camera: [1] Back (default) | [2] Front: ").strip()
            facing = "front" if facing_in == "2" else "back"
            audio_in = input("Capture Microphone Audio? (y/n, default y): ").strip().lower() != "n"
            preview_in = input("Show live preview window on PC? (y/n, default y): ").strip().lower() != "n"
            auto_up = input("Auto-upload to Google Drive after recording? (y/n, default y): ").strip().lower() != "n"
            fmt = input("Format: [1] MP4 (default) | [2] MKV (crash-safe): ").strip()
            fmt_ext = "mkv" if fmt == "2" else "mp4"

            opts = {
                "device_id": dev_id,
                "camera_facing": facing,
                "record_format": fmt_ext,
                "screen_off": True,
                "no_playback": not preview_in,
                "audio_source": "mic" if audio_in else None
            }
            recorder.record_session("record_camera", opts, auto_upload=auto_up)
            input("\nPress Enter to return to menu...")

        elif choice == "6":
            print("\n\033[96m[+] Launching Dual Mode (Screen + Camera Side-by-Side)...\033[0m")
            import subprocess
            cmd_screen = scrcpy.build_command("mirror", {"device_id": dev_id, "window_title": "OmniCapture - Phone Screen"})
            cmd_cam = scrcpy.build_command("camera", {"device_id": dev_id, "camera_facing": "back", "window_title": "OmniCapture - Camera Feed"})
            p1 = subprocess.Popen(cmd_screen)
            p2 = subprocess.Popen(cmd_cam)
            p1.wait()
            p2.wait()

        elif choice == "7":
            show_hotkeys_guide()
            input("Press Enter to return to menu...")

        elif choice == "8":
            print("\n\033[96m[+] Setting up Wireless ADB...\033[0m")
            ok, msg = adb.enable_wireless(dev_id)
            if ok:
                print(f"\033[92m[✓] {msg}\033[0m")
            else:
                print(f"\033[91m[✗] {msg}\033[0m")
            input("\nPress Enter to continue...")

        elif choice == "9":
            drive_menu(cfg, uploader)

        elif choice == "10":
            show_diagnostics(adb, scrcpy, dev_id)
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

def show_diagnostics(adb: ADBManager, scrcpy: ScrcpyEngine, dev_id: str):
    print("\n\033[1;36m=== DEVICE DIAGNOSTICS & HARDWARE CAPABILITIES ===\033[0m\n")
    if not dev_id:
        print("\033[91m[!] No device connected. Connect your phone via USB first.\033[0m")
        return
    print("\033[1;33m[1] Battery & Power:\033[0m")
    batt = adb.get_battery_info(dev_id)
    print(f"  Level:   {batt['level']}")
    print(f"  Status:  {batt['status']}")
    print(f"  Powered: {batt['powered']}\n")

    print("\033[1;33m[2] Wi-Fi IP Address:\033[0m")
    ip = adb.get_wifi_ip(dev_id)
    print(f"  IP: {ip or 'Not found / Wi-Fi disconnected'}\n")

    print("\033[1;33m[3] Camera Sensors (Camera2 API):\033[0m")
    cams = scrcpy.query_cameras(dev_id)
    print(cams)

    print("\033[1;33m[4] Supported Camera Resolutions:\033[0m")
    sizes = scrcpy.query_camera_sizes(dev_id)
    print(sizes)

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="OmniCapture - Display & Stealth Camera Capture Suite")
    subparsers = parser.add_subparsers(dest="command")

    # Command: mirror
    p_mirror = subparsers.add_parser("mirror", help="Mirror phone display with PC control")
    p_mirror.add_argument("--screen-off", action="store_true", help="Turn phone screen off")
    p_mirror.add_argument("--uhid", action="store_true", help="Hardware mouse/keyboard simulation (bypasses Xiaomi/POCO lock)")
    p_mirror.add_argument("--device", help="Specific device ID")

    # Command: camera
    p_cam = subparsers.add_parser("camera", help="Stream camera without opening mobile camera app")
    p_cam.add_argument("--facing", choices=["back", "front", "external"], default="back", help="Camera facing")
    p_cam.add_argument("--device", help="Specific device ID")
    p_cam.add_argument("--size", help="Resolution (e.g. 1920x1080)")
    p_cam.add_argument("--fps", type=int, default=30, help="Capture frame rate")

    # Command: record
    p_rec = subparsers.add_parser("record", help="Record display or camera directly to PC")
    p_rec.add_argument("source", choices=["screen", "camera"], help="What to record")
    p_rec.add_argument("--facing", choices=["back", "front"], default="back", help="Camera facing (if source=camera)")
    p_rec.add_argument("--format", choices=["mp4", "mkv"], default="mp4", help="Video container format")
    p_rec.add_argument("--upload", action="store_true", help="Auto-upload to Google Drive when finished")
    p_rec.add_argument("--no-playback", action="store_true", help="Record silently without opening window on PC")

    # Command: hotkeys
    subparsers.add_parser("hotkeys", help="Display all active keyboard shortcuts and hotkeys")

    # Command: wireless
    subparsers.add_parser("wireless", help="Switch connected phone to wireless Wi-Fi ADB")

    # Command: upload
    p_up = subparsers.add_parser("upload", help="Upload a video to Google Drive")
    p_up.add_argument("file", help="Path to video file")

    # Command: drive-setup
    subparsers.add_parser("drive-setup", help="Configure Google Drive Auto-Upload settings")

    # Command: info
    subparsers.add_parser("info", help="Show connected device and camera diagnostics")

    return parser

def main():
    cfg = load_config()
    adb = ADBManager(cfg.get("scrcpy_dir", ""))
    scrcpy = ScrcpyEngine(cfg.get("scrcpy_dir", ""))
    uploader = DriveUploader(cfg)
    recorder = RecordingManager(cfg.get("recordings_dir", str(BASE_DIR / "recordings")), scrcpy, uploader, adb)

    parser = build_parser()
    args = parser.parse_args()

    # Auto-resolve target device if not explicitly provided
    target_dev = getattr(args, "device", None)
    if not target_dev and args.command:
        devices = adb.list_devices()
        if devices:
            usb_devs = [d for d in devices if not d.get("is_wireless") and d.get("state") == "device"]
            target_dev = usb_devs[0]["id"] if usb_devs else devices[0]["id"]

    if not args.command:
        # Launch interactive TUI
        interactive_menu(cfg, adb, scrcpy, recorder, uploader)
    elif args.command == "hotkeys":
        show_hotkeys_guide()
    elif args.command == "mirror":
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
        if target_dev:
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
        recorder.record_session(mode, opts, auto_upload=args.upload)
    elif args.command == "wireless":
        ok, msg = adb.enable_wireless()
        print(msg)
    elif args.command == "upload":
        ok, msg = uploader.upload_file(args.file)
        print(msg)
    elif args.command == "drive-setup":
        drive_menu(cfg, uploader)
    elif args.command == "info":
        devices = adb.list_devices()
        dev_id = devices[0]["id"] if devices else None
        show_diagnostics(adb, scrcpy, dev_id)

if __name__ == "__main__":
    main()
