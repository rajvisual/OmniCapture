import os
import sys
import time
import datetime
from pathlib import Path
from typing import Dict, Any, Optional, Tuple

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

class RecordingManager:
    def __init__(self, recordings_dir: str, scrcpy_engine, drive_uploader, adb_manager=None):
        self.recordings_dir = Path(recordings_dir)
        self.recordings_dir.mkdir(parents=True, exist_ok=True)
        self.engine = scrcpy_engine
        self.uploader = drive_uploader
        self.adb = adb_manager

    def generate_filename(self, mode: str, fmt: str = "mp4", prefix_tag: str = "") -> Path:
        """Create a timestamped recording file path."""
        now_str = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        tag = f"_{prefix_tag}" if prefix_tag else ""
        if "camera" in mode:
            fname = f"REC_CAMERA{tag}_{now_str}.{fmt}"
        else:
            fname = f"REC_SCREEN{tag}_{now_str}.{fmt}"
        return self.recordings_dir / fname

    @staticmethod
    def format_size(bytes_num: int) -> str:
        """Format bytes into KB, MB, GB."""
        for unit in ["B", "KB", "MB", "GB", "TB"]:
            if bytes_num < 1024.0:
                return f"{bytes_num:.2f} {unit}"
            bytes_num /= 1024.0
        return f"{bytes_num:.2f} PB"

    @staticmethod
    def format_duration(seconds: float) -> str:
        """Format seconds into HH:MM:SS."""
        m, s = divmod(int(seconds), 60)
        h, m = divmod(m, 60)
        return f"{h:02d}:{m:02d}:{s:02d}"

    def record_session(
        self,
        mode: str,
        opts: Dict[str, Any],
        auto_upload: bool = False
    ) -> Tuple[Optional[Path], float, int]:
        """
        Launch unlimited recording session.
        Returns (recorded_file_path, duration_seconds, file_size_bytes).
        """
        fmt = opts.get("record_format", "mp4")
        facing = opts.get("camera_facing", "")
        file_path = self.generate_filename(mode, fmt=fmt, prefix_tag=facing.upper() if facing else "")
        opts["record_file"] = str(file_path)

        cmd = self.engine.build_command(mode, opts)

        print("\n\033[1;36m========================================================================\033[0m")
        print(f"\033[1;32m  🔴 UNLIMITED RECORDING STARTED\033[0m")
        print(f"\033[90m  Mode:\033[0m {mode.upper()}  |  \033[90mFormat:\033[0m {fmt.upper()}")
        print(f"\033[90m  Target File:\033[0m {file_path}")
        if "camera" in mode:
            print(f"\033[90m  Camera:\033[0m {opts.get('camera_facing', 'back').capitalize()} (Screen off / No app opened) | Audio: {opts.get('audio_source', 'mic')}")

        print("\n\033[1;33m  ⌨️  LIVE HOTKEYS (While window is focused):\033[0m")
        print("  \033[1m[Alt + Z]\033[0m          ⏸️  \033[93mPAUSE\033[0m video capture")
        print("  \033[1m[Alt + Shift + Z]\033[0m  ▶️  \033[92mRESUME\033[0m video capture")
        if "camera" not in mode:
            print("  \033[1m[Alt + O]\033[0m          🌑  Turn phone screen OFF (keeps recording)")
            print("  \033[1m[Alt + Shift + O]\033[0m  💡  Turn phone screen ON")
        print("  \033[1m[Alt + F]\033[0m          🖥️  Toggle Fullscreen")
        print("  \033[1m[Ctrl + C] / Close\033[0m 🛑  \033[91mSTOP\033[0m recording & upload to Google Drive")
        print("\033[1;36m========================================================================\033[0m\n")

        # In camera mode, if screen_off is requested, turn off screen via ADB
        if "camera" in mode and opts.get("screen_off") and self.adb:
            self.adb.turn_screen_off(opts.get("device_id"))

        # Run recording live
        code, duration = self.engine.run_live(cmd)

        # Inspect resulting file
        time.sleep(0.5)  # allow disk flush
        if file_path.exists() and file_path.stat().st_size > 0:
            file_size = file_path.stat().st_size
            print("\n\033[1;32m========================================================\033[0m")
            print(f"\033[1;32m  ✅ RECORDING FINISHED & SAVED LOCALLY\033[0m")
            print(f"\033[97m  File:\033[0m {file_path.name}")
            print(f"\033[97m  Path:\033[0m {file_path}")
            print(f"\033[97m  Duration:\033[0m {self.format_duration(duration)}")
            print(f"\033[97m  Size:\033[0m {self.format_size(file_size)}")
            print("\033[1;32m========================================================\033[0m\n")

            if auto_upload:
                print(f"\033[96m[Auto-Upload]\033[0m Triggering Google Drive upload...")
                ok, msg = self.uploader.upload_file(str(file_path))
                if ok:
                    print(f"\033[92m[Auto-Upload Success]\033[0m {msg}")
                else:
                    print(f"\033[91m[Auto-Upload Notice]\033[0m {msg}")

            return file_path, duration, file_size
        else:
            print(f"\n\033[91m[!] No recording saved or file was empty: {file_path}\033[0m")
            return None, duration, 0
