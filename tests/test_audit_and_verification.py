import sys
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from core.adb_manager import ADBManager
from core.scrcpy_engine import ScrcpyEngine
from core.pc_recorder import PCRecorder
from core.recorder import RecordingManager
from core.drive_uploader import DriveUploader
from omni import resolve_target_device, build_parser

class TestAuditAndVerification(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.recordings_dir = Path(self.temp_dir.name)
        self.adb = ADBManager(scrcpy_dir=str(REPO_ROOT / "bin"))
        self.scrcpy = ScrcpyEngine(scrcpy_dir=str(REPO_ROOT / "bin"))
        self.uploader = DriveUploader({})
        self.pc_rec = PCRecorder(bin_dir=str(REPO_ROOT / "bin"))
        self.recorder = RecordingManager(
            str(self.recordings_dir),
            self.scrcpy,
            self.uploader,
            adb_manager=self.adb,
            pc_recorder=self.pc_rec
        )

    def tearDown(self):
        self.temp_dir.cleanup()

    # --- Preflight State Tests ---
    def test_adb_preflight_no_device(self):
        with patch.object(self.adb, "list_devices", return_value=[]):
            check = self.adb.preflight_check()
            self.assertEqual(check["status"], "NO DEVICE FOUND")
            self.assertIsNone(check["device_id"])

    def test_adb_preflight_unauthorized(self):
        mock_devices = [{"id": "DEV123", "state": "unauthorized", "model": "TestPhone", "is_wireless": False}]
        with patch.object(self.adb, "list_devices", return_value=mock_devices):
            check = self.adb.preflight_check()
            self.assertEqual(check["status"], "DEVICE UNAUTHORIZED")
            self.assertEqual(check["device_id"], "DEV123")

    def test_adb_preflight_offline(self):
        mock_devices = [{"id": "DEV123", "state": "offline", "model": "TestPhone", "is_wireless": False}]
        with patch.object(self.adb, "list_devices", return_value=mock_devices):
            check = self.adb.preflight_check()
            self.assertEqual(check["status"], "DEVICE OFFLINE")
            self.assertEqual(check["device_id"], "DEV123")

    def test_adb_preflight_connected(self):
        mock_devices = [{"id": "DEV123", "state": "device", "model": "TestPhone", "is_wireless": False}]
        with patch.object(self.adb, "list_devices", return_value=mock_devices), \
             patch.object(self.adb, "get_device_properties", return_value={"android_version": "12", "model": "TestPhone"}):
            check = self.adb.preflight_check()
            self.assertEqual(check["status"], "DEVICE CONNECTED")
            self.assertEqual(check["device_id"], "DEV123")

    # --- Device Resolution & Prioritization ---
    def test_resolve_target_device_prioritizes_usb(self):
        mock_devices = [
            {"id": "192.168.1.5:5555", "state": "device", "model": "Wi-Fi Phone", "is_wireless": True},
            {"id": "USB_SERIAL_1", "state": "device", "model": "USB Phone", "is_wireless": False}
        ]
        with patch.object(self.adb, "list_devices", return_value=mock_devices):
            resolved = resolve_target_device(self.adb, interactive=False)
            self.assertEqual(resolved, "USB_SERIAL_1")

    # --- Scrcpy Environment & Flag Tests ---
    def test_scrcpy_env_adb_variable(self):
        env = self.scrcpy.get_scrcpy_env(adb_path=Path("C:/custom/adb.exe"))
        self.assertIn("ADB", env)
        self.assertTrue(env["ADB"].endswith("adb.exe"))

    def test_scrcpy_camera_no_audio_when_none(self):
        opts = {"device_id": "DEV1", "camera_facing": "back", "audio_source": "none"}
        cmd = self.scrcpy.build_command("camera", opts)
        self.assertIn("--no-audio", cmd)

    # --- File Validation & Cleanup Tests ---
    def test_empty_file_cleanup(self):
        empty_file = self.recordings_dir / "empty.mp4"
        empty_file.write_bytes(b"")
        valid, size = self.pc_rec.verify_recording_file(empty_file)
        self.assertFalse(valid)
        self.assertEqual(size, 0)
        self.assertFalse(empty_file.exists(), "Empty 0-byte file must be deleted automatically")

    def test_valid_file_retention(self):
        good_file = self.recordings_dir / "good.mp4"
        good_file.write_bytes(b"0" * 4096)
        valid, size = self.pc_rec.verify_recording_file(good_file)
        self.assertTrue(valid)
        self.assertEqual(size, 4096)
        self.assertTrue(good_file.exists())

    # --- Dual Recording Healthcheck & Status Logic ---
    def test_dual_record_aborts_when_ffmpeg_missing(self):
        with patch.object(self.pc_rec, "is_available", return_value=False):
            res = self.recorder.record_dual_pc_and_mobile_camera({})
            self.assertFalse(res["success"])
            self.assertEqual(res["status"], "FAILED")
            self.assertIn("FFmpeg not found", res["error"])

    def test_dual_record_aborts_when_device_missing(self):
        with patch.object(self.pc_rec, "is_available", return_value=True), \
             patch.object(self.adb, "preflight_check", return_value={"status": "NO DEVICE FOUND"}):
            res = self.recorder.record_dual_pc_and_mobile_camera({})
            self.assertFalse(res["success"])
            self.assertEqual(res["status"], "FAILED")
            self.assertIn("Android device unavailable", res["error"])

if __name__ == "__main__":
    unittest.main()
