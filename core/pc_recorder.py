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

        if scale:
            cmd.extend(["-vf", f"scale={scale}"])

        cmd.append(str(output_file))
        return cmd

    def start_recording(
        self,
        output_file: Path | str,
        fps: int = 30,
        draw_mouse: bool = True
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
        return proc, log_file

    def stop_recording(
        self,
        proc: subprocess.Popen,
        log_file: Optional[Any] = None,
        timeout: float = 8.0
    ) -> int:
        """
        Gracefully stop an ongoing FFmpeg recording session.
        Sends 'q' to stdin so FFmpeg properly finalizes the MP4 index header (moov atom).
        """
        if proc.poll() is None:
            try:
                # Send 'q' to tell FFmpeg to stop and write trailing container metadata
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
