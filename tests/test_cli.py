import sys
from pathlib import Path
REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import unittest
from omni import build_parser

class TestCLI(unittest.TestCase):
    def setUp(self):
        self.parser = build_parser()

    def test_empty_command(self):
        args = self.parser.parse_args([])
        self.assertIsNone(args.command)

    def test_mirror_command(self):
        args = self.parser.parse_args(["mirror", "--screen-off", "--uhid"])
        self.assertEqual(args.command, "mirror")
        self.assertTrue(args.screen_off)
        self.assertTrue(args.uhid)

    def test_camera_command(self):
        args = self.parser.parse_args(["camera", "--facing", "front", "--fps", "30", "--size", "1920x1080"])
        self.assertEqual(args.command, "camera")
        self.assertEqual(args.facing, "front")
        self.assertEqual(args.fps, 30)
        self.assertEqual(args.size, "1920x1080")

    def test_record_screen(self):
        args = self.parser.parse_args(["record", "screen", "--format", "mp4", "--upload"])
        self.assertEqual(args.command, "record")
        self.assertEqual(args.source, "screen")
        self.assertEqual(args.format, "mp4")
        self.assertTrue(args.upload)

    def test_record_camera(self):
        args = self.parser.parse_args(["record", "camera", "--facing", "back", "--no-playback"])
        self.assertEqual(args.command, "record")
        self.assertEqual(args.source, "camera")
        self.assertEqual(args.facing, "back")
        self.assertTrue(args.no_playback)

    def test_record_dual(self):
        args = self.parser.parse_args(["record", "dual", "--facing", "front", "--pc-fps", "60", "--upload"])
        self.assertEqual(args.command, "record")
        self.assertEqual(args.source, "dual")
        self.assertEqual(args.facing, "front")
        self.assertEqual(args.pc_fps, 60)
        self.assertTrue(args.upload)

    def test_dual_record_command(self):
        args = self.parser.parse_args(["dual-record", "--facing", "back", "--pc-fps", "30", "--camera-fps", "60", "--format", "mkv"])
        self.assertEqual(args.command, "dual-record")
        self.assertEqual(args.facing, "back")
        self.assertEqual(args.pc_fps, 30)
        self.assertEqual(args.camera_fps, 60)
        self.assertEqual(args.format, "mkv")

    def test_info_command(self):
        args = self.parser.parse_args(["info"])
        self.assertEqual(args.command, "info")

    def test_hotkeys_command(self):
        args = self.parser.parse_args(["hotkeys"])
        self.assertEqual(args.command, "hotkeys")

    def test_wireless_command(self):
        args = self.parser.parse_args(["wireless"])
        self.assertEqual(args.command, "wireless")

if __name__ == "__main__":
    unittest.main()
