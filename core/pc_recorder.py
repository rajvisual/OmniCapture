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

    def build_command(
        self,
        output_file: Path | str,
        fps: int = 30,
        draw_mouse: bool = True,
        preset: str = "ultrafast",
        crf: int = 23,
        show_region: bool = False
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
            "-pix_fmt", "yuv420p",                 # Universal compatibility format
            str(output_file)
        ]
        return cmd

    def start_recording(
        self,
        output_file: Path | str,
        fps: int = 30,
        draw_mouse: bool = True
    ) -> subprocess.Popen:
        """
        Start non-blocking background PC screen recording.
        Returns the active subprocess.Popen instance.
        """
        cmd = self.build_command(output_file, fps=fps, draw_mouse=draw_mouse)
        proc = subprocess.Popen(
            cmd,
            stdin=subprocess.PIPE,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
            text=False
        )
        return proc

    def stop_recording(self, proc: subprocess.Popen, timeout: float = 8.0) -> int:
        """
        Gracefully stop an ongoing FFmpeg recording session.
        Sends 'q' to stdin so FFmpeg properly finalizes the MP4 index header (moov atom).
        """
        if proc.poll() is not None:
            return proc.returncode

        try:
            # Send 'q' to tell FFmpeg to stop and write trailing container metadata
            if proc.stdin:
                proc.stdin.write(b"q\n")
                proc.stdin.flush()
            proc.wait(timeout=timeout)
        except Exception:
            try:
                proc.terminate()
                proc.wait(timeout=3.0)
            except Exception:
                proc.kill()

        return proc.returncode
