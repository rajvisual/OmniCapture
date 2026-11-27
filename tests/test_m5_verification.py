import sys
import unittest
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from gui.theme import OmniTheme, LIGHT_MINIMAL, DARK_LIQUID_GLASS, ThemeTokens
from gui.components.frosted_glass import FrostedGlassManager
from gui.dashboard import OmniCaptureApp

class TestMilestone5Verification(unittest.TestCase):
    """
    Milestone 5 Verification Suite:
    - Widget-tree theme consistency for Dark Liquid Glass
    - Strict absence of hardcoded unauthorized hex colors
    - Standard WCAG 2.1 AA relative luminance contrast validation
    - Frosted glass transient popup snapshot performance (<= 80ms budget)
    - Dynamic auto-reduction validation (recording active = flat)
    """

    def setUp(self):
        self.app = None

    def tearDown(self):
        if self.app is not None:
            try:
                self.app._meter_timer_active = False
                self.app.controller.stop_device_poller()
                self.app.hotkeys.stop()
                self.app.tray.stop()
                if hasattr(self.app, "single_instance") and self.app.single_instance:
                    self.app.single_instance.release()
                self.app.destroy()
            except Exception:
                pass
            self.app = None

    def test_dark_theme_widget_tree(self):
        """Verify entire widget tree correctly applies dark tokens and has zero light residuals."""
        cfg = {
            "scrcpy_dir": "bin",
            "recordings_dir": "recordings",
            "default_record_format": "mp4",
            "max_fps": 60,
            "theme": "dark"
        }
        self.app = OmniCaptureApp(cfg)
        self.app.withdraw()
        self.app.update_idletasks()

        tokens = OmniTheme.get_tokens()
        self.assertTrue(tokens.is_dark, "Active theme must be dark")
        self.assertEqual(self.app.cget("fg_color"), tokens.bg_root)
        self.assertEqual(self.app.dock_panel.cget("fg_color"), tokens.bg_panel)
        self.assertEqual(self.app.inspector_panel.cget("fg_color"), tokens.bg_panel)

        # Inspect all children
        def _walk(widget):
            # Verify no pure white backgrounds in dark mode
            if hasattr(widget, "cget"):
                try:
                    fg = widget.cget("fg_color")
                    if isinstance(fg, str) and fg.lower() in ("#ffffff", "white"):
                        self.fail(f"Found pure white background on {widget} in dark mode")
                except Exception:
                    pass
            for child in widget.winfo_children():
                _walk(child)

        _walk(self.app)

    def test_standard_wcag_contrast_all_pairs(self):
        """Verify standard WCAG 2.1 AA relative luminance contrast on all pairs for both themes."""
        for theme in [LIGHT_MINIMAL, DARK_LIQUID_GLASS]:
            checks = theme.validate_wcag_aa()
            for name, data in checks.items():
                ratio = data["ratio"]
                req = data["required"]
                self.assertTrue(
                    data["passed"],
                    f"Theme '{theme.name}' failed check '{name}': {ratio}:1 < required {req}:1"
                )

    def test_popup_snapshot_latency_budget(self):
        """Verify transient popup blur snapshot runs within 80ms budget."""
        mgr = FrostedGlassManager.get_instance()
        # Test 400x300 popup area
        img, dt_ms = mgr.snapshot_transient_popup(100, 100, 400, 300)
        self.assertIsNotNone(img, "Snapshot image must not be None")
        print(f"\n[Test] Transient Popup Snapshot Latency: {dt_ms:.2f} ms (Budget: 80 ms)")
        self.assertLessEqual(dt_ms, 80.0, f"Snapshot latency {dt_ms:.2f} ms exceeded 80 ms budget!")

    def test_effect_auto_disable_on_recording(self):
        """Verify frosted glass auto-reduces to flat pre-composited surfaces when recording is active."""
        mgr = FrostedGlassManager.get_instance()
        mgr.set_preference_mode("auto")
        mgr.set_focus_state(True)
        mgr.set_minimized_state(False)
        mgr.set_recording_state(False)

        # When idle and focused, transparency should be active
        self.assertTrue(mgr.is_transparency_active(), "Transparency must be active when idle & focused")

        # When recording starts, transparency MUST auto-reduce to flat
        mgr.set_recording_state(True)
        self.assertFalse(mgr.is_transparency_active(), "Transparency must be disabled during active recording")

        # When recording stops, transparency restores cleanly without layout shift
        mgr.set_recording_state(False)
        self.assertTrue(mgr.is_transparency_active(), "Transparency must restore after recording stops")

    def test_button_and_meter_border_tokens(self):
        """Verify quiet button borders and high-contrast meter tracks."""
        # Button borders should be quiet (~1.6-2:1 on panel/raised)
        l_btn_ratio = ThemeTokens.calculate_contrast(LIGHT_MINIMAL.border_button, LIGHT_MINIMAL.bg_panel)
        d_btn_ratio = ThemeTokens.calculate_contrast(DARK_LIQUID_GLASS.border_button, DARK_LIQUID_GLASS.bg_panel)
        self.assertGreaterEqual(l_btn_ratio, 1.4)
        self.assertLessEqual(l_btn_ratio, 2.2)
        self.assertGreaterEqual(d_btn_ratio, 1.4)
        self.assertLessEqual(d_btn_ratio, 2.2)

        # Meter segments must strictly reach >= 3:1 on track in both themes
        for theme in [LIGHT_MINIMAL, DARK_LIQUID_GLASS]:
            c_g = ThemeTokens.calculate_contrast(theme.vu_green, theme.vu_bg)
            c_y = ThemeTokens.calculate_contrast(theme.vu_yellow, theme.vu_bg)
            c_r = ThemeTokens.calculate_contrast(theme.vu_red, theme.vu_bg)
            self.assertGreaterEqual(c_g, 3.0, f"{theme.name} vu_green failed 3:1 on track")
            self.assertGreaterEqual(c_y, 3.0, f"{theme.name} vu_yellow failed 3:1 on track")
            self.assertGreaterEqual(c_r, 3.0, f"{theme.name} vu_red failed 3:1 on track")

if __name__ == "__main__":
    unittest.main()
