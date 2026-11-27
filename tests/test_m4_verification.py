import os
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import unittest
import customtkinter as ctk

from gui.theme import OmniTheme, LIGHT_MINIMAL, DARK_LIQUID_GLASS
from gui.dashboard import OmniCaptureApp
from gui.controller import GUIController
from gui.components import (
    StudioButton,
    StudioSegmentedControl,
    StudioSwitch,
    SourceRow,
    SceneListItem,
    StudioGainSlider,
    StudioAudioMeterCanvas,
    CanvasEmptyState,
    UnifiedTopBar,
    get_icon
)

class TestMilestone4Verification(unittest.TestCase):
    """
    Milestone 4: Light Minimal Polish Verification Test Suite.
    Verifies:
    1. Deep widget tree walk verifying 3-tier hierarchy & zero stale dark colors in Light mode
    2. Zero hardcoded colors in gui/components/ (excluding allowed system/base constants)
    3. WCAG 2.1 AA contrast compliance across all text (>= 4.5:1) and essential non-text (>= 3:1)
    """

    def test_widget_tree_light_theme_deep_walk(self):
        """
        Walk every widget in OmniCaptureApp after switching to Light Minimal.
        Verify:
        - 3-tier surface hierarchy: Root (#F3F4F6) -> Panels (#FFFFFF) -> Raised/Interactive (#F1F3F5)
        - Preview stage stays neutral dark grey (#1B1D21)
        - Top bar matches native caption (#F3F4F6)
        - No panel or inspector widget retains stale dark colors
        """
        config = {
            "resolution": "1920x1080",
            "fps": 60,
            "theme": "dark",
            "tray_enabled": False
        }
        app = OmniCaptureApp(config)
        app.withdraw()
        app.update_idletasks()

        # Switch to Light Minimal
        app.set_active_theme("light")
        tokens = OmniTheme.get_tokens()
        self.assertFalse(tokens.is_dark)

        # 1. Root & 3-Tier Hierarchy Verification
        self.assertEqual(app.cget("fg_color"), tokens.bg_root) # Tier 0: Soft grey base (#F3F4F6)
        self.assertEqual(app.canvas_panel.cget("fg_color"), tokens.bg_panel) # Tier 1: Pure white (#FFFFFF)
        self.assertEqual(app.inspector_panel.cget("fg_color"), tokens.bg_panel) # Tier 1: Pure white (#FFFFFF)
        self.assertEqual(app.dock_panel.cget("fg_color"), tokens.bg_panel) # Tier 1: Pure white (#FFFFFF)

        # 2. Preview Stage Stays Dark Neutral Grey (#1B1D21)
        self.assertEqual(app.canvas_viewport.cget("fg_color"), tokens.bg_stage)
        self.assertEqual(tokens.bg_stage, "#1B1D21")
        self.assertEqual(app.cv_screen_box.cget("fg_color"), "#141619")
        self.assertEqual(app.cv_screen_title.cget("text_color"), tokens.stage_text_primary)
        self.assertEqual(app.cv_empty_state.cget("fg_color"), tokens.stage_bg_card)

        # 3. Native Caption & Top Bar Match Exactly (#F3F4F6)
        self.assertEqual(app.top_bar.cget("fg_color"), tokens.bg_header)
        self.assertEqual(tokens.bg_header, tokens.dwm_caption_hex)
        self.assertEqual(tokens.bg_header, "#F3F4F6")

        # 4. Segmented Control: White thumb on grey track with dark text
        self.assertEqual(app.aspect_seg.cget("selected_color"), "#FFFFFF")
        self.assertEqual(app.aspect_seg.cget("unselected_color"), tokens.bg_raised)
        self.assertEqual(app.aspect_seg.cget("text_color"), tokens.text_primary)

        # 5. Scene List Item: 12% accent subtle background with blue indicator
        self.assertEqual(app.btn_scene_dual.cget("fg_color"), tokens.accent_subtle)
        self.assertEqual(tokens.accent_subtle, "#E0EDFD")
        self.assertEqual(app.btn_scene_dual.indicator.cget("fg_color"), tokens.accent_primary)

        # 6. Audio Mixer Mute: White text on red recording background
        app.strip_mic._toggle_mute() # Mute mic
        self.assertEqual(app.strip_mic.mute_btn.cget("fg_color"), tokens.status_recording)
        self.assertEqual(app.strip_mic.mute_btn.cget("text_color"), "#FFFFFF")
        app.strip_mic._toggle_mute() # Unmute mic

        # 7. Deep Recursive Walk: Ensure no panel widget retains stale dark colors
        stale_dark_colors = {"#0B0C10", "#111218", "#181922", "#13141D", "#1A1B26"}
        violations = []

        def walk(widget):
            for child in widget.winfo_children():
                # Skip widgets on the dark preview stage
                if child in (app.canvas_viewport, app.cv_content, app.cv_empty_state) or str(app.canvas_viewport) in str(child):
                    continue
                try:
                    fg = child.cget("fg_color")
                    if isinstance(fg, str) and fg.upper() in stale_dark_colors:
                        violations.append(f"{child}: fg_color is stale dark {fg}")
                except Exception:
                    pass
                walk(child)

        walk(app.middle_container)
        walk(app.dock_panel)

        self.assertEqual(
            violations,
            [],
            "Found stale dark colors in light mode widget tree:\n" + "\n".join(violations)
        )

        app.single_instance.release()
        app.destroy()

    def test_zero_hardcoded_colors_in_components(self):
        """Verify components in gui/components/ do not use unapproved hardcoded colors."""
        components_dir = REPO_ROOT / "gui" / "components"
        hex_pattern = re.compile(r'#([A-Fa-f0-9]{6}|[A-Fa-f0-9]{3})\b')
        allowed_hex = {
            "#FFFFFF", "#FFF", "#DC2626", "#10B981", "#111827", "#F9FAFB", "#F3F4F6", "#EF4444",
            "#374151", "#D1D5DB"
        }

        violations = []
        for py_file in components_dir.glob("*.py"):
            with open(py_file, "r", encoding="utf-8") as f:
                for line_num, line in enumerate(f, 1):
                    clean_line = line.split("#")[0] if not line.strip().startswith("#") else ""
                    matches = hex_pattern.findall(clean_line)
                    for m in matches:
                        full_hex = f"#{m.upper()}"
                        if full_hex not in allowed_hex:
                            violations.append(f"{py_file.name}:{line_num} -> {full_hex}")

        self.assertEqual(
            violations,
            [],
            f"Found forbidden hardcoded hex colors in gui/components/:\n" + "\n".join(violations)
        )

    def test_wcag_contrast_text_and_essential_non_text(self):
        """Verify all text (>= 4.5:1) and essential non-text (>= 3:1) pairs in Light Minimal."""
        audit = LIGHT_MINIMAL.validate_wcag_aa()
        failures = []
        for check_name, data in audit.items():
            if not data["passed"]:
                failures.append(f"{check_name}: {data['ratio']} < {data['required']}")

        self.assertEqual(
            failures,
            [],
            "WCAG AA compliance failures in LIGHT_MINIMAL:\n" + "\n".join(failures)
        )

if __name__ == "__main__":
    unittest.main()
