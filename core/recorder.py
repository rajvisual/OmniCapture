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
            fname = f"REC_MOBILE_CAMERA{tag}_{now_str}.{fmt}"
        else:
            fname = f"REC_MOBILE_SCREEN{tag}_{now_str}.{fmt}"
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
        # Preflight check for Android device
        if self.adb:
            check = self.adb.preflight_check(opts.get("device_id"))
            if check["status"] != "DEVICE CONNECTED":
                self.adb.print_preflight_card(check)
                return None, 0.0, 0
            opts["device_id"] = check["device_id"]

        fmt = opts.get("record_format", "mp4")
        facing = opts.get("camera_facing", "")
        file_path = self.generate_filename(mode, fmt=fmt, prefix_tag=facing.upper() if facing else "")
        opts["record_file"] = str(file_path)

        cmd = self.engine.build_command(mode, opts)
        env = self.engine.get_scrcpy_env(self.adb.adb_path if self.adb else None)

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

        # In camera mode, ensure camera sensor lock is released and display is awake
        if "camera" in mode and self.adb:
            dev = opts.get("device_id")
            self.adb.wake_screen(dev)
            self.adb.release_camera_lock(dev)

        # Run recording live
        code, duration = self.engine.run_live(cmd, env=env)

        time.sleep(0.5)  # allow disk flush
        is_valid, file_size = self.pc_recorder.verify_recording_file(file_path)

        if is_valid and file_size > 0:
            print("\n\033[1;32m========================================================\033[0m")
            print(f"\033[1;32m  ✅ RECORDING FINISHED & SAVED LOCALLY\033[0m")
            print(f"\033[97m  File:\033[0m     {file_path.name}")
            print(f"\033[90m  Location:\033[0m {file_path}")
            print(f"\033[97m  Duration:\033[0m {self.format_duration(duration)}")
            print(f"\033[97m  Size:\033[0m     {self.format_size(file_size)}")
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
            print(f"\n\033[1;31m[!] Recording failed or produced 0 bytes: {file_path.name}\033[0m")
            if "camera" in mode:
                print("\033[1;33m" + "=" * 70)
                print("  💡 CAMERA HARDWARE ACCESS NOTICE:")
                print("  If you see 'CAMERA_IN_USE' or 'Higher-priority client using camera':")
                print("  An app on your phone (like the Camera app, WhatsApp, or Instagram)")
                print("  was holding exclusive access to the physical camera sensor.")
                print("  OmniCapture has forced-closed the background camera apps for you.")
                print("  Please unlock your phone screen and try again!")
                print("=" * 70 + "\033[0m")
            if code != 0:
                print(f"\033[90mProcess exited with code {code}.\033[0m")
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

        Features:
          - Preflight verification of ADB and Android device authorization.
          - Preflight verification of FFmpeg installation.
          - Startup healthcheck detecting early failures.
          - Independent stream verification (no false success reporting).
          - Automatic cleanup of 0-byte or corrupted files.
          - Accurate status: 'SUCCESS' | 'PARTIAL SUCCESS' | 'FAILED'.
        """
        # 1. Verify FFmpeg availability
        if not self.pc_recorder.is_available():
            print("\n\033[1;31m" + "=" * 70)
            print("  ❌ DUAL RECORDING ERROR: FFMPEG IS REQUIRED FOR PC SCREEN CAPTURE")
            print("=" * 70 + "\033[0m")
            print("  FFmpeg was not found in your system PATH or bin/ folder.")
            print("\n  \033[1mINSTALLATION INSTRUCTIONS:\033[0m")
            print("  Run the following command in PowerShell:")
            print("    \033[1;33mwinget install Gyan.FFmpeg\033[0m")
            print("  Or place ffmpeg.exe inside the OmniCapture 'bin/' directory.")
            print("\033[1;31m" + "=" * 70 + "\033[0m\n")
            return {
                "success": False,
                "status": "FAILED",
                "error": "FFmpeg not found",
                "pc_screen_file": None,
                "mobile_camera_file": None
            }

        # 2. Verify Android Device Preflight
        target_dev = opts.get("device_id")
        if self.adb:
            check = self.adb.preflight_check(target_dev)
            if check["status"] != "DEVICE CONNECTED":
                self.adb.print_preflight_card(check)
                print("\033[1;31m[!] Dual Recording aborted: Valid Android device is required for mobile camera capture.\033[0m\n")
                return {
                    "success": False,
                    "status": "FAILED",
                    "error": f"Android device unavailable: {check['status']}",
                    "pc_screen_file": None,
                    "mobile_camera_file": None
                }
            target_dev = check["device_id"]
            opts["device_id"] = target_dev

        # 3. Setup Target Files
        fmt = opts.get("record_format", "mp4")
        pc_file, cam_file = self.generate_dual_filenames(fmt=fmt)

        # 4. Build Mobile Camera scrcpy options
        cam_opts = {
            "device_id": target_dev,
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
        scrcpy_env = self.engine.get_scrcpy_env(self.adb.adb_path if self.adb else None)

        # Log files to drain stderr and prevent OS buffer deadlocks
        cam_log_path = self.recordings_dir / ".scrcpy_cam_last.log"
        cam_log_file = open(cam_log_path, "w", encoding="utf-8", errors="replace")

        # 5. Launch Processes with Healthcheck
        print("\n\033[1;36m========================================================================\033[0m")
        print("\033[1;32m  🔴 DUAL SIMULTANEOUS RECORDING INITIALIZING...\033[0m")
        print(f"\033[97m  Stream 1 [PC Screen]:\033[0m      {pc_file.name} (FPS: {opts.get('pc_fps', 30)})")
        print(f"\033[97m  Stream 2 [Mobile Camera]:\033[0m  {cam_file.name} (Facing: {cam_opts['camera_facing'].capitalize()}, FPS: {cam_opts['camera_fps']})")
        print(f"\033[90m  Storage Directory:\033[0m         {self.recordings_dir}")
        print("\033[1;36m========================================================================\033[0m\n")

        start_time = time.time()

        # Ensure mobile display is awake and camera sensor lock is released
        if self.adb:
            self.adb.wake_screen(target_dev)
            self.adb.release_camera_lock(target_dev)

        # Start mobile camera subprocess
        cam_proc = subprocess.Popen(
            cam_cmd,
            env=scrcpy_env,
            stdout=cam_log_file,
            stderr=cam_log_file
        )

        # Start PC screen recording subprocess
        pc_fps = opts.get("pc_fps", 30)
        pc_proc, pc_log_file = self.pc_recorder.start_recording(pc_file, fps=pc_fps)

        # Early startup healthcheck (verify neither process died immediately)
        time.sleep(1.2)
        cam_early_exit = cam_proc.poll()
        pc_early_exit = pc_proc.poll()

        if cam_early_exit is not None:
            # Camera crashed on launch!
            cam_log_file.close()
            self.pc_recorder.stop_recording(pc_proc, pc_log_file)
            self.pc_recorder.verify_recording_file(pc_file)
            self.pc_recorder.verify_recording_file(cam_file)

            # Read scrcpy error
            err_msg = ""
            if cam_log_path.exists():
                with open(cam_log_path, "r", encoding="utf-8", errors="replace") as f:
                    err_msg = f.read().strip()

            print("\n\033[1;31m========================================================================\033[0m")
            print(f"\033[1;31m  ❌ STARTUP ERROR: Mobile Camera process failed to start (Code: {cam_early_exit})\033[0m")
            if err_msg:
                print(f"\033[90m{err_msg}\033[0m")
            print("\033[1;31m========================================================================\033[0m\n")
            return {
                "success": False,
                "status": "FAILED",
                "error": f"Mobile camera failed on startup: {err_msg or cam_early_exit}",
                "pc_screen_file": None,
                "mobile_camera_file": None
            }

        if pc_early_exit is not None:
            # PC recorder crashed on launch!
            if cam_proc.poll() is None:
                cam_proc.terminate()
            cam_log_file.close()
            self.pc_recorder.stop_recording(pc_proc, pc_log_file)
            self.pc_recorder.verify_recording_file(pc_file)
            self.pc_recorder.verify_recording_file(cam_file)

            err_pc = self.pc_recorder.get_last_error_log()
            print("\n\033[1;31m========================================================================\033[0m")
            print(f"\033[1;31m  ❌ STARTUP ERROR: PC Screen capture failed to start (Code: {pc_early_exit})\033[0m")
            if err_pc:
                print(f"\033[90m{err_pc}\033[0m")
            print("\033[1;31m========================================================================\033[0m\n")
            return {
                "success": False,
                "status": "FAILED",
                "error": f"PC recorder failed on startup: {err_pc or pc_early_exit}",
                "pc_screen_file": None,
                "mobile_camera_file": None
            }

        # 6. Both processes running smoothly
        print("\033[1;32m  ✅ BOTH CAPTURE FEEDS ARE RUNNING CONCURRENTLY\033[0m")
        print("  \033[1;33m>> Press [Enter] or [Ctrl + C] in this terminal to STOP BOTH recordings. <<\033[0m\n")

        # 7. Monitoring Loop
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
                    print(f"\n\033[93m[Notice] Mobile camera stream closed (Exit code: {cam_proc.returncode}).\033[0m")
                    break
                if pc_proc.poll() is not None:
                    print(f"\n\033[93m[Notice] PC screen recorder stream closed (Exit code: {pc_proc.returncode}).\033[0m")
                    break
                time.sleep(0.3)
        except KeyboardInterrupt:
            print("\n\033[93m[!] Stop signal received (Ctrl+C)...\033[0m")

        # 8. Coordinated Graceful Finalization
        print("\n\033[96m[Stopping]\033[0m Finalizing PC Screen MP4 stream...")
        self.pc_recorder.stop_recording(pc_proc, pc_log_file)

        print("\033[96m[Stopping]\033[0m Finalizing Mobile Camera MP4 stream...")
        if cam_proc.poll() is None:
            try:
                cam_proc.terminate()
                cam_proc.wait(timeout=5.0)
            except Exception:
                cam_proc.kill()
        cam_log_file.close()

        duration = time.time() - start_time
        time.sleep(0.8)  # Allow disk buffer flush

        # 9. Independent Stream File Verification & Cleanup of 0-byte files
        pc_valid, pc_size = self.pc_recorder.verify_recording_file(pc_file)
        cam_valid, cam_size = self.pc_recorder.verify_recording_file(cam_file)

        # 10. Determine Final Status (No False Success!)
        if pc_valid and cam_valid:
            final_status = "SUCCESS"
            print("\n\033[1;32m========================================================================\033[0m")
            print(f"\033[1;32m  ✅ DUAL RECORDING COMPLETE — 2 SEPARATE FILES SAVED\033[0m")
            print(f"\033[97m  Duration:\033[0m            {self.format_duration(duration)}")
            print(f"\033[97m  1. PC Screen File:\033[0m   {pc_file.name} ({self.format_size(pc_size)}) \033[92m[OK]\033[0m")
            print(f"\033[90m     Path:\033[0m             {pc_file}")
            print(f"\033[97m  2. Mobile Camera:\033[0m    {cam_file.name} ({self.format_size(cam_size)}) \033[92m[OK]\033[0m")
            print(f"\033[90m     Path:\033[0m             {cam_file}")
            print("\033[1;32m========================================================================\033[0m\n")

        elif pc_valid and not cam_valid:
            final_status = "PARTIAL SUCCESS"
            print("\n\033[1;33m========================================================================\033[0m")
            print(f"\033[1;33m  ⚠️  PARTIAL SUCCESS — PC Screen Recorded, Mobile Camera Failed\033[0m")
            print(f"\033[97m  Duration:\033[0m            {self.format_duration(duration)}")
            print(f"\033[97m  1. PC Screen File:\033[0m   {pc_file.name} ({self.format_size(pc_size)}) \033[92m[SAVED]\033[0m")
            print(f"\033[90m     Path:\033[0m             {pc_file}")
            print(f"\033[91m  2. Mobile Camera:\033[0m    FAILED (Empty / 0 bytes — removed automatically)")
            print("\033[1;33m========================================================================\033[0m\n")

        elif not pc_valid and cam_valid:
            final_status = "PARTIAL SUCCESS"
            print("\n\033[1;33m========================================================================\033[0m")
            print(f"\033[1;33m  ⚠️  PARTIAL SUCCESS — Mobile Camera Recorded, PC Screen Failed\033[0m")
            print(f"\033[97m  Duration:\033[0m            {self.format_duration(duration)}")
            print(f"\033[91m  1. PC Screen File:\033[0m   FAILED (Empty / 0 bytes — removed automatically)")
            print(f"\033[97m  2. Mobile Camera:\033[0m    {cam_file.name} ({self.format_size(cam_size)}) \033[92m[SAVED]\033[0m")
            print(f"\033[90m     Path:\033[0m             {cam_file}")
            print("\033[1;33m========================================================================\033[0m\n")

        else:
            final_status = "FAILED"
            print("\n\033[1;31m========================================================================\033[0m")
            print(f"\033[1;31m  ❌ DUAL RECORDING FAILED — No valid video files generated\033[0m")
            print(f"\033[90m  Any empty 0-byte temporary files have been cleaned up.\033[0m")
            print("\033[1;31m========================================================================\033[0m\n")

        results = {
            "success": final_status == "SUCCESS",
            "status": final_status,
            "duration": duration,
            "pc_screen_file": pc_file if pc_valid else None,
            "pc_screen_size": pc_size if pc_valid else 0,
            "mobile_camera_file": cam_file if cam_valid else None,
            "mobile_camera_size": cam_size if cam_valid else 0,
        }

        # 11. Cloud Auto-Upload (Only upload valid files!)
        if auto_upload:
            if pc_valid and pc_size > 0:
                print(f"\033[96m[Auto-Upload]\033[0m Uploading PC Screen recording to Google Drive...")
                ok_pc, msg_pc = self.uploader.upload_file(str(pc_file))
                print(f"  -> {msg_pc}")
            if cam_valid and cam_size > 0:
                print(f"\033[96m[Auto-Upload]\033[0m Uploading Mobile Camera recording to Google Drive...")
                ok_cam, msg_cam = self.uploader.upload_file(str(cam_file))
                print(f"  -> {msg_cam}")

        return results
