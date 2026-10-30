import os
import subprocess
import time
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple

class ScrcpyEngine:
    def __init__(self, scrcpy_dir: str):
        self.scrcpy_dir = Path(scrcpy_dir)
        self.scrcpy_path = self._resolve_scrcpy_path()

    def _resolve_scrcpy_path(self) -> Path:
        """Find scrcpy binary inside local project bin/ or configured path."""
        base_bin = Path(__file__).resolve().parent.parent / "bin" / "scrcpy.exe"
        candidates = [
            base_bin,
            self.scrcpy_dir / "scrcpy.exe",
            self.scrcpy_dir / "scrcpy-win64-v3.3.4" / "scrcpy.exe",
            self.scrcpy_dir.parent / "scrcpy.exe",
        ]
        for candidate in candidates:
            if candidate.is_file():
                return candidate
        return Path("scrcpy.exe")

    def build_command(self, mode: str, opts: Dict[str, Any]) -> List[str]:
        """
        Build command-line arguments for scrcpy execution based on mode and options.
        Modes:
          - 'mirror': Interactive display mirror + PC touch/keyboard control
          - 'camera': Direct background camera stream (WITHOUT opening phone camera app)
          - 'record_screen': Record screen to PC file
          - 'record_camera': Record camera stream to PC file
        """
        cmd = [str(self.scrcpy_path)]

        # Specific device target
        if opts.get("device_id"):
            cmd.extend(["-s", str(opts["device_id"])])

        # Stay awake while plugged in (only valid in display mode, rejected in camera mode)
        if opts.get("stay_awake", True) and mode not in ("camera", "record_camera"):
            cmd.append("--stay-awake")

        # Turn phone screen off during capture (only valid in display mode, rejected in camera mode)
        if opts.get("screen_off", False) and mode not in ("camera", "record_camera"):
            cmd.append("--turn-screen-off")

        # Video source: camera or display
        if mode in ("camera", "record_camera"):
            cmd.append("--video-source=camera")
            facing = opts.get("camera_facing", "back")
            if facing:
                cmd.append(f"--camera-facing={facing}")
            if opts.get("camera_id"):
                cmd.append(f"--camera-id={opts['camera_id']}")
            if opts.get("camera_size"):
                cmd.append(f"--camera-size={opts['camera_size']}")
            if opts.get("camera_fps"):
                cmd.append(f"--camera-fps={opts['camera_fps']}")
            if opts.get("camera_high_speed"):
                cmd.append("--camera-high-speed")

            # Camera audio is best captured from microphone
            audio_source = opts.get("audio_source", "mic")
            cmd.append(f"--audio-source={audio_source}")
        else:
            # Display mode audio (disable in live mirror on Android <= 12 to prevent codec errors)
            audio_source = opts.get("audio_source")
            if audio_source and audio_source != "none" and opts.get("record_file"):
                cmd.append(f"--audio-source={audio_source}")
            elif not opts.get("record_file"):
                cmd.append("--no-audio")

        # Headless recording (no display window)
        if opts.get("no_playback", False):
            cmd.append("--no-playback")

        # Recording target file
        record_file = opts.get("record_file")
        if record_file:
            cmd.append(f"--record={record_file}")
            fmt = opts.get("record_format")
            if fmt:
                cmd.append(f"--record-format={fmt}")

        # Quality & Codec (Optimized for 60 FPS zero-lag response)
        max_size = opts.get("max_size", 1200)
        if max_size and mode not in ("camera", "record_camera"):
            cmd.append(f"--max-size={max_size}")

        max_fps = opts.get("max_fps", 60)
        if max_fps:
            cmd.append(f"--max-fps={max_fps}")

        bit_rate = opts.get("bit_rate", "8M")
        if bit_rate:
            cmd.append(f"--video-bit-rate={bit_rate}")

        if opts.get("video_codec"):
            cmd.append(f"--video-codec={opts['video_codec']}")

        # Window Title
        title = opts.get("window_title")
        if not title:
            if "camera" in mode:
                facing = opts.get("camera_facing", "back").capitalize()
                title = f"OmniCapture - {facing} Camera (Background Stream)"
            else:
                title = "OmniCapture - Phone Controller & Display"
        cmd.append(f"--window-title={title}")

        # Input Mode: UHID hardware simulation (bypasses Xiaomi/POCO INJECT_EVENTS permission lock)
        if opts.get("uhid"):
            cmd.extend(["--keyboard=uhid", "--mouse=uhid"])

        # Hotkey modifier: use Left Alt (Alt+Z=Pause, Alt+Shift+Z=Resume, Alt+O=Screen Off, etc.)
        cmd.append("--shortcut-mod=lalt")

        return cmd

    def run_live(self, cmd: List[str]) -> Tuple[int, float]:
        """
        Run scrcpy process live in terminal.
        Returns (exit_code, duration_seconds).
        """
        start_time = time.time()
        try:
            # Run directly connected to terminal so keyboard/mouse forwarding works
            proc = subprocess.Popen(cmd)
            proc.wait()
            duration = time.time() - start_time
            return proc.returncode, duration
        except KeyboardInterrupt:
            duration = time.time() - start_time
            return 0, duration
        except Exception as e:
            print(f"\n[Error launching scrcpy]: {e}")
            return -1, 0.0

    def query_cameras(self, device_id: Optional[str] = None) -> str:
        """Query available cameras on the Android device."""
        cmd = [str(self.scrcpy_path), "--list-cameras"]
        if device_id:
            cmd.extend(["-s", device_id])
        try:
            res = subprocess.run(cmd, capture_output=True, text=True, timeout=10, encoding="utf-8", errors="replace")
            return res.stdout or res.stderr
        except Exception as e:
            return f"Error listing cameras: {e}"

    def query_camera_sizes(self, device_id: Optional[str] = None) -> str:
        """Query available camera capture resolutions on the Android device."""
        cmd = [str(self.scrcpy_path), "--list-camera-sizes"]
        if device_id:
            cmd.extend(["-s", device_id])
        try:
            res = subprocess.run(cmd, capture_output=True, text=True, timeout=10, encoding="utf-8", errors="replace")
            return res.stdout or res.stderr
        except Exception as e:
            return f"Error listing camera sizes: {e}"
