import unittest
from pathlib import Path
from PIL import Image

from core.resource_path import (
    get_base_dir,
    get_bundled_dir,
    resolve_resource,
    resolve_binary,
    get_recordings_dir,
    is_frozen,
)
from gui.theme import OmniTheme
from gui.controller import GUIController
from gui.tray import SystemTrayManager
from gui.hotkeys import GlobalHotkeyManager

class TestGUIComponents(unittest.TestCase):
    def setUp(self):
        self.base_dir = get_base_dir()
        self.sample_config = {
            "scrcpy_dir": "bin",
            "recordings_dir": "recordings",
            "default_record_format": "mp4",
            "max_size": 1200,
            "video_bit_rate": "8M",
            "max_fps": 60,
        }

    def test_resource_path_resolvers(self):
        """Verify resource_path resolves local assets and binaries."""
        self.assertTrue(self.base_dir.is_dir())
        self.assertTrue((self.base_dir / "omni.py").exists())

        # Test resolving icon assets
        icon_path = resolve_resource("assets/logo/omnicapture.ico")
        self.assertTrue(icon_path.exists())
        self.assertTrue(icon_path.is_file())

        png_path = resolve_resource("assets/logo/omnicapture-icon.png")
        self.assertTrue(png_path.exists())
        self.assertTrue(png_path.is_file())

        # Test resolving binaries in bin/
        adb_path = resolve_binary("adb", self.base_dir / "bin")
        self.assertIsNotNone(adb_path)
        self.assertTrue(adb_path.exists())

        scrcpy_path = resolve_binary("scrcpy", self.base_dir / "bin")
        self.assertIsNotNone(scrcpy_path)
        self.assertTrue(scrcpy_path.exists())

        # Test recordings dir
        rec_dir = get_recordings_dir()
        self.assertTrue(rec_dir.is_dir())

    def test_theme_palette(self):
        """Verify OmniTheme dark palette definition."""
        self.assertTrue(OmniTheme.BG_ROOT.startswith("#"))
        self.assertTrue(OmniTheme.BG_CARD.startswith("#"))
        self.assertTrue(OmniTheme.ACCENT_CYAN.startswith("#"))
        self.assertTrue(OmniTheme.ACCENT_PURPLE.startswith("#"))
        self.assertTrue(OmniTheme.ACCENT_RED.startswith("#"))
        self.assertTrue(OmniTheme.ACCENT_GREEN.startswith("#"))
        self.assertTrue(OmniTheme.TEXT_MAIN.startswith("#"))

    def test_controller_initialization_and_state(self):
        """Verify GUIController initial state and diagnostics without starting live hardware."""
        controller = GUIController(self.sample_config)
        self.assertFalse(controller.is_dual_recording())

        cached = controller.get_cached_device()
        self.assertIn("status", cached)
        self.assertIn("model", cached)
        self.assertIn("battery", cached)

        diag = controller.query_diagnostics()
        self.assertIn("adb_path", diag)
        self.assertIn("scrcpy_path", diag)
        self.assertIn("ffmpeg_path", diag)

        recordings = controller.get_recordings_list()
        self.assertIsInstance(recordings, list)

    def test_system_tray_icon_and_menu(self):
        """Verify SystemTrayManager builds valid icon image and menu."""
        tray = SystemTrayManager(
            on_show=lambda: None,
            on_exit=lambda: None,
            on_dual_record=lambda: None,
            on_mirror=lambda: None,
            on_camera=lambda: None,
            on_open_recordings=lambda: None,
        )
        img = tray._load_icon_image()
        self.assertIsInstance(img, Image.Image)
        self.assertEqual(img.size, (64, 64))

        menu = tray._build_menu()
        self.assertIsNotNone(menu)

    def test_hotkey_manager_mappings(self):
        """Verify GlobalHotkeyManager key codes and callback dispatch."""
        hotkeys = GlobalHotkeyManager(root_window=None)
        mappings = hotkeys._get_key_mappings()

        self.assertIn(1, mappings)  # Ctrl+Alt+D
        self.assertIn(2, mappings)  # Ctrl+Alt+M
        self.assertIn(3, mappings)  # Ctrl+Alt+C
        self.assertIn(4, mappings)  # Ctrl+Alt+R

        triggered = []
        hotkeys.register(1, mappings[1][0], mappings[1][1], lambda: triggered.append("dual"))
        self.assertIn(1, hotkeys._hotkeys)
        hotkeys._hotkeys[1]()
        self.assertEqual(triggered, ["dual"])

if __name__ == "__main__":
    unittest.main()
