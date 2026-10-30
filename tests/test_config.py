import sys
from pathlib import Path
REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import json
import unittest
from omni import load_config, BASE_DIR

class TestConfig(unittest.TestCase):
    def test_load_config_defaults(self):
        cfg = load_config()
        self.assertIsInstance(cfg, dict)
        self.assertIn("scrcpy_dir", cfg)
        self.assertIn("recordings_dir", cfg)
        self.assertIn("max_size", cfg)
        self.assertIn("video_bit_rate", cfg)
        self.assertIn("max_fps", cfg)
        self.assertIn("google_drive", cfg)

    def test_relative_paths_exist(self):
        cfg = load_config()
        bin_path = Path(cfg["scrcpy_dir"])
        if not bin_path.is_absolute():
            bin_path = BASE_DIR / bin_path

        rec_path = Path(cfg["recordings_dir"])
        if not rec_path.is_absolute():
            rec_path = BASE_DIR / rec_path

        self.assertTrue(bin_path.exists(), f"Binary dir should exist: {bin_path}")
        self.assertTrue(rec_path.exists(), f"Recordings dir should exist: {rec_path}")

    def test_config_types(self):
        cfg = load_config()
        self.assertIsInstance(cfg["max_size"], int)
        self.assertIsInstance(cfg["max_fps"], int)
        self.assertIsInstance(cfg["video_bit_rate"], str)
        self.assertIsInstance(cfg["screen_off_during_capture"], bool)

if __name__ == "__main__":
    unittest.main()
