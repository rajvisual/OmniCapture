import sys
from pathlib import Path
REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import unittest
from core.scrcpy_engine import ScrcpyEngine

class TestScrcpyArgs(unittest.TestCase):
    def setUp(self):
        self.engine = ScrcpyEngine(scrcpy_dir=str(REPO_ROOT / "bin"))

    def test_mirror_default_command(self):
        opts = {
            "device_id": "test_device_123",
            "screen_off": True,
            "stay_awake": True,
            "max_size": 1200,
            "max_fps": 60,
            "bit_rate": "8M"
        }
        cmd = self.engine.build_command("mirror", opts)
        self.assertIn("-s", cmd)
        self.assertIn("test_device_123", cmd)
        self.assertIn("--turn-screen-off", cmd)
        self.assertIn("--stay-awake", cmd)
        self.assertIn("--max-size=1200", cmd)
        self.assertIn("--max-fps=60", cmd)
        self.assertIn("--video-bit-rate=8M", cmd)
        self.assertIn("--shortcut-mod=lalt", cmd)

    def test_camera_mode_excludes_forbidden_flags(self):
        # Camera mode MUST exclude --turn-screen-off and --stay-awake to prevent scrcpy validation crash
        opts = {
            "device_id": "test_device_123",
            "camera_facing": "back",
            "camera_size": "1920x1080",
            "camera_fps": 30,
            "screen_off": True,
            "stay_awake": True
        }
        cmd = self.engine.build_command("camera", opts)
        self.assertIn("--video-source=camera", cmd)
        self.assertIn("--camera-facing=back", cmd)
        self.assertIn("--camera-size=1920x1080", cmd)
        self.assertIn("--camera-fps=30", cmd)
        self.assertNotIn("--turn-screen-off", cmd)
        self.assertNotIn("--stay-awake", cmd)

    def test_uhid_flags(self):
        opts = {
            "uhid": True
        }
        cmd = self.engine.build_command("mirror", opts)
        self.assertIn("--keyboard=uhid", cmd)
        self.assertIn("--mouse=uhid", cmd)

    def test_recording_flags(self):
        opts = {
            "record_file": "recordings/test.mp4",
            "record_format": "mp4",
            "no_playback": True
        }
        cmd = self.engine.build_command("record_screen", opts)
        self.assertIn("--record=recordings/test.mp4", cmd)
        self.assertIn("--record-format=mp4", cmd)
        self.assertIn("--no-playback", cmd)

if __name__ == "__main__":
    unittest.main()
