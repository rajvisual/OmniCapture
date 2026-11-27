import os
import sys
import shutil
import subprocess
import time
from pathlib import Path
from typing import List, Optional, Tuple, Dict, Any

from core.resource_path import resolve_binary, get_recordings_dir

class PCRecorder:
    """
    High-performance Windows desktop screen recorder powered by FFmpeg.
    Captures full PC display with mouse cursor and encodes to MP4/MKV via libx264.
    """

    def __init__(self, ffmpeg_path: Optional[str] = None, bin_dir: Optional[str] = None):
        self.bin_dir = Path(bin_dir) if bin_dir else Path(__file__).resolve().parent.parent / "bin"
        self.ffmpeg_path = self._resolve_ffmpeg(ffmpeg_path)
        self.last_log_path = get_recordings_dir() / ".pc_recorder_last.log"
        self._cached_encoder: Optional[Tuple[str, str]] = None

    def detect_best_encoder(self) -> Tuple[str, str]:
        """
        Auto-detect the best hardware video encoder supported on the current host.
        Order of precedence:
          1. h264_nvenc (NVIDIA NVENC)
          2. h264_amf   (AMD AMF / Radeon)
          3. h264_qsv   (Intel QuickSync)
          4. h264_mf    (Windows Media Foundation MFT)
          5. libx264    (CPU Software Fallback)
        Returns (codec_name, display_name).
        """
        if self._cached_encoder:
            return self._cached_encoder

        if not self.is_available():
            self._cached_encoder = ("libx264", "Software (libx264)")
            return self._cached_encoder

        candidates = [
            ("h264_nvenc", "NVIDIA NVENC (Hardware)", ["-preset", "p1", "-tune", "ll"]),
            ("h264_amf", "AMD AMF (Radeon GPU)", ["-quality", "speed"]),
            ("h264_qsv", "Intel QuickSync (Hardware)", ["-preset", "veryfast"]),
            ("h264_mf", "MediaFoundation (Hardware MFT)", []),
            ("libx264", "Software CPU (libx264)", ["-preset", "ultrafast", "-crf", "23"])
        ]

        for codec, display_name, extra_flags in candidates:
            try:
                cmd = [
                    str(self.ffmpeg_path),
                    "-y",
                    "-f", "lavfi",
                    "-i", "testsrc=duration=0.04:size=64x64:rate=30",
                    "-c:v", codec,
                    *extra_flags,
                    "-f", "null",
                    "-"
                ]
                res = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    timeout=3,
                    check=False
                )
                if res.returncode == 0:
                    self._cached_encoder = (codec, display_name)
                    return self._cached_encoder
            except Exception:
                continue

        self._cached_encoder = ("libx264", "Software CPU (libx264)")
        return self._cached_encoder

    @property
    def encoder(self) -> str:
        """The active video encoder codec name (e.g. 'h264_amf', 'h264_nvenc', 'libx264')."""
        return self.detect_best_encoder()[0]

    def _resolve_ffmpeg(self, custom_path: Optional[str] = None) -> Optional[Path]:
        """Locate ffmpeg binary in custom path, bin directory, or system PATH."""
        if custom_path and Path(custom_path).is_file():
            return Path(custom_path)

        resolved = resolve_binary("ffmpeg", self.bin_dir)
        if resolved:
            return resolved

        # Check local bin/
        local_candidate = self.bin_dir / "ffmpeg.exe"
        if local_candidate.is_file():
            return local_candidate

        # Check system PATH
        system_candidate = shutil.which("ffmpeg")
        if system_candidate:
            return Path(system_candidate)

        return None

    def is_available(self) -> bool:
        """Check if FFmpeg is available for PC screen recording."""
        return self.ffmpeg_path is not None and self.ffmpeg_path.is_file()

    def get_ffmpeg_version(self) -> Optional[str]:
        """Query FFmpeg version line."""
        if not self.is_available():
            return None
        try:
            res = subprocess.run(
                [str(self.ffmpeg_path), "-version"],
                capture_output=True,
                text=True,
                timeout=4,
                check=False
            )
            if res.returncode == 0 and res.stdout:
                return res.stdout.splitlines()[0].strip()
        except Exception:
            pass
        return None

    def build_command(
        self,
        output_file: Path | str,
        fps: int = 30,
        draw_mouse: bool = True,
        codec: Optional[str] = None,
        preset: str = "ultrafast",
        crf: int = 23,
        scale: Optional[str] = None
    ) -> List[str]:
        """
        Build the FFmpeg execution command for Windows desktop capture.
        Auto-detects hardware encoder (nvenc > amf > qsv > mf > libx264).
        """
        if not self.ffmpeg_path:
            raise FileNotFoundError(
                "FFmpeg executable not found. Please install FFmpeg (e.g. 'winget install Gyan.FFmpeg') "
                "or place ffmpeg.exe inside the bin/ directory."
            )

        active_codec = codec or self.detect_best_encoder()[0]

        cmd = [
            str(self.ffmpeg_path),
            "-y",                                  # Overwrite output without asking
            "-f", "gdigrab",                       # Windows GDI desktop capture device
            "-framerate", str(fps),                # Target capture frame rate
            "-draw_mouse", "1" if draw_mouse else "0",
            "-i", "desktop",                       # Capture entire primary desktop
            "-c:v", active_codec,                  # Hardware-accelerated or software codec
        ]

        if active_codec == "h264_amf":
            cmd.extend(["-quality", "speed", "-rc", "cbr"])
        elif active_codec == "h264_nvenc":
            cmd.extend(["-preset", "p1", "-tune", "ll"])
        elif active_codec == "h264_qsv":
            cmd.extend(["-preset", "veryfast"])
        elif active_codec == "libx264":
            cmd.extend(["-preset", preset, "-crf", str(crf)])

        cmd.extend(["-pix_fmt", "yuv420p"])

        if str(output_file).lower().endswith(".mp4"):
            # Crash-safe fragmented MP4: writes keyframe moof fragments so interrupted recordings are fully playable
            cmd.extend(["-movflags", "+frag_keyframe+empty_moov+default_base_moof"])

        if scale:
            cmd.extend(["-vf", f"scale={scale}"])

        cmd.append(str(output_file))
        return cmd

    def _get_session_lock_path(self) -> Path:
        return get_recordings_dir() / ".omni_active_recording.json"

    def _write_active_session_lock(self, output_file: Path | str, pid: int, phone_file: Optional[Path | str] = None):
        try:
            lock = self._get_session_lock_path()
            data = {
                "pid": pid,
                "pc_file": str(output_file),
                "phone_file": str(phone_file) if phone_file else None,
                "start_time": time.time(),
                "status": "recording"
            }
            import json
            lock.write_text(json.dumps(data, indent=2), encoding="utf-8")
        except Exception:
            pass

    def _clear_active_session_lock(self):
        try:
            lock = self._get_session_lock_path()
            if lock.is_file():
                lock.unlink(missing_ok=True)
        except Exception:
            pass

    def check_and_recover_interrupted_recordings(self, recordings_dir: Optional[Path | str] = None) -> List[Dict[str, Any]]:
        """
        Scan recordings folder for interrupted sessions after an ungraceful exit/crash.
        Recovers playable video data and remuxes headers if needed.
        """
        import json
        import ctypes
        rec_dir = Path(recordings_dir) if recordings_dir else get_recordings_dir()
        lock = rec_dir / ".omni_active_recording.json"
        recovered = []
        if not lock.is_file():
            return recovered

        try:
            data = json.loads(lock.read_text(encoding="utf-8"))
            pid = data.get("pid")
            is_dead = True
            if pid and sys.platform == "win32":
                try:
                    kernel32 = ctypes.windll.kernel32
                    h_proc = kernel32.OpenProcess(0x0400, False, pid)
                    if h_proc:
                        kernel32.CloseHandle(h_proc)
                        is_dead = False
                except Exception:
                    pass

            if is_dead:
                for file_key in ("pc_file", "phone_file"):
                    fpath = data.get(file_key)
                    if fpath and Path(fpath).is_file() and Path(fpath).stat().st_size > 1024:
                        p = Path(fpath)
                        repaired_name = f"{p.stem}_recovered{p.suffix}"
                        repaired_path = p.parent / repaired_name
                        if self.ffmpeg_path and self.ffmpeg_path.is_file():
                            cmd = [
                                str(self.ffmpeg_path), "-y", "-err_detect", "ignore_err",
                                "-i", str(p), "-c", "copy", str(repaired_path)
                            ]
                            res = subprocess.run(cmd, capture_output=True, timeout=10, check=False)
                            if res.returncode == 0 and repaired_path.is_file() and repaired_path.stat().st_size > 1024:
                                p.unlink(missing_ok=True)
                                recovered.append({"original": p.name, "recovered": repaired_name, "size": repaired_path.stat().st_size})
                                continue
                        recovered.append({"original": p.name, "recovered": p.name, "size": p.stat().st_size})
            lock.unlink(missing_ok=True)
        except Exception:
            try:
                lock.unlink(missing_ok=True)
            except Exception:
                pass
        return recovered

    @staticmethod
    def get_disk_free_bytes(path: Path | str) -> int:
        """Query available disk space in bytes for target recordings directory."""
        try:
            return shutil.disk_usage(str(path)).free
        except Exception:
            return 10 * 1024**3

    @staticmethod
    def generate_sync_sidecar(
        pc_file: Path | str,
        phone_file: Path | str,
        pc_start_ns: int,
        phone_start_ns: int,
        is_simulated: bool = False
    ) -> Path:
        """
        Generate <take>.sync.json sidecar file beside video files for timeline editor alignment.
        """
        import json
        p_pc = Path(pc_file)
        p_phone = Path(phone_file)
        offset_ms = round((phone_start_ns - pc_start_ns) / 1e6, 2)
        sidecar_path = p_pc.with_suffix(".sync.json")
        data = {
            "session_id": p_pc.stem,
            "recorded_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
            "sync_offset_ms": offset_ms,
            "is_simulated": is_simulated,
            "streams": {
                "pc_screen": {
                    "file": p_pc.name,
                    "start_epoch_ns": pc_start_ns,
                    "container": p_pc.suffix.lstrip(".").lower()
                },
                "phone_camera": {
                    "file": p_phone.name,
                    "start_epoch_ns": phone_start_ns,
                    "container": p_phone.suffix.lstrip(".").lower()
                }
            },
            "alignment_guide": (
                f"Shift phone stream by {offset_ms:+.2f} ms relative to PC stream"
                if not is_simulated else "Simulated capture offset"
            )
        }
        sidecar_path.write_text(json.dumps(data, indent=2), encoding="utf-8")
        return sidecar_path

    def start_recording(
        self,
        output_file: Path | str,
        fps: int = 30,
        draw_mouse: bool = True,
        phone_file: Optional[Path | str] = None
    ) -> Tuple[subprocess.Popen, Any]:
        """
        Start non-blocking background PC screen recording.
        Drains stderr to log file to prevent OS buffer deadlock.
        Returns (proc, log_file_handle).
        """
        cmd = self.build_command(output_file, fps=fps, draw_mouse=draw_mouse)

        # Open log file to record FFmpeg output cleanly
        self.last_log_path.parent.mkdir(parents=True, exist_ok=True)
        log_file = open(self.last_log_path, "w", encoding="utf-8", errors="replace")

        proc = subprocess.Popen(
            cmd,
            stdin=subprocess.PIPE,
            stdout=subprocess.DEVNULL,
            stderr=log_file,
            text=False
        )

        try:
            from core.process_job import ProcessJobManager
            ProcessJobManager.get_instance().assign_process(proc)
        except Exception:
            pass

        self._write_active_session_lock(output_file, proc.pid, phone_file=phone_file)
        return proc, log_file

    def stop_recording(
        self,
        proc: subprocess.Popen,
        log_file: Optional[Any] = None,
        timeout: float = 8.0
    ) -> int:
        """
        Gracefully stop an ongoing FFmpeg recording session.
        Sends 'q' to stdin so FFmpeg properly finalizes the container index header.
        """
        if proc.poll() is None:
            try:
                if proc.stdin and not proc.stdin.closed:
                    proc.stdin.write(b"q\n")
                    proc.stdin.flush()
                proc.wait(timeout=timeout)
            except Exception:
                try:
                    proc.terminate()
                    proc.wait(timeout=3.0)
                except Exception:
                    proc.kill()

        if log_file and not log_file.closed:
            try:
                log_file.flush()
                log_file.close()
            except Exception:
                pass

        self._clear_active_session_lock()

        return proc.returncode

    def get_last_error_log(self, max_lines: int = 6) -> str:
        """Read recent lines from the last execution log."""
        if self.last_log_path.exists():
            try:
                with open(self.last_log_path, "r", encoding="utf-8", errors="replace") as f:
                    lines = [l.strip() for l in f.readlines() if l.strip()]
                    return "\n".join(lines[-max_lines:])
            except Exception:
                pass
        return "No log output available."

    def verify_recording_file(self, path: Path | str) -> Tuple[bool, int]:
        """
        Verify that a recording file exists and is valid (> 1024 bytes).
        Deletes empty / broken 0-byte files automatically.
        Returns (is_valid, file_size_bytes).
        """
        p = Path(path)
        if not p.exists():
            return False, 0
        size = p.stat().st_size
        if size <= 1024:
            # File is empty or corrupted header only -> remove it
            try:
                p.unlink()
            except Exception:
                pass
            return False, 0
        return True, size
