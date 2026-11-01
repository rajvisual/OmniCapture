import os
import sys
import time
import datetime
import subprocess
import threading
from pathlib import Path
from typing import Dict, Any, Optional, Tuple

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

from core.pc_recorder import PCRecorder

class RecordingManager:
    def __init__(self, recordings_dir: str, scrcpy_engine, drive_uploader, adb_manager=None, pc_recorder=None):
        self.recordings_dir = Path(recordings_dir)
        self.recordings_dir.mkdir(parents=True, exist_ok=True)
        self.engine = scrcpy_engine
        self.uploader = drive_uploader
        self.adb = adb_manager

        bin_dir = getattr(scrcpy_engine, "scrcpy_dir", None)
        self.pc_recorder = pc_recorder or PCRecorder(bin_dir=bin_dir)

    def generate_filename(self, mode: str, fmt: str = "mp4", prefix_tag: str = "") -> Path:
        """Create a timestamped recording file path."""
        now_str = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        tag = f"_{prefix_tag}" if prefix_tag else ""
        if "camera" in mode:
            fname = f"REC_CAMERA{tag}_{now_str}.{fmt}"
        else:
            fname = f"REC_SCREEN{tag}_{now_str}.{fmt}"
        return self.recordings_dir / fname

    def generate_dual_filenames(self, fmt: str = "mp4") -> Tuple[Path, Path]:
        """Create paired timestamped file paths for PC Screen and Mobile Camera."""
        now_str = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        pc_path = self.recordings_dir / f"REC_PC_SCREEN_{now_str}.{fmt}"
        cam_path = self.recordings_dir / f"REC_MOBILE_CAMERA_{now_str}.{fmt}"
        return pc_path, cam_path

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
        Launch unlimited recording session (mobile screen or mobile camera).
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

    def record_dual_pc_and_mobile_camera(
        self,
        opts: Dict[str, Any],
        auto_upload: bool = False
    ) -> Dict[str, Any]:
        """
        Simultaneously records:
          1. Windows PC Screen -> REC_PC_SCREEN_YYYYMMDD_HHMMSS.mp4 (via FFmpeg)
          2. Android Mobile Camera -> REC_MOBILE_CAMERA_YYYYMMDD_HHMMSS.mp4 (via scrcpy)
        Saves both as separate, high-quality video files simultaneously.
        """
        if not self.pc_recorder.is_available():
            print("\n\033[1;31m========================================================================\033[0m")
            print("\033[1;31m  [ERROR] FFmpeg is required for PC screen capture but was not found.\033[0m")
            print("  Please install FFmpeg using PowerShell:")
            print("    \033[1;33mwinget install Gyan.FFmpeg\033[0m")
            print("  Or place ffmpeg.exe inside the bin/ directory.")
            print("\033[1;31m========================================================================\033[0m\n")
            return {"success": False, "error": "FFmpeg not found"}

        fmt = opts.get("record_format", "mp4")
        pc_file, cam_file = self.generate_dual_filenames(fmt=fmt)

        # Build Mobile Camera scrcpy options
        cam_opts = {
            "device_id": opts.get("device_id"),
            "camera_facing": opts.get("camera_facing", "back"),
            "camera_size": opts.get("camera_size"),
            "camera_fps": opts.get("camera_fps", 30),
            "record_file": str(cam_file),
            "record_format": fmt,
            "audio_source": opts.get("audio_source", "mic"),
            "no_playback": opts.get("no_playback", False),
            "window_title": "OmniCapture - Mobile Camera Feed (Dual Mode)"
        }
        cam_cmd = self.engine.build_command("record_camera", cam_opts)

        print("\n\033[1;36m========================================================================\033[0m")
        print("\033[1;32m  🔴 DUAL SIMULTANEOUS RECORDING ACTIVE\033[0m")
        print(f"\033[97m  Stream 1 [PC Screen]:\033[0m      {pc_file.name} (FPS: {opts.get('pc_fps', 30)})")
        print(f"\033[97m  Stream 2 [Mobile Camera]:\033[0m  {cam_file.name} (Facing: {cam_opts['camera_facing'].capitalize()}, FPS: {cam_opts['camera_fps']})")
        print(f"\033[90m  Storage Directory:\033[0m         {self.recordings_dir}")
        print("\033[1;33m  ------------------------------------------------------------------------\033[0m")
        print("  \033[1m>> Both feeds are recording concurrently into two separate files.\033[0m")
        print("  \033[1m>> Press [Enter] or [Ctrl + C] in this terminal to STOP BOTH recordings.\033[0m")
        print("\033[1;36m========================================================================\033[0m\n")

        start_time = time.time()

        # Turn mobile display off for stealth operation & power saving
        if opts.get("screen_off", True) and self.adb:
            self.adb.turn_screen_off(opts.get("device_id"))

        # Launch Mobile Camera capture process
        cam_proc = subprocess.Popen(cam_cmd)

        # Launch PC Desktop Screen capture process
        pc_fps = opts.get("pc_fps", 30)
        pc_proc = self.pc_recorder.start_recording(pc_file, fps=pc_fps)

        # Wait for user to trigger stop
        stop_event = threading.Event()

        def wait_for_input():
            try:
                input()
                stop_event.set()
            except Exception:
                pass

        input_thread = threading.Thread(target=wait_for_input, daemon=True)
        input_thread.start()

        try:
            while not stop_event.is_set():
                if cam_proc.poll() is not None:
                    print("\n\033[93m[Notice] Mobile camera window was closed.\033[0m")
                    break
                if pc_proc.poll() is not None:
                    print("\n\033[93m[Notice] PC screen recorder process ended.\033[0m")
                    break
                time.sleep(0.3)
        except KeyboardInterrupt:
            print("\n\033[93m[!] Stop signal received (Ctrl+C)...\033[0m")

        # Stop PC Screen recording cleanly (sends 'q' to finalize MP4 container)
        print("\n\033[96m[Stopping]\033[0m Finalizing PC Screen MP4 stream...")
        self.pc_recorder.stop_recording(pc_proc)

        # Stop Mobile Camera recording cleanly
        print("\033[96m[Stopping]\033[0m Finalizing Mobile Camera MP4 stream...")
        if cam_proc.poll() is None:
            try:
                cam_proc.terminate()
                cam_proc.wait(timeout=5.0)
            except Exception:
                cam_proc.kill()

        duration = time.time() - start_time
        time.sleep(0.8)  # Allow disk buffer flush

        pc_size = pc_file.stat().st_size if pc_file.exists() else 0
        cam_size = cam_file.stat().st_size if cam_file.exists() else 0

        print("\n\033[1;32m========================================================================\033[0m")
        print(f"\033[1;32m  ✅ DUAL RECORDING COMPLETE — 2 SEPARATE FILES SAVED\033[0m")
        print(f"\033[97m  Duration:\033[0m            {self.format_duration(duration)}")
        print(f"\033[97m  1. PC Screen File:\033[0m   {pc_file.name} ({self.format_size(pc_size)})")
        print(f"\033[90m     Path:\033[0m             {pc_file}")
        print(f"\033[97m  2. Mobile Camera:\033[0m    {cam_file.name} ({self.format_size(cam_size)})")
        print(f"\033[90m     Path:\033[0m             {cam_file}")
        print("\033[1;32m========================================================================\033[0m\n")

        results = {
            "success": True,
            "duration": duration,
            "pc_screen_file": pc_file if pc_size > 0 else None,
            "pc_screen_size": pc_size,
            "mobile_camera_file": cam_file if cam_size > 0 else None,
            "mobile_camera_size": cam_size,
        }

        if auto_upload:
            if pc_size > 0:
                print(f"\033[96m[Auto-Upload]\033[0m Uploading PC Screen recording to Google Drive...")
                ok_pc, msg_pc = self.uploader.upload_file(str(pc_file))
                print(f"  -> {msg_pc}")
            if cam_size > 0:
                print(f"\033[96m[Auto-Upload]\033[0m Uploading Mobile Camera recording to Google Drive...")
                ok_cam, msg_cam = self.uploader.upload_file(str(cam_file))
                print(f"  -> {msg_cam}")

        return results
