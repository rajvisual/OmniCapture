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

    def test_theme_tokens_extended(self):
        """Verify extended design tokens, spacing scale, and font factories."""
        self.assertEqual(OmniTheme.SPACE_XS, 4)
        self.assertEqual(OmniTheme.SPACE_SM, 8)
        self.assertEqual(OmniTheme.SPACE_MD, 12)
        self.assertEqual(OmniTheme.SPACE_LG, 16)
        self.assertIn(OmniTheme.RADIUS_CONTROL, (4, 8))

        self.assertTrue(OmniTheme.VU_GREEN.startswith("#"))
        self.assertTrue(OmniTheme.VU_YELLOW.startswith("#"))
        self.assertTrue(OmniTheme.VU_RED.startswith("#"))

        self.assertIsNotNone(OmniTheme.font_title())
        self.assertIsNotNone(OmniTheme.font_section())
        self.assertIsNotNone(OmniTheme.font_body())
        self.assertIsNotNone(OmniTheme.font_mono())

    def test_theme_switching_and_tokens(self):
        """Verify runtime theme switching between Light Minimal and Dark Liquid Glass."""
        OmniTheme.set_theme("light")
        tokens_light = OmniTheme.get_tokens()
        self.assertEqual(tokens_light.name, "light")
        self.assertFalse(tokens_light.is_dark)
        self.assertEqual(OmniTheme.BG_ROOT, tokens_light.bg_root)
        self.assertEqual(OmniTheme.BLUR_RADIUS, 0)
        self.assertEqual(OmniTheme.NOISE_OPACITY, 0.0)

        OmniTheme.set_theme("dark")
        tokens_dark = OmniTheme.get_tokens()
        self.assertEqual(tokens_dark.name, "dark")
        self.assertTrue(tokens_dark.is_dark)
        self.assertEqual(OmniTheme.BG_ROOT, tokens_dark.bg_root)
        self.assertTrue(OmniTheme.SURFACE_GLASS.startswith("#"))
        self.assertEqual(OmniTheme.BLUR_RADIUS, 28)
        self.assertGreater(OmniTheme.NOISE_OPACITY, 0.0)

    def test_wcag_aa_contrast_all_token_pairs(self):
        """Verify WCAG AA contrast compliance across all foreground/background token pairs."""
        from gui.theme import LIGHT_MINIMAL, DARK_LIQUID_GLASS

        for theme in [LIGHT_MINIMAL, DARK_LIQUID_GLASS]:
            audit = theme.validate_wcag_aa()
            for check_name, data in audit.items():
                self.assertTrue(
                    data["passed"],
                    f"Theme {theme.name} failed WCAG AA check '{check_name}': ratio {data['ratio']} < required {data['required']}"
                )

    def test_components_and_dialogs_import(self):
        """Verify all desktop components and dialogs are importable and exposed."""
        from gui import (
            AudioChannelStrip,
            ToastNotificationManager,
            CommandPalette,
            OmniCaptureApp,
        )
        from gui.components import (
            StatusChip,
            CanvasEmptyState,
            UnifiedTopBar,
            MenuDropdown,
        )
        from gui.dwm import DWMManager
        from gui.dialogs import (
            RecordingsGalleryDialog,
            StudioSettingsDialog,
            DiagnosticsDialog,
        )
        self.assertIsNotNone(AudioChannelStrip)
        self.assertIsNotNone(ToastNotificationManager)
        self.assertIsNotNone(CommandPalette)
        self.assertIsNotNone(OmniCaptureApp)
        self.assertIsNotNone(StatusChip)
        self.assertIsNotNone(CanvasEmptyState)
        self.assertIsNotNone(UnifiedTopBar)
        self.assertIsNotNone(MenuDropdown)
        self.assertIsNotNone(DWMManager)
        self.assertIsNotNone(RecordingsGalleryDialog)
        self.assertIsNotNone(StudioSettingsDialog)
        self.assertIsNotNone(DiagnosticsDialog)

    def test_settings_manager_and_geometry_clamping(self):
        """Verify settings persistence and multi-monitor window geometry clamping."""
        from core.settings_manager import SettingsManager, clamp_window_geometry

        settings = SettingsManager.load()
        self.assertIsInstance(settings, dict)
        self.assertIn("window_width", settings)
        self.assertIn("window_height", settings)

        # Off-screen clamping tests (e.g. disconnected external display)
        cx, cy, cw, ch = clamp_window_geometry(-9999, -9999, 1180, 800)
        self.assertGreaterEqual(cx, 0)
        self.assertGreaterEqual(cy, 0)
        self.assertGreaterEqual(cw, 1100)
        self.assertGreaterEqual(ch, 720)

    def test_single_instance_manager(self):
        """Verify SingleInstanceManager Win32 named mutex acquire and release."""
        from gui.single_instance import SingleInstanceManager

        manager = SingleInstanceManager(mutex_name="Global\\OmniCapture_Test_Mutex_123")
        ok = manager.acquire()
        self.assertTrue(ok)
        manager.release()

    def test_widget_tree_color_compliance_on_theme_switch(self):
        """Walk the entire widget tree after theme switch to verify all widgets match active tokens."""
        from gui.dashboard import OmniCaptureApp
        from gui.theme import LIGHT_MINIMAL, DARK_LIQUID_GLASS

        # Create hidden test instance
        app = OmniCaptureApp(self.sample_config)
        app.withdraw()
        app.update_idletasks()

        try:
            # 1. Switch to Light Minimal
            app.set_active_theme("light")
            app.update_idletasks()
            light_tokens = LIGHT_MINIMAL

            # Verify key panels match Light tokens
            self.assertEqual(app.cget("fg_color"), light_tokens.bg_root)
            self.assertEqual(app.canvas_panel.cget("fg_color"), light_tokens.bg_panel)
            self.assertEqual(app.inspector_panel.cget("fg_color"), light_tokens.bg_panel)
            self.assertEqual(app.insp_header.cget("fg_color"), light_tokens.bg_header)
            self.assertEqual(app.dock_panel.cget("fg_color"), light_tokens.bg_panel)
            self.assertEqual(app.footer.cget("fg_color"), light_tokens.bg_header)

            # Verify dock titles and labels in Light Minimal
            self.assertEqual(app.dock_title_scenes.cget("text_color"), light_tokens.text_primary)
            self.assertEqual(app.dock_title_sources.cget("text_color"), light_tokens.text_primary)
            self.assertEqual(app.dock_title_mixer.cget("text_color"), light_tokens.text_primary)
            self.assertEqual(app.dock_title_controls.cget("text_color"), light_tokens.text_primary)
            self.assertEqual(app.lbl_insp_cam.cget("text_color"), light_tokens.text_muted)

            def walk_widgets(widget):
                for c in widget.winfo_children():
                    yield c
                    yield from walk_widgets(c)

            # Verify no widget retained dark panel colors in Light mode
            for w in walk_widgets(app):
                if hasattr(w, "cget"):
                    try:
                        fg = w.cget("fg_color")
                        if fg and isinstance(fg, str) and fg.startswith("#"):
                            self.assertNotIn(
                                fg.upper(),
                                ["#111218", "#191A23"],
                                f"Widget {w} retained dark background {fg} in Light mode"
                            )
                    except Exception:
                        pass

            # 2. Switch to Dark Liquid Glass
            app.set_active_theme("dark")
            app.update_idletasks()
            dark_tokens = DARK_LIQUID_GLASS

            self.assertEqual(app.cget("fg_color"), dark_tokens.bg_root)
            self.assertEqual(app.canvas_panel.cget("fg_color"), dark_tokens.bg_panel)
            self.assertEqual(app.inspector_panel.cget("fg_color"), dark_tokens.bg_panel)
            self.assertEqual(app.insp_header.cget("fg_color"), dark_tokens.bg_header)
            self.assertEqual(app.dock_panel.cget("fg_color"), dark_tokens.bg_panel)
            self.assertEqual(app.footer.cget("fg_color"), dark_tokens.bg_header)

            self.assertEqual(app.dock_title_scenes.cget("text_color"), dark_tokens.text_primary)
            self.assertEqual(app.dock_title_sources.cget("text_color"), dark_tokens.text_primary)
            self.assertEqual(app.dock_title_mixer.cget("text_color"), dark_tokens.text_primary)
            self.assertEqual(app.dock_title_controls.cget("text_color"), dark_tokens.text_primary)
            self.assertEqual(app.lbl_insp_cam.cget("text_color"), dark_tokens.text_muted)

            # Verify no widget retained light panel colors in Dark mode
            for w in walk_widgets(app):
                if hasattr(w, "cget"):
                    try:
                        fg = w.cget("fg_color")
                        if fg and isinstance(fg, str) and fg.startswith("#"):
                            self.assertNotIn(
                                fg.upper(),
                                ["#FFFFFF", "#F9FAFB"],
                                f"Widget {w} retained light background {fg} in Dark mode"
                            )
                    except Exception:
                        pass
        finally:
            try:
                app._meter_timer_active = False
                app.controller.stop_device_poller()
                app.hotkeys.stop()
                app.tray.stop()
                app.single_instance.release()
                app.destroy()
            except Exception:
                pass


if __name__ == "__main__":
    unittest.main()
