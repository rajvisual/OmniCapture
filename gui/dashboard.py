import os
import sys
import time
import shutil
import subprocess
import threading
from pathlib import Path
from typing import Optional, Dict, Any, List
import tkinter as tk
from tkinter import messagebox

import customtkinter as ctk
from PIL import Image

from gui.theme import OmniTheme, ThemeTokens
from gui.dwm import DWMManager
from gui.controller import GUIController
from gui.tray import SystemTrayManager
from gui.hotkeys import GlobalHotkeyManager
from gui.single_instance import SingleInstanceManager
from gui.taskbar import TaskbarManager
from core.settings_manager import SettingsManager, clamp_window_geometry
from core.notifications import NotificationManager
from gui.components.top_bar import UnifiedTopBar
from gui.components.audio_meter import AudioChannelStrip
from gui.components.status_chip import StatusChip
from gui.components.empty_state import CanvasEmptyState
from gui.components.toast import ToastNotificationManager
from gui.components.command_palette import CommandPalette
from gui.components.state_banner import StudioStateBanner
from gui.components import (
    StudioButton,
    StudioSegmentedControl,
    StudioSwitch,
    SourceRow,
    SceneListItem,
    get_icon
)
# Lazy-loaded dialogs imported in their respective opener methods to optimize cold-start
from core.resource_path import resolve_resource, get_base_dir, get_recordings_dir

