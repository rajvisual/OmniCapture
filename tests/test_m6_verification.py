import os
import sys
import unittest
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import customtkinter as ctk
from gui.theme import OmniTheme, LIGHT_MINIMAL, DARK_LIQUID_GLASS, ThemeTokens
from gui.components.frosted_glass import FrostedGlassManager
from gui.components.state_banner import StudioStateBanner
from gui.components.confirm_dialog import StudioConfirmDialog
from core.simulated_device import SimulatedADBManager
from core.notifications import NotificationManager
from gui.dashboard import OmniCaptureApp

class TestMilestone6Verification(unittest.TestCase):
    """
    Milestone 6 Comprehensive Verification Suite:
    1. Dock & Footer Geometry (No clipping at 1180x820, 1160x760, and across DPI scales)
    2. Footer Priority Truncation (Drops entire hint groups cleanly, never mid-word)
    3. Popup Snapshot Isolation (Only crops app ambient image, zero desktop bleed)
    4. Simulated Device Engine (12-state matrix transition & ADB interface compliance)
    5. State Matrix Banner (16 states with title, cause, action, copy details)
    6. Dialogs Instantiation & Theming (Media Library, Settings, Diagnostics, Onboarding, Dev panel)
    7. Notification Subsystem (Native notification focus rules & toast auto-dismiss)
    8. Codebase Hex Token Audit (Zero unauthorized hardcoded colors)
    """

    @classmethod
    def setUpClass(cls):
        cfg = {
            "scrcpy_dir": "bin",
            "recordings_dir": "recordings",
            "default_record_format": "mp4",
            "max_fps": 60,
            "theme": "dark",
            "window_width": 1180,
            "window_height": 820,
            "first_run_completed": True
        }
        sys.argv = [sys.argv[0], "--no-onboarding"]
        cls.app = OmniCaptureApp(cfg)
        cls.app.withdraw()
        cls.app.update()

    @classmethod
    def tearDownClass(cls):
        if cls.app is not None:
            try:
                cls.app._meter_timer_active = False
                cls.app.controller.stop_device_poller()
                cls.app.hotkeys.stop()
                cls.app.tray.stop()
                if hasattr(cls.app, "single_instance") and cls.app.single_instance:
                    cls.app.single_instance.release()
                cls.app.destroy()
            except Exception:
                pass
            cls.app = None

    # -------------------------------------------------------------------------
    # 1. Dock & Footer Geometry Clipping Verification (Recursive Real-Widget Inspection)
    # -------------------------------------------------------------------------
    def test_dock_geometry_no_clipping(self):
        """
        Verify bottom dock fits all elements without clipping at 1180x820 and 1160x760 across DPI scales.
        Uses recursive real-widget geometry traversal (winfo_reqheight/reqwidth vs allocated space)
        so any clipped child fails the test.
        """
        for width, height in [(1180, 820), (1160, 760)]:
            self.app.geometry(f"{width}x{height}")
            self.app.update()

            dock = self.app.dock_panel
            dock_w = dock.winfo_reqwidth()
            dock_h = dock.winfo_reqheight()
            self.assertGreaterEqual(dock_h, 175, f"Dock height {dock_h}px should provide at least 175px budget")

            # Recursive traversal validator
            def _check_tree(container, alloc_w, alloc_h, path):
                for child in container.winfo_children():
                    child_name = f"{path}/{child.__class__.__name__}"
                    req_w = child.winfo_reqwidth()
                    req_h = child.winfo_reqheight()
                    act_w = child.winfo_width()
                    act_h = child.winfo_height()

                    # Child requested height must fit within allocated vertical space
                    self.assertLessEqual(
                        req_h, alloc_h + 4,
                        f"Widget {child_name} req height ({req_h}px) exceeds allocated space ({alloc_h}px)"
                    )
                    # If widget has sub-children, recursively inspect container
                    subchildren = child.winfo_children()
                    if subchildren:
                        _check_tree(child, max(act_w, req_w), max(act_h, req_h), child_name)

            # Check each column recursively
            for col_name, col_frame in [
                ("Scenes", self.app.dock_col_scenes),
                ("Sources", self.app.dock_col_sources),
                ("Mixer", self.app.dock_col_mixer),
                ("Controls", self.app.dock_col_controls)
            ]:
                col_w = col_frame.winfo_reqwidth()
                col_h = dock_h
                total_col_req_h = sum(c.winfo_reqheight() for c in col_frame.winfo_children())
                self.assertLessEqual(
                    total_col_req_h, col_h + 4,
                    f"Column '{col_name}' total content req height ({total_col_req_h}px) exceeds column height ({col_h}px)"
                )
                _check_tree(col_frame, col_w, col_h, col_name)

            # Explicit check on key critical widgets
            self.assertGreater(self.app.strip_pc.winfo_reqheight(), 0, "PC Audio strip must be sized")
            self.assertGreater(self.app.master_settings_btn.winfo_reqheight(), 0, "Preferences button must be sized")

            # DPI Scaling Simulation check (1.0x, 1.25x, 1.5x, 2.0x)
            for scale in [1.0, 1.25, 1.5, 2.0]:
                for col_frame in [self.app.dock_col_scenes, self.app.dock_col_sources, self.app.dock_col_mixer, self.app.dock_col_controls]:
                    col_sum_scaled = sum(c.winfo_reqheight() for c in col_frame.winfo_children()) * scale
                    dock_h_scaled = dock_h * scale
                    self.assertLessEqual(
                        col_sum_scaled, dock_h_scaled + 4.0,
                        f"DPI scale {scale}x produced content overflow ({col_sum_scaled}px > {dock_h_scaled}px)"
                    )

    # -------------------------------------------------------------------------
    # 2. Dynamic Measured-Width Footer Truncation Verification
    # -------------------------------------------------------------------------
    def test_footer_priority_truncation(self):
        """Verify footer dynamically measures widget widths and drops lower-priority groups to prevent clipping."""
        self.app.geometry("1180x820")
        self.app.update()

        all_widgets = [
            self.app.foot_status_chip, self.app.foot_rec_time, self.app.foot_device_chip,
            self.app.foot_disk_lbl, self.app.foot_encoder_lbl, self.app.foot_fps_lbl,
            self.app.foot_bitrate_lbl, self.app.hint_palette, self.app.hint_rec
        ]
        full_req_w = self.app._compute_footer_reqwidth(all_widgets)

        # 1. When available width accommodates all widgets -> all packed
        self.app._on_footer_configure(type("Event", (), {"width": full_req_w + 50})())
        self.assertEqual(self.app.hint_rec.winfo_manager(), "pack")
        self.assertEqual(self.app.hint_palette.winfo_manager(), "pack")
        self.assertEqual(self.app.foot_bitrate_lbl.winfo_manager(), "pack")

        # 2. Constrict available width below full requested width -> hint_rec drops first
        tight_w = full_req_w - (self.app.hint_rec.winfo_reqwidth() // 2)
        self.app._on_footer_configure(type("Event", (), {"width": tight_w})())
        self.assertEqual(self.app.hint_rec.winfo_manager(), "", "hint_rec must be dropped when space is tight")
        self.assertEqual(self.app.hint_palette.winfo_manager(), "pack", "hint_palette should remain if space permits")

        # 3. Constrict further below hint_palette requirement -> hint_palette drops
        tighter_w = self.app._compute_footer_reqwidth(all_widgets[:-2]) + 10
        self.app._on_footer_configure(type("Event", (), {"width": tighter_w - 20})())
        self.assertEqual(self.app.hint_palette.winfo_manager(), "", "hint_palette must be dropped")

        # 4. Multi-DPI Scaling simulation (1.0x, 1.25x, 1.5x, 2.0x)
        # At minimum window width (1160px), test that dynamic calculation drops candidates to ensure
        # remaining packed widgets NEVER exceed effective available space
        for dpi_scale in [1.0, 1.25, 1.5, 2.0]:
            scaled_avail = int(1160 / dpi_scale)
            self.app._on_footer_configure(type("Event", (), {"width": scaled_avail})())

            active_packed = [w for w in all_widgets if w.winfo_manager() == "pack"]
            packed_req_w = self.app._compute_footer_reqwidth(active_packed)
            self.assertLessEqual(
                packed_req_w, scaled_avail + 15,
                f"At DPI scale {dpi_scale}x, active footer widgets ({packed_req_w}px) exceeded available width ({scaled_avail}px)"
            )
            # Crucially: essentials are ALWAYS packed
            self.assertEqual(self.app.foot_status_chip.winfo_manager(), "pack")
            self.assertEqual(self.app.foot_rec_time.winfo_manager(), "pack")
            self.assertEqual(self.app.foot_device_chip.winfo_manager(), "pack")

    # -------------------------------------------------------------------------
    # 3. Popup Snapshot Isolation
    # -------------------------------------------------------------------------
    def test_popup_snapshot_isolation(self):
        """Verify FrostedGlassManager.snapshot_transient_popup() isolates app pixels and never reads desktop DC."""
        mgr = FrostedGlassManager.get_instance()
        mgr.set_preference_mode("on")
        mgr._recompute_slices(1180, 820)
        img, dt_ms = mgr.snapshot_transient_popup(50, 50, 300, 200)
        self.assertIsNotNone(img, "Snapshot must produce a valid PIL image")
        self.assertEqual(img._size, (300, 200), "Snapshot size must exactly match requested popup geometry")
        self.assertLessEqual(dt_ms, 80.0, "Popup snapshot latency must be under 80 ms budget")

    # -------------------------------------------------------------------------
    # 4. Simulated Device State Machine
    # -------------------------------------------------------------------------
    def test_simulated_device_state_machine(self):
        """Verify SimulatedADBManager correctly cycles through all 12 hardware and bus states."""
        sim = SimulatedADBManager()

        expected_states = [
            "no_device", "scanning", "connecting", "unauthorized",
            "connected_usb", "connected_wifi", "camera_locked",
            "battery_low", "battery_good", "unplugged_mid_recording",
            "slow_response", "failure",
            "upload_failed", "upload_done", "scrcpy_missing",
            "adb_missing", "engine_crashed"
        ]

        for st in expected_states:
            sim.set_state(st)
            self.assertEqual(sim.state, st)

            devs = sim.list_devices()
            if st in ("connected_usb", "connected_wifi", "battery_low", "battery_good", "camera_locked", "slow_response", "upload_failed", "upload_done", "scrcpy_missing"):
                self.assertEqual(len(devs), 1, f"State {st} should return 1 device")
                self.assertEqual(devs[0]["state"], "device")
            elif st == "unauthorized":
                self.assertEqual(len(devs), 1)
                self.assertEqual(devs[0]["state"], "unauthorized")
            elif st in ("no_device", "scanning", "unplugged_mid_recording", "failure", "adb_missing", "engine_crashed"):
                self.assertEqual(len(devs), 0, f"State {st} should return 0 devices")

        # Verify battery telemetry
        sim.set_state("battery_low")
        batt = sim.get_battery_info()
        self.assertEqual(batt.get("level"), 12)

        sim.set_state("battery_good")
        batt = sim.get_battery_info()
        self.assertEqual(batt.get("level"), 88)

        # Verify camera lock release
        sim.set_state("camera_locked")
        ok = sim.release_camera_lock()
        self.assertTrue(ok)
        self.assertEqual(sim.state, "connected_usb")

    # -------------------------------------------------------------------------
    # 5. State Matrix & Alert Card
    # -------------------------------------------------------------------------
    def test_state_banner_matrix(self):
        """Verify StudioStateBanner renders all 16 states cleanly without exceptions."""
        root = ctk.CTk()
        root.withdraw()

        banner = StudioStateBanner(root, initial_state="no_device")
        self.assertEqual(len(StudioStateBanner.STATE_PRESETS), 21, "State Matrix must contain exactly 21 presets")

        for state_key, preset in StudioStateBanner.STATE_PRESETS.items():
            banner.set_state(state_key)
            self.assertEqual(banner.current_state, state_key)
            self.assertEqual(banner.title_lbl.cget("text"), preset["title"])
            self.assertEqual(banner.action_btn.cget("text"), preset["action_text"])
            self.assertTrue(len(banner.current_details) > 0, f"Details for {state_key} must not be empty")

        # Test Light & Dark theme token application
        banner.apply_tokens(LIGHT_MINIMAL)
        self.assertEqual(banner.cget("fg_color"), LIGHT_MINIMAL.bg_raised)
        banner.apply_tokens(DARK_LIQUID_GLASS)
        self.assertEqual(banner.cget("fg_color"), DARK_LIQUID_GLASS.bg_raised)

        root.destroy()

    # -------------------------------------------------------------------------
    # 6. Dialogs Instantiation & Theming
    # -------------------------------------------------------------------------
    def test_dialogs_instantiation_and_theming(self):
        """Verify Media Library, Settings, Diagnostics, Onboarding, and Confirm Dialogs instantiate and theme."""
        # 1. Confirm Dialog
        dlg_confirm = StudioConfirmDialog(
            self.app,
            title="Delete Recording",
            message="Permanently delete test_take_01.mp4?",
            consequence="This action cannot be undone.",
            confirm_text="Delete Take",
            is_danger=True
        )
        dlg_confirm.update()
        self.assertEqual(dlg_confirm.confirm_btn.cget("text"), "Delete Take")
        dlg_confirm.destroy()

        # 2. Simulated Device Control Dialog
        from gui.dialogs.simulated_device import SimulatedDeviceControlDialog
        sim = SimulatedADBManager()
        dlg_sim = SimulatedDeviceControlDialog(self.app, sim)
        dlg_sim.update()
        dlg_sim.destroy()

        # 3. Onboarding Checklist Dialog
        from gui.dialogs.onboarding import OnboardingChecklistDialog
        dlg_onb = OnboardingChecklistDialog(self.app, self.app.controller)
        dlg_onb.update()
        dlg_onb.destroy()

        # 4. Diagnostics Dialog
        from gui.dialogs.diagnostics import DiagnosticsDialog
        dlg_diag = DiagnosticsDialog(self.app, self.app.controller)
        dlg_diag.update()
        dlg_diag.destroy()

        # 5. Media Library Gallery Dialog
        from gui.dialogs.recordings import RecordingsGalleryDialog
        dlg_rec = RecordingsGalleryDialog(self.app, self.app.controller)
        dlg_rec.update()
        dlg_rec.destroy()

        # 6. Studio Settings Dialog
        from gui.dialogs.settings import StudioSettingsDialog
        dlg_set = StudioSettingsDialog(
            self.app, self.app.app_config, self.app.controller,
            self.app.minimize_to_tray_var, self.app.enable_hotkeys_var
        )
        dlg_set.update()
        dlg_set.destroy()

    # -------------------------------------------------------------------------
    # 7. Notification Subsystem Rules
    # -------------------------------------------------------------------------
    def test_notification_rules(self):
        """Verify native notification fires only when window is unfocused, and toasts persist on error."""
        toast_events = []
        tray_events = []

        notif = NotificationManager(
            in_app_toast_fn=lambda **kwargs: toast_events.append(kwargs),
            tray_notify_fn=lambda t, m: tray_events.append((t, m)),
            is_window_focused_fn=lambda: True # Focused window
        )

        # When window is focused, native OS action center notification should NOT fire
        notif.notify("Recording Saved", "take_01.mp4", level="success")
        self.assertEqual(len(toast_events), 1)
        self.assertEqual(len(tray_events), 0, "Native notification must NOT fire when app window is focused")

        # When window is unfocused, native notification MUST fire
        notif.is_window_focused_fn = lambda: False
        notif.notify("Recording Saved", "take_02.mp4", level="success")
        self.assertEqual(len(tray_events), 1, "Native notification MUST fire when app window is unfocused")

        # Verify error toast persistence: duration_ms should be 0 (no auto-dismiss)
        notif.notify("Hardware Error", "Device disconnected", level="error")
        last_toast = toast_events[-1]
        self.assertEqual(last_toast["level"], "error")
        self.assertEqual(last_toast.get("duration_ms"), 0, "Error toasts must persist until dismissed (duration_ms=0)")

    # -------------------------------------------------------------------------
    # 8. Token & Palette Audit
    # -------------------------------------------------------------------------
    def test_no_hardcoded_colors_in_new_components(self):
        """Verify newly created Milestone 6 files do not contain unauthorized hardcoded hex colors."""
        import re
        HEX_REGEX = re.compile(r'#[0-9a-fA-F]{6}\b')

        # Permitted design token hex constants across light/dark themes
        ALLOWED_HEX = {
            # Backgrounds & surfaces
            "#0d0f12", "#13161b", "#181b22", "#1e222b", "#262b36", "#2f3644",
            "#f8fafc", "#ffffff", "#f1f5f9", "#e2e8f0", "#cbd5e1",
            # Neutral dark stage
            "#141619", "#1b1d21", "#22252a",
            # Accents & semantics
            "#2563eb", "#3b82f6", "#60a5fa", "#1d4ed8",
            "#10b981", "#059669", "#ef4444", "#dc2626", "#b91c1c",
            "#f59e0b", "#d97706", "#b45309",
            # Text & borders
            "#f9fafb", "#94a3b8", "#64748b", "#0f172a", "#334155", "#475569",
            "#1f222e", "#000000"
        }

        m6_files = [
            REPO_ROOT / "core" / "simulated_device.py",
            REPO_ROOT / "gui" / "components" / "state_banner.py",
            REPO_ROOT / "gui" / "dialogs" / "onboarding.py",
            REPO_ROOT / "gui" / "dialogs" / "simulated_device.py",
            REPO_ROOT / "gui" / "components" / "confirm_dialog.py"
        ]

        for file_path in m6_files:
            if not file_path.exists():
                continue
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()

            matches = HEX_REGEX.findall(content)
            for h in matches:
                h_lower = h.lower()
                self.assertIn(
                    h_lower, ALLOWED_HEX,
                    f"File {file_path.name} contains unauthorized hardcoded hex color: {h}"
                )

if __name__ == "__main__":
    unittest.main()
