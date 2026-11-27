import os
import sys
import shutil
from pathlib import Path
from typing import Optional

def is_frozen() -> bool:
    """Return True if running as a compiled PyInstaller standalone executable."""
    return getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS")

def get_base_dir() -> Path:
    """
    Get the permanent base application directory (where config.json, recordings/, etc. live).
    If frozen, this is the directory containing the .exe.
    If running as script, this is the repository root containing omni.py.
    """
    if is_frozen():
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent.parent

def get_bundled_dir() -> Path:
    """
    Get the directory containing bundled read-only assets (icons, bins, configs).
    If frozen, this points to sys._MEIPASS.
    If running as script, this points to the repository root.
    """
    if is_frozen():
        return Path(getattr(sys, "_MEIPASS")).resolve()
    return get_base_dir()

def resolve_resource(rel_path: str | Path) -> Path:
    """
    Resolve a relative resource path (e.g. 'assets/logo/omnicapture.ico').
    Checks the bundled directory first, then falls back to the base directory.
    """
    p = Path(rel_path)
    bundled = get_bundled_dir() / p
    if bundled.exists():
        return bundled
    return get_base_dir() / p

def resolve_binary(binary_name: str, preferred_dir: Optional[Path | str] = None) -> Optional[Path]:
    """
    Locate an executable binary (e.g. adb.exe, scrcpy.exe, ffmpeg.exe).
    Checks:
      1. preferred_dir / binary_name (if provided)
      2. get_bundled_dir() / 'bin' / binary_name
      3. get_base_dir() / 'bin' / binary_name
      4. System PATH (shutil.which)
    """
    name = binary_name if binary_name.lower().endswith(".exe") or sys.platform != "win32" else f"{binary_name}.exe"

    if preferred_dir:
        pref = Path(preferred_dir)
        cand = pref / name if not pref.is_file() else pref
        if cand.is_file():
            return cand

    cand_bundled = get_bundled_dir() / "bin" / name
    if cand_bundled.is_file():
        return cand_bundled

    cand_base = get_base_dir() / "bin" / name
    if cand_base.is_file():
        return cand_base

    system_path = shutil.which(binary_name) or shutil.which(name)
    if system_path:
        return Path(system_path).resolve()

    return None

def get_recordings_dir() -> Path:
    """Get the recordings directory, ensuring it exists."""
    rec_dir = get_base_dir() / "recordings"
    rec_dir.mkdir(parents=True, exist_ok=True)
    return rec_dir
