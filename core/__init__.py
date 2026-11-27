"""
OmniCapture Core Engine Package
"""
__version__ = "1.2.0"

from core.adb_manager import ADBManager
from core.scrcpy_engine import ScrcpyEngine
from core.recorder import RecordingManager
from core.pc_recorder import PCRecorder
from core.drive_uploader import DriveUploader
from core.resource_path import (
    is_frozen,
    get_base_dir,
    get_bundled_dir,
    resolve_resource,
    resolve_binary,
    get_recordings_dir,
)

__all__ = [
    "ADBManager",
    "ScrcpyEngine",
    "RecordingManager",
    "PCRecorder",
    "DriveUploader",
    "is_frozen",
    "get_base_dir",
    "get_bundled_dir",
    "resolve_resource",
    "resolve_binary",
    "get_recordings_dir",
]
