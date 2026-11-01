import sys
from pathlib import Path
REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import unittest
from core.pc_recorder import PCRecorder
from core.recorder import RecordingManager
from core.scrcpy_engine import ScrcpyEngine
from core.drive_uploader import DriveUploader

class TestPCRecorder(unittest.TestCase):
    def setUp(self):
        self.recorder = PCRecorder()
        self.engine = ScrcpyEngine(scrcpy_dir=str(REPO_ROOT / "bin"))
        self.uploader = DriveUploader({})
        self.rec_mgr = RecordingManager(str(REPO_ROOT / "recordings"), self.engine, self.uploader)

    def test_pc_recorder_build_command(self):
        if not self.recorder.is_available():
            self.skipTest("FFmpeg not installed in test environment")

        out_path = REPO_ROOT / "recordings" / "test_out.mp4"
        cmd = self.recorder.build_command(out_path, fps=30, draw_mouse=True)
        self.assertIn("-f", cmd)
        self.assertIn("gdigrab", cmd)
        self.assertIn("-framerate", cmd)
        self.assertIn("30", cmd)
        self.assertIn("-draw_mouse", cmd)
        self.assertIn("1", cmd)
        self.assertIn("-i", cmd)
        self.assertIn("desktop", cmd)
        self.assertIn("-c:v", cmd)
        self.assertIn("libx264", cmd)
        self.assertIn(str(out_path), cmd)

    def test_dual_filenames_generation(self):
        pc_file, cam_file = self.rec_mgr.generate_dual_filenames(fmt="mp4")
        self.assertNotEqual(pc_file, cam_file)
        self.assertTrue(pc_file.name.startswith("REC_PC_SCREEN_"))
        self.assertTrue(cam_file.name.startswith("REC_MOBILE_CAMERA_"))
        self.assertTrue(pc_file.name.endswith(".mp4"))
        self.assertTrue(cam_file.name.endswith(".mp4"))

    def test_dual_filenames_custom_format(self):
        pc_file, cam_file = self.rec_mgr.generate_dual_filenames(fmt="mkv")
        self.assertTrue(pc_file.name.endswith(".mkv"))
        self.assertTrue(cam_file.name.endswith(".mkv"))

if __name__ == "__main__":
    unittest.main()