class OmniCaptureApp(ctk.CTk):
    """
    OmniCapture Broadcast Studio — Professional Windows 11 Desktop Application.
    Designed according to OBS Studio, DaVinci Resolve, and Fluent / Windows 11 design guidelines:
    - Unified Custom Top Bar with In-App Menus (eliminates white native menu clash)
    - 3-Level Surface Hierarchy (App Background, Panels, Raised Controls)
    - Windows 11 DWM Integration (Immersive Dark/Light mode, caption sync, rounded corners, Mica)
    - Two Complete Themes: Light Minimal & Dark Liquid Glass with runtime theme switching
    - Designed Canvas Empty State with scan action
    - Professional DAW Audio Strips with dB scale and smooth VU meters
    - Command Palette (Ctrl+P / Ctrl+Shift+P) for fast keyboard navigation
    - Real-time Broadcast Telemetry status bar
    """

    def __init__(self, config: Dict[str, Any]):
        # Enforce explicit Windows AppUserModelID for taskbar grouping & icon
        TaskbarManager.set_app_user_model_id("OmniCapture.Studio.Desktop.1.4.dev")

        # Single instance enforcement via Win32 named mutex
        self.single_instance = SingleInstanceManager()
        if not self.single_instance.acquire() and "unittest" not in sys.modules:
            print("[OmniCapture] Another instance is already running. Focusing existing window.")
            sys.exit(0)

        super().__init__()

        self.app_config = config
        self.controller = GUIController(config)
        self._connected_device_id: Optional[str] = None
        self._old_wndproc = None
        self._c_wndproc = None

        # Load persistent user settings from %APPDATA%/OmniCapture/settings.json
        self.settings = SettingsManager.load()
        for k, v in self.settings.items():
            if k not in self.app_config or self.app_config[k] is None:
                self.app_config[k] = v

        # Active Studio Scene / Preset: "dual" | "mirror" | "camera" | "screen"
        self.active_scene = "dual"
        self.show_guides = self.settings.get("show_guides", True)

        # Initial theme setup (detect system theme on first launch if not configured)
        saved_theme = self.app_config.get("theme") or self.settings.get("theme")
        if not saved_theme:
            saved_theme = OmniTheme.detect_system_theme()
            self.app_config["theme"] = saved_theme
        OmniTheme.set_theme(saved_theme)

        # Appearance & Window Configuration
        tokens = OmniTheme.get_tokens()
        self.title("OmniCapture Studio")
        self.minsize(1160, 760)
        self._restore_window_geometry()
        self.configure(fg_color=tokens.bg_root)

        self._set_app_icon()

        # Apply Windows 11 DWM Attributes (Caption color, Dark Mode, Rounded corners, Mica)
        self.after(50, self._apply_dwm)

        # In-App Toast Notification Engine (Bottom-Right positioned, auto-dismiss 3s)
        self.toasts = ToastNotificationManager(self)

        # Taskbar COM Manager (ITaskbarList3 progress states)
        self.taskbar = TaskbarManager(hwnd=None)
        self.after(200, self._init_taskbar_hwnd)

        # System Preferences
        self.minimize_to_tray_var = ctk.BooleanVar(value=self.settings.get("minimize_to_tray", True))
        self.enable_hotkeys_var = ctk.BooleanVar(value=self.settings.get("enable_hotkeys", True))

        # System Tray Integration
        self.tray = SystemTrayManager(
            on_show=self._show_window,
            on_exit=self._on_app_exit,
            on_dual_record=self._on_hotkey_dual_record,
            on_mirror=self._on_hotkey_mirror,
            on_camera=self._on_hotkey_camera,
            on_open_recordings=self.controller.open_recordings_folder
        )

        # Unified Notification Subsystem (Native Windows Action Center + In-App glass toasts)
        self.notifications = NotificationManager(
            in_app_toast_fn=self.toasts.show,
            tray_notify_fn=self.tray.notify
        )

        # Global System Hotkeys Manager
        self.hotkeys = GlobalHotkeyManager(root_window=self)
        self._setup_hotkeys()

        # Timers & Animation States
        self._meter_timer_active = False
        self._recording_pulse_active = False
        self._pulse_phase = 0

        # Simulated Device Engine (developer mode via --demo-device or Tools menu)
        self._sim_engine = None
        if "--demo-device" in sys.argv or "--simulated-device" in sys.argv:
            from core.simulated_device import SimulatedADBManager
            self._sim_engine = SimulatedADBManager()
            self.controller.set_simulated_device_manager(self._sim_engine)

        # Build Full Studio Architecture in proper Tk pack order:
        # Top bar -> Status footer -> Production dock -> Center canvas (absorbs remaining flex)
        self._build_top_bar()
        if self._sim_engine:
            self.top_bar.set_simulated_mode(True)
        self._build_status_footer()
        self._build_bottom_production_dock()
        self._build_center_and_inspector()

        # Keyboard Accelerators & Alt-Key Mnemonics
        self._bind_keyboard_shortcuts()

        # Wire window events & device poller
        self.protocol("WM_DELETE_WINDOW", self._on_window_close)
        self.controller.register_device_listener(self._on_device_state_changed)

        # Frosted glass engine integration (zero per-frame work)
        from gui.components.frosted_glass import FrostedGlassManager
        self.frosted_glass = FrostedGlassManager.get_instance(self)
        if "glass_effects" in self.app_config:
            self.frosted_glass.set_preference_mode(self.app_config["glass_effects"])
        self.bind("<Configure>", self._on_window_configure, add="+")
        self.bind("<FocusIn>", lambda e: self.frosted_glass.set_focus_state(True), add="+")
        self.bind("<FocusOut>", lambda e: self.frosted_glass.set_focus_state(False), add="+")

        # Defer background threads and hardware probes to after first paint for fast cold start (< 1200ms)
        self.after(100, self._start_audio_level_animation)
        self.after(150, self._deferred_background_init)
        self.after(250, self._initial_refresh)
        if not self.settings.get("first_run_completed", False) and "unittest" not in sys.modules:
            self.after(600, self._check_first_run_onboarding)

    def _deferred_background_init(self):
        try:
            self.tray.start()
        except Exception:
            pass
        if self.enable_hotkeys_var.get():
            try:
                self.hotkeys.start()
            except Exception:
                pass
        try:
            self.controller.start_device_poller(interval_sec=2.5)
        except Exception:
            pass
        self._refresh_encoder_chip()

    def _on_window_configure(self, event):
        if event.widget == self:
            self.frosted_glass.on_window_resized(event.width, event.height)

    def _init_taskbar_hwnd(self):
        try:
            self.taskbar.hwnd = self.winfo_id()
            self._install_wndproc_hook()
        except Exception:
            pass

    def _install_wndproc_hook(self):
        """Install Win32 subclass procedure to safely finalize active recordings on OS shutdown/logoff."""
        if sys.platform != "win32":
            return
        try:
            import ctypes
            from ctypes import wintypes
            WM_QUERYENDSESSION = 0x0011
            WM_ENDSESSION = 0x0016
            GWLP_WNDPROC = -4

            WNDPROC = ctypes.WINFUNCTYPE(ctypes.c_ssize_t, wintypes.HWND, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM)

            CallWindowProc = ctypes.windll.user32.CallWindowProcW
            CallWindowProc.restype = ctypes.c_ssize_t
            CallWindowProc.argtypes = [ctypes.c_void_p, wintypes.HWND, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM]

            def _py_wndproc(hwnd, msg, wparam, lparam):
                if msg in (WM_QUERYENDSESSION, WM_ENDSESSION):
                    try:
                        if self.controller.is_dual_recording():
                            self.controller.stop_dual_recording()
                    except Exception:
                        pass
                    return 1
                return CallWindowProc(ctypes.c_void_p(self._old_wndproc), hwnd, msg, wparam, lparam)

            self._c_wndproc = WNDPROC(_py_wndproc)
            SetWindowLongPtr = ctypes.windll.user32.SetWindowLongPtrW
            SetWindowLongPtr.restype = ctypes.c_ssize_t
            SetWindowLongPtr.argtypes = [wintypes.HWND, ctypes.c_int, ctypes.c_ssize_t]

            proc_addr = ctypes.cast(self._c_wndproc, ctypes.c_void_p).value
            self._old_wndproc = SetWindowLongPtr(self.winfo_id(), GWLP_WNDPROC, proc_addr)
        except Exception:
            pass

    def _uninstall_wndproc_hook(self):
        """Restore default Win32 window procedure."""
        if sys.platform == "win32" and hasattr(self, "_old_wndproc") and self._old_wndproc:
            try:
                import ctypes
                from ctypes import wintypes
                GWLP_WNDPROC = -4
                SetWindowLongPtr = ctypes.windll.user32.SetWindowLongPtrW
                SetWindowLongPtr.restype = ctypes.c_ssize_t
                SetWindowLongPtr.argtypes = [wintypes.HWND, ctypes.c_int, ctypes.c_ssize_t]
                SetWindowLongPtr(self.winfo_id(), GWLP_WNDPROC, self._old_wndproc)
                self._old_wndproc = None
            except Exception:
                pass

    def _apply_dwm(self):
        tokens = OmniTheme.get_tokens()
        DWMManager.apply_theme(
            self,
            dark_mode=tokens.is_dark,
            caption_color_hex=tokens.dwm_caption_hex,
            text_color_hex=tokens.dwm_text_hex,
            backdrop_type=tokens.dwm_backdrop_type
        )

    def _restore_window_geometry(self):
        w = self.settings.get("window_width") or self.app_config.get("window_width", 1180)
        h = self.settings.get("window_height") or self.app_config.get("window_height", 820)
        x = self.settings.get("window_x") if self.settings.get("window_x") is not None else self.app_config.get("window_x")
        y = self.settings.get("window_y") if self.settings.get("window_y") is not None else self.app_config.get("window_y")

        clamped_x, clamped_y, clamped_w, clamped_h = clamp_window_geometry(x, y, w, h, min_w=1160, min_h=760)
        self.geometry(f"{clamped_w}x{clamped_h}+{clamped_x}+{clamped_y}")

        if self.settings.get("is_maximized"):
            self.after(100, lambda: self.state("zoomed"))

    def _save_window_geometry(self):
        try:
            is_max = (self.state() == "zoomed")
            self.settings["is_maximized"] = is_max
            if not is_max:
                self.settings["window_width"] = self.winfo_width()
                self.settings["window_height"] = self.winfo_height()
                self.settings["window_x"] = self.winfo_x()
                self.settings["window_y"] = self.winfo_y()
                self.app_config["window_width"] = self.winfo_width()
                self.app_config["window_height"] = self.winfo_height()
                self.app_config["window_x"] = self.winfo_x()
                self.app_config["window_y"] = self.winfo_y()
            self.settings["theme"] = OmniTheme.get_tokens().name
            SettingsManager.save(self.settings)
        except Exception:
            pass

    def _set_app_icon(self):
        ico_path = resolve_resource("assets/logo/omnicapture.ico")
        if ico_path.is_file():
            try:
                self.iconbitmap(str(ico_path))
            except Exception:
                pass

    # -------------------------------------------------------------------------
    # 1. UNIFIED CUSTOM TOP BAR (Replaces clashing white Win32 menu bar)
    # -------------------------------------------------------------------------

    def _build_top_bar(self):
        menu_handlers = {
            "open_recordings_folder": self.controller.open_recordings_folder,
            "open_recordings_gallery": self._open_recordings_window,
            "open_settings": self._open_settings_window,
            "minimize_to_tray": self._on_minimize_to_tray,
            "exit_app": self._on_app_exit,
            "start_dual_record": self._on_master_record_click,
            "launch_mirror": self._on_launch_mirror,
            "launch_camera": self._on_start_camera_recording,
            "start_screen_record": self._on_start_screen_recording,
            "stop_active_recording": self._on_stop_dual_recording,
            "open_command_palette": self._open_command_palette,
            "release_camera_lock": self._on_release_lock,
            "switch_wireless_adb": self._on_switch_to_wireless,
            "refresh_devices": self._on_manual_refresh,
            "open_diagnostics": self._open_diagnostics_window,
            "switch_scene": self._select_scene,
            "reset_window_size": self._reset_window_size,
            "open_hotkeys_guide": self._open_hotkeys_guide,
            "open_gallery": self._open_component_gallery,
            "open_about": self._open_about_dialog,
            "open_simulated_device": self._open_simulated_device_dialog,
            "open_onboarding": self._open_onboarding_dialog,
        }

        self.top_bar = UnifiedTopBar(
            self,
            menu_handlers=menu_handlers,
            on_open_palette=self._open_command_palette,
            on_refresh=self._on_manual_refresh,
            on_release_lock=self._on_release_lock,
            on_toggle_theme=self._toggle_theme
        )
        self.top_bar.pack(fill="x", side="top")

    # -------------------------------------------------------------------------
    # 2. CENTER STAGE (16:9 Canvas Viewport) & RIGHT INSPECTOR
    # -------------------------------------------------------------------------

    def _build_center_and_inspector(self):
        tokens = OmniTheme.get_tokens()

        self.middle_container = ctk.CTkFrame(self, fg_color="transparent", corner_radius=0)
        self.middle_container.pack(fill="both", expand=True, padx=OmniTheme.SPACE_12, pady=(OmniTheme.SPACE_8, OmniTheme.SPACE_6))

        self.middle_container.columnconfigure(0, weight=3) # Canvas Viewport
        self.middle_container.columnconfigure(1, weight=1) # Inspector Panel
        self.middle_container.rowconfigure(0, weight=1)

        # -----------------------------
        # A. STUDIO LIVE CANVAS (Panel Level 2)
        # -----------------------------
        self.canvas_panel = ctk.CTkFrame(
            self.middle_container,
            fg_color=tokens.bg_panel,
            corner_radius=OmniTheme.RADIUS_PANEL,
            border_width=1,
            border_color=tokens.border_subtle
        )
        self.canvas_panel.grid(row=0, column=0, sticky="nsew", padx=(0, OmniTheme.SPACE_8))

        # Canvas Top Control Bar
        canvas_top = ctk.CTkFrame(self.canvas_panel, fg_color="transparent", height=36)
        canvas_top.pack(fill="x", padx=OmniTheme.SPACE_16, pady=OmniTheme.SPACE_12)

        self.canvas_mode_lbl = ctk.CTkLabel(
            canvas_top,
            text="Preview: Dual Recording",
            font=OmniTheme.font_section(),
            text_color=tokens.text_primary
        )
        self.canvas_mode_lbl.pack(side="left")

        # Aspect & Guides Toolstrip
        toolstrip = ctk.CTkFrame(canvas_top, fg_color="transparent")
        toolstrip.pack(side="right")

        self.aspect_seg = StudioSegmentedControl(
            toolstrip,
            values=["16:9", "9:16", "Fit"],
            command=self._on_aspect_changed
        )
        self.aspect_seg.set("16:9")
        self.aspect_seg.pack(side="left", padx=(0, 10))

        self.canvas_stats_lbl = ctk.CTkLabel(
            toolstrip,
            text="1920x1080  ·  60 FPS  ·  Low-Latency NVMe",
            font=OmniTheme.font_mono(10),
            text_color=tokens.text_dim
        )
        self.canvas_stats_lbl.pack(side="left")

        # 16-State Alert Banner & Diagnostic Action Card
        self.state_banner = StudioStateBanner(
            self.canvas_panel,
            initial_state="no_device",
            on_action=self._on_banner_action,
            on_copy_details=lambda details: self.toasts.show("Diagnostics", "Details copied to clipboard", level="info")
        )
        self.state_banner.pack(fill="x", padx=OmniTheme.SPACE_16, pady=(0, OmniTheme.SPACE_8))

        # 16:9 Viewport Box (Level 1 Surface - Stays neutral dark grey #1B1D21 in all themes)
        self.canvas_viewport = ctk.CTkFrame(
            self.canvas_panel,
            fg_color=tokens.bg_stage,
            border_width=1,
            border_color=tokens.border_stage,
            corner_radius=OmniTheme.RADIUS_CONTROL
        )
        self.canvas_viewport.pack(fill="both", expand=True, padx=OmniTheme.SPACE_16, pady=(0, OmniTheme.SPACE_16))

        # Viewfinder Elements & Empty State
        self._build_canvas_visualizer(tokens)

        # -----------------------------
        # B. PROPERTIES INSPECTOR (Panel Level 2)
        # -----------------------------
        self.inspector_panel = ctk.CTkFrame(
            self.middle_container,
            fg_color=tokens.bg_panel,
            corner_radius=OmniTheme.RADIUS_PANEL,
            border_width=1,
            border_color=tokens.border_subtle
        )
        self.inspector_panel.grid(row=0, column=1, sticky="nsew")

        self.insp_header = ctk.CTkFrame(self.inspector_panel, fg_color=tokens.bg_header, height=36, corner_radius=0)
        self.insp_header.pack(fill="x")
        self.insp_title_lbl = ctk.CTkLabel(
            self.insp_header,
            text="Properties",
            font=OmniTheme.font_section(),
            text_color=tokens.text_primary
        )
        self.insp_title_lbl.pack(side="left", padx=OmniTheme.SPACE_16, pady=8)

        # Scrollable form content
        self.insp_scroll = ctk.CTkScrollableFrame(self.inspector_panel, fg_color="transparent")
        self.insp_scroll.pack(fill="both", expand=True, padx=OmniTheme.SPACE_12, pady=OmniTheme.SPACE_8)

        self._build_inspector_properties(tokens)

    def _build_canvas_visualizer(self, tokens: ThemeTokens):
        """Construct both the active scene representation and the designed empty state."""
        # 1. Designed Empty State (Shown when no device is connected)
        self.cv_empty_state = CanvasEmptyState(
            self.canvas_viewport,
            on_refresh=self._on_manual_refresh,
            on_diagnostics=self._open_diagnostics_window
        )
        self.cv_empty_state.place(relx=0.5, rely=0.5, anchor="center", relwidth=0.85, relheight=0.7)

        # 2. Active Scene Viewport Representation
        self.cv_content = ctk.CTkFrame(self.canvas_viewport, fg_color="transparent")
        # Hidden initially until device is connected
        # self.cv_content.place(relx=0.5, rely=0.5, anchor="center")

        self.cv_screen_box = ctk.CTkFrame(
            self.cv_content,
            fg_color="#141619",
            border_width=1,
            border_color=tokens.stage_border_card,
            width=380,
            height=214,
            corner_radius=OmniTheme.RADIUS_CONTROL
        )
        self.cv_screen_box.pack(pady=4)
        self.cv_screen_box.pack_propagate(False)

        # Safe area guide frame
        self.cv_guide_box = ctk.CTkFrame(
            self.cv_screen_box,
            fg_color="transparent",
            border_width=1,
            border_color=tokens.border_subtle
        )
        self.cv_guide_box.place(relx=0.05, rely=0.05, relwidth=0.9, relheight=0.9)

        # Center crosshair marker
        self.cv_crosshair = ctk.CTkLabel(
            self.cv_screen_box,
            text="+",
            font=OmniTheme.font_headline(),
            text_color=tokens.text_dim
        )
        self.cv_crosshair.place(relx=0.5, rely=0.5, anchor="center")

        self.cv_screen_title = ctk.CTkLabel(
            self.cv_screen_box,
            text="PC Primary Display (Direct3D 11)",
            font=OmniTheme.font_section(),
            text_color=tokens.stage_text_primary
        )
        self.cv_screen_title.pack(anchor="center", pady=(60, 4))

        self.cv_screen_sub = ctk.CTkLabel(
            self.cv_screen_box,
            text="1920x1080 @ 60 FPS",
            font=OmniTheme.font_mono(10),
            text_color=tokens.stage_text_muted
        )
        self.cv_screen_sub.pack(anchor="center")

        # PiP Mobile Camera Box (Dual mode)
        self.cv_pip_box = ctk.CTkFrame(
            self.cv_screen_box,
            fg_color=tokens.stage_bg_card,
            border_width=1,
            border_color=tokens.accent_primary,
            width=105,
            height=70,
            corner_radius=4
        )
        self.cv_pip_box.place(relx=0.96, rely=0.94, anchor="se")
        self.cv_pip_box.pack_propagate(False)

        self.cv_pip_lbl = ctk.CTkLabel(
            self.cv_pip_box,
            text="Camera2 Sensor",
            font=OmniTheme.font_caption(),
            text_color=tokens.stage_text_primary
        )
        self.cv_pip_lbl.pack(expand=True)

        # PiP Dragging and Corner Snapping
        for w in [self.cv_pip_box, self.cv_pip_lbl]:
            w.bind("<Button-1>", self._on_pip_drag_start, add="+")
            w.bind("<B1-Motion>", self._on_pip_drag_motion, add="+")
            w.bind("<ButtonRelease-1>", self._on_pip_drag_end, add="+")

        # Active Recording Tally HUD
        self.cv_recording_hud = ctk.CTkFrame(
            self.canvas_viewport,
            fg_color=tokens.stage_bg_card,
            corner_radius=OmniTheme.RADIUS_CONTROL,
            border_width=1,
            border_color=tokens.status_recording
        )

        hud_row = ctk.CTkFrame(self.cv_recording_hud, fg_color="transparent")
        hud_row.pack(padx=16, pady=8)

        self.cv_tally_dot = ctk.CTkLabel(
            hud_row,
            text="● Rec",
            font=OmniTheme.font_meta(),
            text_color=tokens.status_recording
        )
        self.cv_tally_dot.pack(side="left", padx=(0, 10))

        self.cv_tally_timer = ctk.CTkLabel(
            hud_row,
            text="00:00:00",
            font=OmniTheme.font_mono(12, weight="bold"),
            text_color=tokens.text_primary
        )
        self.cv_tally_timer.pack(side="left", padx=(0, 16))

        self.cv_tally_stats = ctk.CTkLabel(
            hud_row,
            text="PC: 0.0 MB  ·  Cam: 0.0 MB",
            font=OmniTheme.font_mono(10),
            text_color=tokens.text_muted
        )
        self.cv_tally_stats.pack(side="left")

    def _on_aspect_changed(self, choice: str):
        if choice == "9:16":
            self.cv_screen_box.configure(width=160, height=284)
            self.cv_pip_box.place_forget()
        elif choice == "Fit":
            self.cv_screen_box.configure(width=420, height=236)
            if self.active_scene == "dual":
                self.cv_pip_box.place(relx=0.96, rely=0.94, anchor="se")
        else:
            self.cv_screen_box.configure(width=380, height=214)
            if self.active_scene == "dual":
                self.cv_pip_box.place(relx=0.96, rely=0.94, anchor="se")

    def _on_pip_drag_start(self, event):
        self._pip_drag_data = {"x": event.x, "y": event.y}

    def _on_pip_drag_motion(self, event):
        if not hasattr(self, "_pip_drag_data"):
            return
        dx = event.x - self._pip_drag_data["x"]
        dy = event.y - self._pip_drag_data["y"]
        cur_x = self.cv_pip_box.winfo_x() + dx
        cur_y = self.cv_pip_box.winfo_y() + dy
        self.cv_pip_box.place(x=cur_x, y=cur_y, relx=0, rely=0, anchor="nw")

    def _on_pip_drag_end(self, event):
        if not hasattr(self, "_pip_drag_data"):
            return
        del self._pip_drag_data
        import math
        parent_w = max(1, self.cv_screen_box.winfo_width())
        parent_h = max(1, self.cv_screen_box.winfo_height())
        pip_center_x = self.cv_pip_box.winfo_x() + (self.cv_pip_box.winfo_width() / 2)
        pip_center_y = self.cv_pip_box.winfo_y() + (self.cv_pip_box.winfo_height() / 2)
        corners = [
            ("nw", 0.04, 0.06),
            ("ne", 0.96, 0.06),
            ("sw", 0.04, 0.94),
            ("se", 0.96, 0.94)
        ]
        best_anchor, best_rx, best_ry = "se", 0.96, 0.94
        min_dist = float("inf")
        for anchor, rx, ry in corners:
            tx = parent_w * rx
            ty = parent_h * ry
            d = math.hypot(pip_center_x - tx, pip_center_y - ty)
            if d < min_dist:
                min_dist = d
                best_anchor, best_rx, best_ry = anchor, rx, ry
        self.cv_pip_box.place(relx=best_rx, rely=best_ry, anchor=best_anchor)

    def _build_inspector_properties(self, tokens: ThemeTokens):
        # 1. Section: Camera Sensor
        self.lbl_insp_cam = ctk.CTkLabel(self.insp_scroll, text="Camera sensor", font=OmniTheme.font_caption(), text_color=tokens.text_muted)
        self.lbl_insp_cam.pack(anchor="w", pady=(2, 2))
        self.prop_cam_facing = StudioSegmentedControl(
            self.insp_scroll,
            values=["Back", "Front"]
        )
        self.prop_cam_facing.set("Back")
        self.prop_cam_facing.pack(fill="x", pady=(0, 6))

        # 2. Section: Frame Rate
        self.lbl_insp_fps = ctk.CTkLabel(self.insp_scroll, text="Capture frame rate", font=OmniTheme.font_caption(), text_color=tokens.text_muted)
        self.lbl_insp_fps.pack(anchor="w", pady=(0, 2))
        self.prop_fps = StudioSegmentedControl(
            self.insp_scroll,
            values=["30 fps", "60 fps"]
        )
        self.prop_fps.set("60 fps")
        self.prop_fps.pack(fill="x", pady=(0, 6))

        # 3. Section: Container Format
        self.lbl_insp_format = ctk.CTkLabel(self.insp_scroll, text="Video container", font=OmniTheme.font_caption(), text_color=tokens.text_muted)
        self.lbl_insp_format.pack(anchor="w", pady=(0, 2))
        self.prop_format = StudioSegmentedControl(
            self.insp_scroll,
            values=["MP4", "MKV (Crash-Safe)"]
        )
        self.prop_format.set("MP4")
        self.prop_format.pack(fill="x", pady=(0, 6))

        # 4. Section: Touch Mode
        self.lbl_insp_input = ctk.CTkLabel(self.insp_scroll, text="Touch input mode", font=OmniTheme.font_caption(), text_color=tokens.text_muted)
        self.lbl_insp_input.pack(anchor="w", pady=(0, 2))
        self.prop_input_mode = StudioSegmentedControl(
            self.insp_scroll,
            values=["Standard Touch", "Hardware (UHID)"]
        )
        self.prop_input_mode.set("Standard Touch")
        self.prop_input_mode.pack(fill="x", pady=(0, 8))

        # 5. Compound Switches with helper text
        self.prop_preview_var = ctk.BooleanVar(value=True)
        self.sw_preview = StudioSwitch(
            self.insp_scroll,
            text="Show preview window",
            helper_text="Live direct viewfinder playback on desktop",
            variable=self.prop_preview_var
        )
        self.sw_preview.pack(fill="x", pady=2)

        self.prop_screen_off_var = ctk.BooleanVar(value=True)
        self.sw_screen_off = StudioSwitch(
            self.insp_scroll,
            text="Turn mobile screen off",
            helper_text="Saves phone battery & prevents thermal throttling",
            variable=self.prop_screen_off_var
        )
        self.sw_screen_off.pack(fill="x", pady=2)

        self.prop_upload_var = ctk.BooleanVar(value=False)
        self.sw_upload = StudioSwitch(
            self.insp_scroll,
            text="Auto-upload to Drive",
            helper_text="Syncs finished recording to virtual cloud path",
            variable=self.prop_upload_var
        )
        self.sw_upload.pack(fill="x", pady=2)

        # 6. Wi-Fi Switch Action Button
        self.wifi_switch_btn = StudioButton(
            self.insp_scroll,
            text="Switch to Wi-Fi ADB",
            variant="secondary",
            icon=get_icon("wifi"),
            command=self._on_switch_to_wireless
        )
        self.wifi_switch_btn.pack(fill="x", pady=(14, 4))

    # -------------------------------------------------------------------------
    # 3. BOTTOM MODULAR PRODUCTION DOCK (The 4 Classic OBS Docks)
    # -------------------------------------------------------------------------

    def _build_bottom_production_dock(self):
        tokens = OmniTheme.get_tokens()

        self.dock_panel = ctk.CTkFrame(
            self,
            fg_color=tokens.bg_panel,
            border_width=1,
            border_color=tokens.border_subtle,
            corner_radius=0,
            height=185
        )
        self.dock_panel.pack(fill="x", side="bottom")

        self.dock_panel.rowconfigure(0, weight=1)
        self.dock_panel.columnconfigure(0, weight=1) # Scenes
        self.dock_panel.columnconfigure(1, weight=1) # Sources
        self.dock_panel.columnconfigure(2, weight=2) # Audio Mixer
        self.dock_panel.columnconfigure(3, weight=1) # Master Controls

        # -----------------------------
        # DOCK 1: SCENES
        # -----------------------------
        d1 = ctk.CTkFrame(self.dock_panel, fg_color="transparent")
        d1.grid(row=0, column=0, sticky="nsew", padx=6, pady=4)
        self.dock_col_scenes = d1

        self.dock_title_scenes = ctk.CTkLabel(d1, text="Scenes", font=OmniTheme.font_section(), text_color=tokens.text_primary)
        self.dock_title_scenes.pack(anchor="w", padx=8, pady=(0, 4))

        self.btn_scene_dual = SceneListItem(d1, scene_id="dual", number=1, title="Dual Stream (PC+Cam)", is_active=True, on_select=self._select_scene)
        self.btn_scene_dual.pack(fill="x", padx=8, pady=1)

        self.btn_scene_mirror = SceneListItem(d1, scene_id="mirror", number=2, title="Screen Mirror", is_active=False, on_select=self._select_scene)
        self.btn_scene_mirror.pack(fill="x", padx=8, pady=1)

        self.btn_scene_camera = SceneListItem(d1, scene_id="camera", number=3, title="Camera Feed", is_active=False, on_select=self._select_scene)
        self.btn_scene_camera.pack(fill="x", padx=8, pady=1)

        self.btn_scene_screen = SceneListItem(d1, scene_id="screen", number=4, title="Screen Record", is_active=False, on_select=self._select_scene)
        self.btn_scene_screen.pack(fill="x", padx=8, pady=1)

        # -----------------------------
        # DOCK 2: SOURCES
        # -----------------------------
        d2 = ctk.CTkFrame(self.dock_panel, fg_color="transparent")
        d2.grid(row=0, column=1, sticky="nsew", padx=6, pady=4)
        self.dock_col_sources = d2

        self.dock_title_sources = ctk.CTkLabel(d2, text="Sources", font=OmniTheme.font_section(), text_color=tokens.text_primary)
        self.dock_title_sources.pack(anchor="w", padx=8, pady=(0, 4))

        self.source_pc_check = SourceRow(d2, name="PC display (gdigrab)", initial_checked=True, initial_active=True)
        self.source_pc_check.pack(fill="x", padx=8, pady=2)

        self.source_cam_check = SourceRow(d2, name="Phone camera sensor", initial_checked=True, initial_active=True)
        self.source_cam_check.pack(fill="x", padx=8, pady=2)

        self.source_uhid_check = SourceRow(d2, name="UHID touch mouse", initial_checked=False, initial_active=False)
        self.source_uhid_check.pack(fill="x", padx=8, pady=2)

        # -----------------------------
        # DOCK 3: AUDIO MIXER
        # -----------------------------
        d3 = ctk.CTkFrame(self.dock_panel, fg_color="transparent")
        d3.grid(row=0, column=2, sticky="nsew", padx=8, pady=4)
        self.dock_col_mixer = d3

        self.dock_title_mixer = ctk.CTkLabel(d3, text="Audio mixer", font=OmniTheme.font_section(), text_color=tokens.text_primary)
        self.dock_title_mixer.pack(anchor="w", padx=4, pady=(0, 2))

        self.strip_mic = AudioChannelStrip(d3, channel_name="Phone microphone", initial_volume=0.85)
        self.strip_mic.pack(fill="x", padx=4, pady=(0, 2))

        self.strip_pc = AudioChannelStrip(d3, channel_name="Desktop playback", initial_volume=0.75)
        self.strip_pc.pack(fill="x", padx=4)

        # -----------------------------
        # DOCK 4: MASTER CONTROLS
        # -----------------------------
        d4 = ctk.CTkFrame(self.dock_panel, fg_color="transparent")
        d4.grid(row=0, column=3, sticky="nsew", padx=12, pady=4)
        self.dock_col_controls = d4

        self.dock_title_controls = ctk.CTkLabel(d4, text="Controls", font=OmniTheme.font_section(), text_color=tokens.text_primary)
        self.dock_title_controls.pack(anchor="w", pady=(0, 2))

        # Primary Action: 38px prominent primary button with red record dot icon
        self.master_record_btn = StudioButton(
            d4,
            text="Start Recording",
            variant="primary",
            size="normal",
            height=38,
            icon=get_icon("record"),
            command=self._on_master_record_click
        )
        self.master_record_btn.pack(fill="x", pady=(0, 2))

        self.master_mirror_btn = StudioButton(
            d4,
            text="Launch Mirror",
            variant="secondary",
            size="small",
            icon=get_icon("monitor"),
            command=self._on_launch_mirror
        )
        self.master_mirror_btn.pack(fill="x", pady=1)

        self.master_recordings_btn = StudioButton(
            d4,
            text="Media Library",
            variant="secondary",
            size="small",
            icon=get_icon("folder"),
            command=self._open_recordings_window
        )
        self.master_recordings_btn.pack(fill="x", pady=1)

        self.master_settings_btn = StudioButton(
            d4,
            text="Preferences",
            variant="secondary",
            size="small",
            icon=get_icon("settings"),
            command=self._open_settings_window
        )
        self.master_settings_btn.pack(fill="x", pady=(1, 0))

    def _update_scene_buttons(self, tokens: ThemeTokens):
        for btn, sid in [
            (self.btn_scene_dual, "dual"),
            (self.btn_scene_mirror, "mirror"),
            (self.btn_scene_camera, "camera"),
            (self.btn_scene_screen, "screen")
        ]:
            btn.set_active(sid == self.active_scene)

    def _select_scene(self, scene_id: str):
        self.active_scene = scene_id
        tokens = OmniTheme.get_tokens()
        self._update_scene_buttons(tokens)

        if scene_id == "dual":
            self.canvas_mode_lbl.configure(text="Preview: Dual Recording")
            self.cv_screen_title.configure(text="PC Screen + Mobile Camera")
            self.cv_screen_sub.configure(text="Parallel dual streams @ 60 FPS")
            self.cv_pip_box.place(relx=0.96, rely=0.94, anchor="se")
            self.source_pc_check.select()
            self.source_cam_check.select()
            self.master_record_btn.configure(text="Start Dual Record")
        elif scene_id == "mirror":
            self.canvas_mode_lbl.configure(text="Preview: Screen Mirror")
            self.cv_screen_title.configure(text="Android Display Mirror")
            self.cv_screen_sub.configure(text="Direct3D 11 Interactive Touch @ 60 FPS")
            self.cv_pip_box.place_forget()
            self.source_pc_check.deselect()
            self.source_cam_check.deselect()
            self.master_record_btn.configure(text="Launch Mirror")
        elif scene_id == "camera":
            self.canvas_mode_lbl.configure(text="Preview: Camera Feed")
            self.cv_screen_title.configure(text="Raw Camera2 Sensor Viewfinder")
            self.cv_screen_sub.configure(text="Screen off / No camera app opened")
            self.cv_pip_box.place_forget()
            self.source_pc_check.deselect()
            self.source_cam_check.select()
            self.master_record_btn.configure(text="Start Camera Record")
        elif scene_id == "screen":
            self.canvas_mode_lbl.configure(text="Preview: Screen Record")
            self.cv_screen_title.configure(text="Mobile Display Recorder")
            self.cv_screen_sub.configure(text="Direct-to-PC storage")
            self.cv_pip_box.place_forget()
            self.source_pc_check.deselect()
            self.source_cam_check.deselect()
            self.master_record_btn.configure(text="Start Screen Record")

    # -------------------------------------------------------------------------
    # 4. BROADCAST TELEMETRY STATUS BAR
    # -------------------------------------------------------------------------

    def _build_status_footer(self):
        tokens = OmniTheme.get_tokens()

        self.footer = ctk.CTkFrame(self, fg_color=tokens.bg_header, height=28, corner_radius=0)
        self.footer.pack(fill="x", side="bottom")

        self.foot_status_chip = StatusChip(self.footer, text="Studio Ready", state="ready")
        self.foot_status_chip.pack(side="left", padx=12, pady=2)

        self.foot_rec_time = ctk.CTkLabel(
            self.footer,
            text="Rec: 00:00:00",
            font=OmniTheme.font_mono(11),
            text_color=tokens.text_muted
        )
        self.foot_rec_time.pack(side="left", padx=10)

        self.foot_fps_lbl = ctk.CTkLabel(
            self.footer,
            text="60.0 fps",
            font=OmniTheme.font_mono(11),
            text_color=tokens.text_dim
        )
        self.foot_fps_lbl.pack(side="left", padx=10)

        self.foot_bitrate_lbl = ctk.CTkLabel(
            self.footer,
            text="8.0 Mbps",
            font=OmniTheme.font_mono(11),
            text_color=tokens.text_dim
        )
        self.foot_bitrate_lbl.pack(side="left", padx=10)

        self.foot_disk_lbl = ctk.CTkLabel(
            self.footer,
            text=self._query_disk_space_str(),
            font=OmniTheme.font_mono(11),
            text_color=tokens.text_dim
        )
        self.foot_disk_lbl.pack(side="left", padx=10)

        # Video Encoder chip (AMF / NVENC / QSV / libx264)
        self.foot_encoder_lbl = ctk.CTkLabel(
            self.footer,
            text="ENC: Hardware",
            font=OmniTheme.font_mono(11),
            text_color=tokens.text_dim
        )
        self.foot_encoder_lbl.pack(side="left", padx=10)

        # Connected Device Chip
        self.foot_device_chip = StatusChip(
            self.footer,
            text="No Device",
            state="disconnected"
        )
        self.foot_device_chip.pack(side="left", padx=6, pady=2)

        # Right side hint groups (priority-based truncation drops whole groups cleanly)
        self.hint_rec = ctk.CTkLabel(
            self.footer,
            text="Ctrl+Alt+D: Record",
            font=OmniTheme.font_caption(),
            text_color=tokens.text_dim
        )
        self.hint_rec.pack(side="right", padx=(4, 16))

        self.hint_palette = ctk.CTkLabel(
            self.footer,
            text="Ctrl+P: Palette  ·",
            font=OmniTheme.font_caption(),
            text_color=tokens.text_dim
        )
        self.hint_palette.pack(side="right", padx=(4, 0))

        # Priority-based truncation: hide hints first when width is tight, never cut mid-word
        self.footer.bind("<Configure>", self._on_footer_configure, add="+")

    def _compute_footer_reqwidth(self, widgets: list) -> int:
        """Calculate the total physical pixel width requested by a set of footer widgets."""
        total = 32 # Left (16px) and right (16px) outer edge margins
        for w in widgets:
            if hasattr(w, "winfo_reqwidth"):
                total += w.winfo_reqwidth() + 14 # Include inter-item horizontal padding
        return total

    def _on_footer_configure(self, event):
        """
        Dynamic Measured-Width Footer Truncation Engine.
        Directly compares the live measured pixel widths (winfo_reqwidth) of all footer groups
        against the currently available pixel width, eliminating fragile hardcoded thresholds.
        Guarantees zero clipping and clean whole-group dropping across 100%, 125%, 150%, and 200% DPI.
        """
        avail_w = event.width
        if avail_w <= 1:
            return

        # Baseline essential studio telemetry (never dropped)
        essentials = [self.foot_status_chip, self.foot_rec_time, self.foot_device_chip]

        # Prioritized optional groups: lowest priority is dropped first when available width is tight
        # Priority order to drop:
        # 1. hint_rec (Ctrl+Alt+D)
        # 2. hint_palette (Ctrl+P)
        # 3. foot_bitrate_lbl (Bitrate readout)
        # 4. foot_fps_lbl (FPS readout)
        # 5. foot_encoder_lbl (Encoder chip)
        # 6. foot_disk_lbl (Disk free space)
        optional_candidates = [
            self.hint_rec,
            self.hint_palette,
            self.foot_bitrate_lbl,
            self.foot_fps_lbl,
            self.foot_encoder_lbl,
            self.foot_disk_lbl
        ]

        current_active = essentials + optional_candidates
        dropped = set()

        for candidate in optional_candidates:
            active_subset = [w for w in current_active if w not in dropped]
            if self._compute_footer_reqwidth(active_subset) > avail_w:
                dropped.add(candidate)
            else:
                break

        # Apply geometry manager states based on dynamic measurements
        # Left-docked telemetry items:
        for w in [self.foot_disk_lbl, self.foot_encoder_lbl, self.foot_fps_lbl, self.foot_bitrate_lbl]:
            if w in dropped:
                if w.winfo_manager() == "pack":
                    w.pack_forget()
            else:
                if not w.winfo_manager():
                    w.pack(side="left", padx=10)

        # Right-docked keyboard accelerator hints:
        if self.hint_palette in dropped:
            if self.hint_palette.winfo_manager() == "pack":
                self.hint_palette.pack_forget()
        else:
            if not self.hint_palette.winfo_manager():
                self.hint_palette.pack(side="right", padx=(4, 0))

        if self.hint_rec in dropped:
            if self.hint_rec.winfo_manager() == "pack":
                self.hint_rec.pack_forget()
            if hasattr(self, "hint_palette"):
                self.hint_palette.configure(text="Ctrl+P: Palette")
        else:
            if not self.hint_rec.winfo_manager():
                self.hint_rec.pack(side="right", padx=(4, 16))
            if hasattr(self, "hint_palette"):
                self.hint_palette.configure(text="Ctrl+P: Palette  ·")

    def _refresh_encoder_chip(self):
        try:
            enc = self.controller.get_active_encoder_short()
            self.foot_encoder_lbl.configure(text=f"ENC: {enc}")
        except Exception:
            pass

    def _query_disk_space_str(self) -> str:
        try:
            rec_dir = self.controller.recordings_dir
            usage = shutil.disk_usage(rec_dir)
            free_gb = usage.free / (1024 ** 3)
            return f"Disk: {free_gb:.1f} GB free"
        except Exception:
            return "Disk: OK"

    # -------------------------------------------------------------------------
    # 5. RUNTIME THEME SWITCHING ENGINE
    # -------------------------------------------------------------------------

    def set_active_theme(self, theme_name: str):
        """Set active theme and re-theme all widgets throughout the application."""
        OmniTheme.set_theme(theme_name)
        self.app_config["theme"] = theme_name
        self.settings["theme"] = theme_name
        tokens = OmniTheme.get_tokens()
        self.apply_theme(tokens)

    def apply_theme(self, tokens: ThemeTokens):
        """Central re-theming method that updates every widget from theme tokens."""
        # Update root & panels
        self.configure(fg_color=tokens.bg_root)
        self.middle_container.configure(fg_color="transparent")
        self.canvas_panel.configure(fg_color=tokens.bg_panel, border_color=tokens.border_subtle)
        self.canvas_viewport.configure(fg_color=tokens.bg_stage, border_color=tokens.border_stage)
        self.canvas_mode_lbl.configure(text_color=tokens.text_primary)
        self.canvas_stats_lbl.configure(text_color=tokens.text_dim)
        self.aspect_seg.apply_tokens(tokens)

        # Inspector Panel & Controls
        self.inspector_panel.configure(fg_color=tokens.bg_panel, border_color=tokens.border_subtle)
        self.insp_header.configure(fg_color=tokens.bg_header)
        self.insp_title_lbl.configure(text_color=tokens.text_primary)
        self.lbl_insp_cam.configure(text_color=tokens.text_muted)
        self.lbl_insp_fps.configure(text_color=tokens.text_muted)
        self.lbl_insp_format.configure(text_color=tokens.text_muted)
        self.lbl_insp_input.configure(text_color=tokens.text_muted)

        for seg in [self.prop_cam_facing, self.prop_fps, self.prop_format, self.prop_input_mode]:
            seg.apply_tokens(tokens)

        self.sw_preview.apply_tokens(tokens)
        self.sw_screen_off.apply_tokens(tokens)
        self.sw_upload.apply_tokens(tokens)
        self.wifi_switch_btn.apply_tokens(tokens)

        # Canvas Visualizer Box (Stage dark styling)
        self.cv_screen_box.configure(fg_color="#141619", border_color=tokens.stage_border_card)
        self.cv_guide_box.configure(border_color=tokens.border_subtle)
        self.cv_crosshair.configure(text_color=tokens.stage_text_dim)
        self.cv_screen_title.configure(text_color=tokens.stage_text_primary)
        self.cv_screen_sub.configure(text_color=tokens.stage_text_muted)
        self.cv_pip_box.configure(fg_color=tokens.stage_bg_card, border_color=tokens.accent_primary)
        self.cv_pip_lbl.configure(text_color=tokens.stage_text_primary)
        self.cv_recording_hud.configure(fg_color=tokens.stage_bg_card, border_color=tokens.status_recording)
        self.cv_tally_dot.configure(text_color=tokens.status_recording)
        self.cv_tally_timer.configure(text_color=tokens.stage_text_primary)
        self.cv_tally_stats.configure(text_color=tokens.stage_text_muted)

        # Bottom Production Dock
        self.dock_panel.configure(fg_color=tokens.bg_panel, border_color=tokens.border_subtle)
        self.dock_title_scenes.configure(text_color=tokens.text_primary)
        self.dock_title_sources.configure(text_color=tokens.text_primary)
        self.dock_title_mixer.configure(text_color=tokens.text_primary)
        self.dock_title_controls.configure(text_color=tokens.text_primary)

        # Scene List Items
        for scene_item in [self.btn_scene_dual, self.btn_scene_mirror, self.btn_scene_camera, self.btn_scene_screen]:
            scene_item.apply_tokens(tokens)
        self._update_scene_buttons(tokens)

        # Sources Rows
        for src in [self.source_pc_check, self.source_cam_check, self.source_uhid_check]:
            src.apply_tokens(tokens)

        # Master Controls
        is_rec = self.controller.is_dual_recording()
        self.master_record_btn.configure(
            fg_color=tokens.status_recording if is_rec else tokens.accent_primary,
            hover_color=tokens.status_recording_hover if is_rec else tokens.accent_hover,
            text_color="#FFFFFF"
        )
        self.master_mirror_btn.apply_tokens(tokens)
        self.master_recordings_btn.apply_tokens(tokens)
        self.master_settings_btn.apply_tokens(tokens)

        # Subcomponents
        self.top_bar.apply_tokens(tokens)
        if hasattr(self, "state_banner") and self.state_banner:
            self.state_banner.apply_tokens(tokens)
        self.cv_empty_state.apply_tokens(tokens)
        self.strip_mic.apply_tokens(tokens)
        self.strip_pc.apply_tokens(tokens)
        self.foot_status_chip.apply_tokens(tokens)
        self.foot_device_chip.apply_tokens(tokens)

        # Footer
        self.footer.configure(fg_color=tokens.bg_header)
        self.foot_rec_time.configure(text_color=tokens.text_muted)
        self.foot_fps_lbl.configure(text_color=tokens.text_dim)
        self.foot_bitrate_lbl.configure(text_color=tokens.text_dim)
        self.foot_disk_lbl.configure(text_color=tokens.text_dim)
        self.foot_encoder_lbl.configure(text_color=tokens.text_dim)
        if hasattr(self, "hint_rec"):
            self.hint_rec.configure(text_color=tokens.text_dim)
        if hasattr(self, "hint_palette"):
            self.hint_palette.configure(text_color=tokens.text_dim)
        if hasattr(self, "hotkey_legend"):
            self.hotkey_legend.configure(text_color=tokens.text_dim)

        # Re-apply DWM window frame
        self._apply_dwm()

    def _toggle_theme(self):
        """Switch between Light Minimal and Dark Liquid Glass instantly."""
        new_theme = "light" if OmniTheme.get_tokens().is_dark else "dark"
        self.set_active_theme(new_theme)

    # -------------------------------------------------------------------------
    # 6. AUDIO & RECORDING PULSE ANIMATIONS
    # -------------------------------------------------------------------------

    def _start_audio_level_animation(self):
        self._meter_timer_active = True

        def _loop():
            if not self._meter_timer_active:
                return
            is_active = self.controller.is_dual_recording()
            try:
                self.strip_mic.simulate_audio_activity(active=is_active)
                self.strip_pc.simulate_audio_activity(active=is_active)
            except Exception:
                pass

            # Subtle Recording Pulse Animation
            if is_active and self._recording_pulse_active:
                self._pulse_phase = (self._pulse_phase + 1) % 16
                tokens = OmniTheme.get_tokens()
                pulse_color = tokens.status_recording_hover if self._pulse_phase < 8 else tokens.status_recording
                try:
                    self.master_record_btn.configure(fg_color=pulse_color)
                except Exception:
                    pass

            delay = 80 if is_active else 250
            self.after(delay, _loop)

        self.after(500, _loop)

    # -------------------------------------------------------------------------
    # 7. COMMAND PALETTE & DIALOGS
    # -------------------------------------------------------------------------

    def _open_command_palette(self):
        commands = [
            {"title": "Start Dual Recording (PC + Phone)", "category": "Capture", "shortcut": "Ctrl+Alt+D", "action": self._on_start_dual_recording, "keywords": "rec video"},
            {"title": "Stop Active Recording", "category": "Capture", "shortcut": "Esc", "action": self._on_stop_dual_recording, "keywords": "end finish"},
            {"title": "Launch Screen Mirror", "category": "Capture", "shortcut": "Ctrl+Alt+M", "action": self._on_launch_mirror, "keywords": "phone display view"},
            {"title": "Start Camera Viewfinder", "category": "Capture", "shortcut": "Ctrl+Alt+C", "action": self._on_start_camera_recording, "keywords": "webcam sensor"},
            {"title": "Start Screen Recording", "category": "Capture", "shortcut": "", "action": self._on_start_screen_recording, "keywords": "mobile display"},
            {"title": "Open Media Library & Recordings", "category": "Media", "shortcut": "Ctrl+Alt+R", "action": self._open_recordings_window, "keywords": "gallery files list"},
            {"title": "Open Recordings Folder in Explorer", "category": "Files", "shortcut": "", "action": self.controller.open_recordings_folder, "keywords": "directory disk path"},
            {"title": "Release Camera Hardware Lock", "category": "Hardware", "shortcut": "Ctrl+Shift+L", "action": self._on_release_lock, "keywords": "unlock busy sensor fix"},
            {"title": "Switch to Wireless ADB (Wi-Fi)", "category": "Hardware", "shortcut": "", "action": self._on_switch_to_wireless, "keywords": "tcp ip wireless"},
            {"title": "Refresh Connected Devices", "category": "Hardware", "shortcut": "F5", "action": self._on_manual_refresh, "keywords": "reload adb phone"},
            {"title": "Toggle Theme (Light / Dark)", "category": "View", "shortcut": "", "action": self._toggle_theme, "keywords": "appearance dark light mode"},
            {"title": "System & Hardware Diagnostics", "category": "Tools", "shortcut": "", "action": self._open_diagnostics_window, "keywords": "info check debug ffmpeg"},
            {"title": "Getting Started Setup Checklist", "category": "Help", "shortcut": "", "action": self._open_onboarding_dialog, "keywords": "onboarding wizard setup guide steps"},
            {"title": "Developer: Simulated Device Mode", "category": "Developer", "shortcut": "", "action": self._open_simulated_device_dialog, "keywords": "mock simulate test states device error"},
            {"title": "Developer: Design System Component Gallery", "category": "Developer", "shortcut": "", "action": self._open_component_gallery, "keywords": "components gallery design tokens ui"},
            {"title": "Studio Preferences & Settings", "category": "Settings", "shortcut": "Ctrl+,", "action": self._open_settings_window, "keywords": "config options format"},
            {"title": "Scene: Dual Stream", "category": "Scenes", "shortcut": "1", "action": lambda: self._select_scene("dual"), "keywords": "preset layout"},
            {"title": "Scene: Screen Mirror", "category": "Scenes", "shortcut": "2", "action": lambda: self._select_scene("mirror"), "keywords": "preset layout"},
            {"title": "Scene: Camera Viewfinder", "category": "Scenes", "shortcut": "3", "action": lambda: self._select_scene("camera"), "keywords": "preset layout"},
            {"title": "Scene: Screen Record", "category": "Scenes", "shortcut": "4", "action": lambda: self._select_scene("screen"), "keywords": "preset layout"},
            {"title": "Minimize to System Tray", "category": "Window", "shortcut": "Ctrl+W", "action": self._on_minimize_to_tray, "keywords": "hide background"},
            {"title": "Exit OmniCapture Studio", "category": "Window", "shortcut": "Ctrl+Q", "action": self._on_app_exit, "keywords": "quit close"},
        ]
        self.palette = CommandPalette(self, commands)
        return self.palette

    def _open_recordings_window(self):
        from gui.dialogs.recordings import RecordingsGalleryDialog
        RecordingsGalleryDialog(self, self.controller, on_toast=self.toasts.show)

    def _open_settings_window(self):
        from gui.dialogs.settings import StudioSettingsDialog
        StudioSettingsDialog(
            self,
            self.app_config,
            self.controller,
            self.minimize_to_tray_var,
            self.enable_hotkeys_var,
            on_toast=self.toasts.show
        )

    def _open_diagnostics_window(self):
        from gui.dialogs.diagnostics import DiagnosticsDialog
        DiagnosticsDialog(self, self.controller, on_toast=self.toasts.show)

    def _open_simulated_device_dialog(self):
        from gui.dialogs.simulated_device import SimulatedDeviceControlDialog
        if not hasattr(self, "_sim_engine") or not self._sim_engine:
            from core.simulated_device import SimulatedADBManager
            self._sim_engine = SimulatedADBManager()
            self.controller.set_simulated_device_manager(self._sim_engine)
            self.top_bar.set_simulated_mode(True)
        SimulatedDeviceControlDialog(self, self._sim_engine, on_state_change=self._on_simulated_state_change)

    def _on_simulated_state_change(self, state_id: str):
        if hasattr(self, "state_banner") and self.state_banner and state_id in self.state_banner.STATE_PRESETS:
            self.state_banner.set_state(state_id)
        if state_id == "unplugged_mid_recording":
            self.notifications.notify("Device Disconnected", "USB connection was lost mid-recording", level="warning")
        elif state_id == "battery_low":
            self.top_bar.set_device_status("● POCO X6 Pro (USB Direct) · 12% ⚡")
            self.foot_device_chip.set_status("POCO X6 Pro (12%)", state="warning")
            self.toasts.show("Low Battery", "Connected phone battery is at 12%", level="warning")
        elif state_id == "slow_response":
            self.top_bar.set_device_status("● POCO X6 Pro (High Latency +1.5s)")
            self.toasts.show("ADB Latency", "Device response latency +1.5s", level="warning")
        elif state_id == "failure":
            self.state_banner.set_state("device_unplugged", custom_desc="USB Bus hardware failure detected. Reconnect USB cable.")
        elif state_id == "engine_crashed":
            self.notifications.notify("Engine Crash", "Video capture worker crashed with code 0xC0000005", level="error")
        self.controller.refresh_device_now()

    def _open_onboarding_dialog(self):
        from gui.dialogs.onboarding import OnboardingChecklistDialog
        def _on_done():
            self.settings["first_run_completed"] = True
            SettingsManager.save(self.settings)
        OnboardingChecklistDialog(self, self.controller, on_theme_toggle=self._toggle_theme, on_complete=_on_done)

    def _check_first_run_onboarding(self):
        if not self.settings.get("first_run_completed", False):
            self._open_onboarding_dialog()

    def _on_banner_action(self, state_name: str):
        if state_name in ("no_device", "permission_denied"):
            self._open_onboarding_dialog()
        elif state_name in ("scanning", "connecting", "unauthorized", "device_unplugged"):
            self._on_manual_refresh()
        elif state_name == "camera_locked":
            self._on_release_lock()
        elif state_name in ("connected_usb", "connected_wifi"):
            self._on_launch_mirror()
        elif state_name == "recording":
            self._on_stop_dual_recording()
        elif state_name == "disk_nearly_full":
            self._open_settings_window()
        elif state_name == "disk_full":
            self._open_recordings_window()
        elif state_name in ("ffmpeg_missing", "scrcpy_missing", "adb_missing"):
            self._open_diagnostics_window()
        elif state_name == "upload_failed":
            self.toasts.show("Cloud Upload", "Retrying Google Drive upload...", level="info")
        elif state_name == "upload_done":
            self.controller.open_recordings_folder()
        elif state_name == "engine_crashed":
            self._on_manual_refresh()
            self.toasts.show("Engine Reset", "Capture worker subprocess restarted", level="success")
        else:
            self.toasts.show("Studio Action", f"Action triggered for state: {state_name}", level="info")

    def _open_hotkeys_guide(self):
        w = ctk.CTkToplevel(self)
        w.title("Keyboard Shortcuts & Hotkeys")
        w.geometry("500x480")
        w.resizable(False, False)
        tokens = OmniTheme.get_tokens()
        w.configure(fg_color=tokens.bg_root)

        box = ctk.CTkFrame(w, fg_color=tokens.bg_panel, corner_radius=OmniTheme.RADIUS_CARD)
        box.pack(fill="both", expand=True, padx=16, pady=16)

        ctk.CTkLabel(box, text="Keyboard Shortcuts & System Hotkeys", font=OmniTheme.font_section(), text_color=tokens.text_primary).pack(anchor="w", padx=14, pady=(12, 6))

        scroll = ctk.CTkScrollableFrame(box, fg_color="transparent")
        scroll.pack(fill="both", expand=True, padx=4, pady=4)

        shortcuts = [
            ("Ctrl + P / Ctrl + K", "Open Studio Command Palette"),
            ("F1", "Getting Started Setup Checklist"),
            ("Ctrl + /", "Open Keyboard Shortcuts Guide"),
            ("Ctrl + Alt + D", "Start / Stop Dual Recording (Global Hotkey)"),
            ("Ctrl + Alt + M", "Launch Display Mirror (Global Hotkey)"),
            ("Ctrl + Alt + C", "Launch Camera Viewfinder (Global Hotkey)"),
            ("Ctrl + Alt + R", "Open Recordings Folder (Global Hotkey)"),
            ("Ctrl + Shift + L", "Release Camera Sensor Hardware Lock"),
            ("F5", "Refresh Connected Android Devices"),
            ("1 / 2 / 3 / 4", "Switch Active Studio Scene"),
            ("Ctrl + ,", "Open Studio Preferences Dialog"),
            ("Esc", "Stop Active Capture / Close Popups"),
            ("Alt + F / C / T / V / S / H", "Windows Standard Menu Mnemonics"),
            ("Ctrl + W", "Minimize Application to System Tray"),
            ("Ctrl + Q", "Exit Application Cleanly"),
        ]

        for key, desc in shortcuts:
            r = ctk.CTkFrame(scroll, fg_color="transparent")
            r.pack(fill="x", padx=10, pady=2)
            ctk.CTkLabel(r, text=key, font=OmniTheme.font_mono(10, weight="bold"), text_color=tokens.accent_primary, width=170, anchor="w").pack(side="left")
            ctk.CTkLabel(r, text=desc, font=OmniTheme.font_body(), text_color=tokens.text_secondary).pack(side="left")

    def _open_about_dialog(self):
        messagebox.showinfo(
            "About OmniCapture Studio",
            "OmniCapture Studio v1.4.0-dev\n\n"
            "Hardware-Accelerated Dual PC Screen & Mobile Camera Studio.\n"
            "Engineered with Windows 11 Fluent Design, DWM Mica/Acrylic support, "
            "and synchronized multi-stream recording.\n\n"
            "Open source under the Apache 2.0 License.",
            parent=self
        )

    def _reset_window_size(self):
        self.geometry("1180x800")
        self.toasts.show("Window Layout", "Reset to default 1180x800 resolution", level="info")

    def _open_component_gallery(self):
        from gui.dialogs.component_gallery import ComponentGalleryWindow
        ComponentGalleryWindow(self)

    def _bind_keyboard_shortcuts(self):
        # Command Palette
        self.bind("<Control-p>", lambda e: self._open_command_palette())
        self.bind("<Control-P>", lambda e: self._open_command_palette())
        self.bind("<Control-Shift-P>", lambda e: self._open_command_palette())
        self.bind("<Control-Shift-p>", lambda e: self._open_command_palette())
        self.bind("<Control-k>", lambda e: self._open_command_palette())
        self.bind("<Control-K>", lambda e: self._open_command_palette())

        # General Studio Actions
        self.bind("<F1>", lambda e: self._open_onboarding_dialog())
        self.bind("<F5>", lambda e: self._on_manual_refresh())
        self.bind("<Control-comma>", lambda e: self._open_settings_window())
        self.bind("<Control-q>", lambda e: self._on_app_exit())
        self.bind("<Control-w>", lambda e: self._on_minimize_to_tray())
        self.bind("<Control-slash>", lambda e: self._open_hotkeys_guide())
        self.bind("<Control-question>", lambda e: self._open_hotkeys_guide())
        self.bind("<Control-Shift-L>", lambda e: self._on_release_lock())
        self.bind("<Control-Shift-l>", lambda e: self._on_release_lock())
        self.bind("<Escape>", lambda e: self._on_escape_pressed())

        # Alt-Key Menu Mnemonics (Windows 11 Standard)
        for key, menu_name in [
            ("f", "File"), ("c", "Capture"), ("t", "Tools"),
            ("v", "View"), ("s", "Settings"), ("h", "Help")
        ]:
            self.bind(f"<Alt-{key}>", lambda e, m=menu_name: self.top_bar.open_menu_by_name(m))
            self.bind(f"<Alt-{key.upper()}>", lambda e, m=menu_name: self.top_bar.open_menu_by_name(m))

        self.bind("1", lambda e: self._select_scene("dual") if not self._is_entry_focused() else None)
        self.bind("2", lambda e: self._select_scene("mirror") if not self._is_entry_focused() else None)
        self.bind("3", lambda e: self._select_scene("camera") if not self._is_entry_focused() else None)
        self.bind("4", lambda e: self._select_scene("screen") if not self._is_entry_focused() else None)

    def _on_escape_pressed(self):
        """Handle Escape key: close active palette/dropdown, or stop recording if active."""
        if hasattr(self, "palette") and self.palette:
            self.palette.close()
            return
        if hasattr(self, "top_bar") and self.top_bar and self.top_bar.active_dropdown:
            try:
                self.top_bar.active_dropdown.close()
            except Exception:
                pass
            self.top_bar.active_dropdown = None
            return
        if self.controller.is_dual_recording():
            self._on_stop_dual_recording()

    def _is_entry_focused(self) -> bool:
        try:
            return isinstance(self.focus_get(), (tk.Entry, ctk.CTkEntry))
        except Exception:
            return False

    # -------------------------------------------------------------------------
    # 8. MASTER ACTION DISPATCHER & RECORDING EXECUTION
    # -------------------------------------------------------------------------

    def _on_master_record_click(self):
        if self.controller.is_dual_recording():
            self._on_stop_dual_recording()
            return

        if self.active_scene == "dual":
            self._on_start_dual_recording()
        elif self.active_scene == "mirror":
            self._on_launch_mirror()
        elif self.active_scene == "camera":
            self._on_start_camera_recording()
        elif self.active_scene == "screen":
            self._on_start_screen_recording()

    def _on_start_dual_recording(self):
        facing = "back" if "Back" in self.prop_cam_facing.get() else "front"
        fps_val = 60 if "60" in self.prop_fps.get() else 30
        fmt = "mkv" if "MKV" in self.prop_format.get() else "mp4"
        preview = self.prop_preview_var.get()
        upload = self.prop_upload_var.get()

        ok, msg = self.controller.start_dual_recording(
            facing=facing,
            pc_fps=fps_val,
            camera_fps=fps_val,
            record_format=fmt,
            preview=preview,
            auto_upload=upload,
            on_tick=self._on_dual_tick,
            on_complete=self._on_dual_complete
        )

        tokens = OmniTheme.get_tokens()
        if ok:
            self._recording_pulse_active = True
            self.master_record_btn.configure(
                text="Stop Recording",
                fg_color=tokens.status_recording,
                hover_color=tokens.status_recording_hover
            )
            self.cv_recording_hud.place(relx=0.5, rely=0.08, anchor="n")
            self.foot_status_chip.set_status("RECORDING", state="recording")
            if hasattr(self, "state_banner") and self.state_banner:
                self.state_banner.set_state("recording")
            self.taskbar.set_progress_state(TaskbarManager.TBPF_NOPROGRESS)
            self.taskbar.set_recording_overlay(True)
            self.tray.set_recording_state(True, "00:00:00")
            self.notifications.notify("Recording Started", "Parallel dual streams recording to disk", level="success")
        else:
            self.foot_status_chip.set_status(f"ERROR: {msg[:25]}", state="warning")
            self.notifications.notify("Recording Failed", msg, level="error")

    def _on_dual_tick(self, elapsed: float, pc_sz: int, cam_sz: int):
        m, s = divmod(int(elapsed), 60)
        h, m = divmod(m, 60)
        time_str = f"{h:02d}:{m:02d}:{s:02d}"

        def _fmt(b: int) -> str:
            for u in ["B", "KB", "MB", "GB"]:
                if b < 1024.0:
                    return f"{b:.1f} {u}"
                b /= 1024.0
            return f"{b:.1f} TB"

        stats_str = f"PC: {_fmt(pc_sz)}  ·  Cam: {_fmt(cam_sz)}"
        self.after(0, lambda: self._update_tally(time_str, stats_str))

    def _update_tally(self, time_str: str, stats_str: str):
        self.cv_tally_timer.configure(text=time_str)
        self.cv_tally_stats.configure(text=stats_str)
        self.foot_rec_time.configure(text=f"REC: {time_str}")
        self.tray.set_recording_state(True, time_str)

    def _on_stop_dual_recording(self):
        self._recording_pulse_active = False
        self.controller.stop_dual_recording()

    def _on_dual_complete(self, result: Dict[str, Any]):
        def _ui():
            self._recording_pulse_active = False
            tokens = OmniTheme.get_tokens()
            self.master_record_btn.configure(
                text="Start Dual Record",
                fg_color=tokens.accent_primary,
                hover_color=tokens.accent_hover
            )
            self.cv_recording_hud.place_forget()
            status = result.get("status", "COMPLETE")
            dur = result.get("duration_formatted", "00:00")
            self.foot_status_chip.set_status("STUDIO READY", state="ready")
            self.foot_rec_time.configure(text="REC: 00:00:00")
            self.foot_disk_lbl.configure(text=self._query_disk_space_str())
            if hasattr(self, "state_banner") and self.state_banner:
                self.state_banner.set_state("connected_usb" if self._connected_device_id else "no_device")
            self.taskbar.set_recording_overlay(False)
            self.taskbar.set_progress_state(TaskbarManager.TBPF_NOPROGRESS)
            self.tray.set_recording_state(False)
            self.notifications.notify_recording_saved(result.get("output_path", dur), dur)

        self.after(0, _ui)

    # -------------------------------------------------------------------------
    # 9. SINGLE STREAM HANDLERS
    # -------------------------------------------------------------------------

    def _on_launch_mirror(self):
        uhid = "Hardware" in self.prop_input_mode.get()
        screen_off = self.prop_screen_off_var.get()
        ok, msg = self.controller.launch_display_mirror(
            uhid=uhid,
            screen_off=screen_off,
            stay_awake=True,
            on_exit=lambda code: None
        )
        if not ok:
            self.toasts.show("Mirror Failed", msg, level="warning")

    def _on_start_screen_recording(self):
        fmt = "mkv" if "MKV" in self.prop_format.get() else "mp4"
        upload = self.prop_upload_var.get()
        ok, msg = self.controller.record_screen(
            record_format=fmt,
            auto_upload=upload,
            on_complete=lambda path, dur, sz: self._on_single_complete(path, "Screen")
        )
        if not ok:
            self.toasts.show("Screen Record", msg, level="warning")

    def _on_start_camera_recording(self):
        facing = "back" if "Back" in self.prop_cam_facing.get() else "front"
        fmt = "mkv" if "MKV" in self.prop_format.get() else "mp4"
        preview = self.prop_preview_var.get()
        upload = self.prop_upload_var.get()
        ok, msg = self.controller.record_camera(
            facing=facing,
            record_format=fmt,
            preview=preview,
            audio_mic=True,
            auto_upload=upload,
            on_complete=lambda path, dur, sz: self._on_single_complete(path, "Camera")
        )
        if not ok:
            self.toasts.show("Camera Record", msg, level="warning")

    def _on_single_complete(self, path: Optional[Path], mode_name: str):
        if path:
            self.toasts.show(f"{mode_name} Saved", path.name, level="success")
            self.tray.notify("OmniCapture Studio", f"{mode_name} saved: {path.name}")
            self.foot_disk_lbl.configure(text=self._query_disk_space_str())

    def _on_switch_to_wireless(self):
        def _worker():
            ok, msg = self.controller.switch_to_wireless_adb()
            self.after(0, lambda: self.toasts.show("Wireless ADB", msg, level="success" if ok else "warning"))
        threading.Thread(target=_worker, daemon=True).start()

    # -------------------------------------------------------------------------
    # 10. TELEMETRY & DEVICE STATE UPDATES
    # -------------------------------------------------------------------------

    def _initial_refresh(self):
        self.controller.refresh_device_now()

    def _on_device_state_changed(self, state: Dict[str, Any]):
        self.after(0, lambda: self._update_device_ui(state))

    def _update_device_ui(self, state: Dict[str, Any]):
        status = state.get("status")
        model = state.get("model", "No Device")
        conn_str = "Wi-Fi" if state.get("is_wireless") else "USB Direct"

        if status == "CONNECTED":
            dev_id = state.get("device_id")
            if self._connected_device_id != dev_id:
                self._connected_device_id = dev_id
                self.notifications.notify_device_event(True, f"{model} ({conn_str})")

            batt = state.get("battery", {})
            lvl = batt.get("level", "")
            batt_str = f" · {lvl} ⚡" if lvl and lvl != "N/A" else ""
            device_text = f"● {model} ({conn_str}){batt_str}"
            self.top_bar.set_device_status(device_text)
            self.foot_device_chip.set_status(f"{model} ({conn_str})", state="connected")

            # Switch Canvas from Empty State to Active Viewport Representation
            self.cv_empty_state.place_forget()
            self.cv_content.place(relx=0.5, rely=0.5, anchor="center")
            if hasattr(self, "state_banner") and self.state_banner:
                if not self.controller.is_dual_recording():
                    self.state_banner.set_state("connected_wifi" if state.get("is_wireless") else "connected_usb")
        else:
            if self._connected_device_id is not None:
                self._connected_device_id = None
                self.notifications.notify_device_event(False)
            self.foot_device_chip.set_status("No Device", state="disconnected")

            if status == "UNAUTHORIZED":
                self.top_bar.set_device_status("Unauthorized: unlock phone and tap 'Always allow'")
                if hasattr(self, "state_banner") and self.state_banner:
                    self.state_banner.set_state("unauthorized")
            elif status == "OFFLINE":
                self.top_bar.set_device_status("Device offline: reconnect USB cable")
                if hasattr(self, "state_banner") and self.state_banner:
                    self.state_banner.set_state("no_device", custom_desc="Device offline: reconnect USB cable.")
            else:
                self.top_bar.set_device_status("Connect a phone via USB to start")
                if hasattr(self, "state_banner") and self.state_banner:
                    if not self.controller.is_dual_recording():
                        self.state_banner.set_state("no_device")

            self.cv_content.place_forget()
            self.cv_empty_state.place(relx=0.5, rely=0.5, anchor="center", relwidth=0.85, relheight=0.7)

    def _on_manual_refresh(self):
        self.controller.refresh_device_now()
        self.toasts.show("Device Scan", "ADB devices refreshed", level="info")

    def _on_release_lock(self):
        ok, msg = self.controller.release_camera_lock()
        self.toasts.show("Camera Lock", msg, level="success" if ok else "warning")

    # -------------------------------------------------------------------------
    # 11. HOTKEYS, TRAY & LIFECYCLE
    # -------------------------------------------------------------------------

    def _setup_hotkeys(self):
        self.hotkeys.register(1, 0x0002 | 0x0001, ord("D"), self._on_hotkey_dual_record)
        self.hotkeys.register(2, 0x0002 | 0x0001, ord("M"), self._on_hotkey_mirror)
        self.hotkeys.register(3, 0x0002 | 0x0001, ord("C"), self._on_hotkey_camera)
        self.hotkeys.register(4, 0x0002 | 0x0001, ord("R"), self.controller.open_recordings_folder)

    def _on_hotkey_dual_record(self):
        if self.controller.is_dual_recording():
            self._on_stop_dual_recording()
        else:
            self._show_window()
            self._select_scene("dual")
            self._on_start_dual_recording()

    def _on_hotkey_mirror(self):
        self._show_window()
        self._select_scene("mirror")
        self._on_launch_mirror()

    def _on_hotkey_camera(self):
        self._show_window()
        self._select_scene("camera")
        self.controller.launch_stealth_camera(facing="back", audio_mic=True)

    def _show_window(self):
        self.deiconify()
        self.lift()
        self.focus_force()

    def _on_minimize_to_tray(self):
        self.withdraw()
        self.tray.notify(
            "OmniCapture Studio",
            "Running in background. Click tray icon or press Ctrl+Alt+D to record."
        )

    def _on_window_close(self):
        if self.controller.is_dual_recording():
            if not messagebox.askyesno(
                "Recording Active",
                "A studio recording is currently in progress.\n\n"
                "Stop recording and exit now?",
                parent=self
            ):
                return

        if self.minimize_to_tray_var.get():
            self._on_minimize_to_tray()
        else:
            self._on_app_exit()

    def _on_app_exit(self):
        if self.controller.is_dual_recording():
            if not messagebox.askyesno(
                "Recording Active",
                "A studio recording is currently in progress.\n\n"
                "Stop recording and exit now?",
                parent=self
            ):
                return

        self._meter_timer_active = False
        self._save_window_geometry()
        self._uninstall_wndproc_hook()
        if self.controller.is_dual_recording():
            self.controller.stop_dual_recording()
        self.taskbar.set_recording_overlay(False)
        self.taskbar.set_progress_state(TaskbarManager.TBPF_NOPROGRESS)
        self.taskbar.cleanup()
        self.single_instance.release()
        self.controller.stop_device_poller()
        self.hotkeys.stop()
        self.tray.stop()
        self.destroy()
        sys.exit(0)

    def destroy(self):
        if hasattr(self, "single_instance") and self.single_instance:
            self.single_instance.release()
        super().destroy()
