import os
import sys
import shutil
import subprocess
import time
from pathlib import Path
from typing import List, Optional, Tuple, Dict, Any

class PCRecorder:
    """
    High-performance Windows desktop screen recorder powered by FFmpeg.
    Captures full PC display with mouse cursor and encodes to MP4/MKV via libx264.
    """

    def __init__(self, ffmpeg_path: Optional[str] = None, bin_dir: Optional[str] = None):
        self.bin_dir = Path(bin_dir) if bin_dir else Path(__file__).resolve().parent.parent / "bin"
        self.ffmpeg_path = self._resolve_ffmpeg(ffmpeg_path)
        self.last_log_path = self.bin_dir.parent / "recordings" / ".pc_recorder_last.log"

    def _resolve_ffmpeg(self, custom_path: Optional[str] = None) -> Optional[Path]:
        """Locate ffmpeg binary in custom path, bin directory, or system PATH."""
        if custom_path and Path(custom_path).is_file():
            return Path(custom_path)

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
        preset: str = "ultrafast",
        crf: int = 23,
        scale: Optional[str] = None
    ) -> List[str]:
        """
        Build the FFmpeg execution command for Windows GDI desktop capture.
        """
        if not self.ffmpeg_path:
            raise FileNotFoundError(
                "FFmpeg executable not found. Please install FFmpeg (e.g. 'winget install Gyan.FFmpeg') "
                "or place ffmpeg.exe inside the bin/ directory."
            )

        cmd = [
            str(self.ffmpeg_path),
            "-y",                                  # Overwrite output without asking
            "-f", "gdigrab",                       # Windows GDI desktop capture device
            "-framerate", str(fps),                # Target capture frame rate
            "-draw_mouse", "1" if draw_mouse else "0",
            "-i", "desktop",                       # Capture entire primary desktop
            "-c:v", "libx264",                     # H.264 video codec
            "-preset", preset,                     # Ultrafast encoding for minimal CPU latency
            "-crf", str(crf),                      # Constant Rate Factor (balanced quality/size)
            "-pix_fmt", "yuv420p"                  # Universal compatibility format
        ]

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
