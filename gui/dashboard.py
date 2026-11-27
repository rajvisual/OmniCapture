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
from gui.components.top_bar import UnifiedTopBar
from gui.components.audio_meter import AudioChannelStrip
from gui.components.status_chip import StatusChip
from gui.components.empty_state import CanvasEmptyState
from gui.components.toast import ToastNotificationManager
from gui.components.command_palette import CommandPalette
from gui.dialogs.recordings import RecordingsGalleryDialog
from gui.dialogs.settings import StudioSettingsDialog
from gui.dialogs.diagnostics import DiagnosticsDialog
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
        super().__init__()

        self.app_config = config
        self.controller = GUIController(config)

        # Active Studio Scene / Preset: "dual" | "mirror" | "camera" | "screen"
        self.active_scene = "dual"
        self.show_guides = True

        # Initial theme setup (detect system theme on first launch if not configured)
        saved_theme = self.app_config.get("theme")
        if not saved_theme:
            saved_theme = OmniTheme.detect_system_theme()
            self.app_config["theme"] = saved_theme
        OmniTheme.set_theme(saved_theme)

        # Appearance & Window Configuration
        tokens = OmniTheme.get_tokens()
        self.title("OmniCapture Studio")
        self._restore_window_geometry()
        self.minsize(1040, 700)
        self.configure(fg_color=tokens.bg_root)

        self._set_app_icon()

        # Apply Windows 11 DWM Attributes (Caption color, Dark Mode, Rounded corners, Mica)
        self.after(50, self._apply_dwm)

        # In-App Toast Notification Engine
        self.toasts = ToastNotificationManager(self)

        # System Preferences
        self.minimize_to_tray_var = ctk.BooleanVar(value=True)
        self.enable_hotkeys_var = ctk.BooleanVar(value=True)

        # System Tray Integration
        self.tray = SystemTrayManager(
            on_show=self._show_window,
            on_exit=self._on_app_exit,
            on_dual_record=self._on_hotkey_dual_record,
            on_mirror=self._on_hotkey_mirror,
            on_camera=self._on_hotkey_camera,
            on_open_recordings=self.controller.open_recordings_folder
        )

        # Global System Hotkeys Manager
        self.hotkeys = GlobalHotkeyManager(root_window=self)
        self._setup_hotkeys()

        # Timers & Animation States
        self._meter_timer_active = False
        self._recording_pulse_active = False
        self._pulse_phase = 0

        # Build Full Studio Architecture
        self._build_top_bar()
        self._build_center_and_inspector()
        self._build_bottom_production_dock()
        self._build_status_footer()

        # Keyboard Accelerators
        self._bind_keyboard_shortcuts()

        # Wire window events & device poller
        self.protocol("WM_DELETE_WINDOW", self._on_window_close)
        self.controller.register_device_listener(self._on_device_state_changed)
        self.controller.start_device_poller(interval_sec=2.5)

        self.tray.start()
        if self.enable_hotkeys_var.get():
            self.hotkeys.start()

        # Start simulated audio room activity
        self._start_audio_level_animation()

        # Initial device discovery
        self.after(250, self._initial_refresh)

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
        w = self.app_config.get("window_width", 1180)
        h = self.app_config.get("window_height", 800)
        x = self.app_config.get("window_x")
        y = self.app_config.get("window_y")
        if x is not None and y is not None:
            self.geometry(f"{w}x{h}+{x}+{y}")
        else:
            self.geometry(f"{w}x{h}")

    def _save_window_geometry(self):
        try:
            self.app_config["window_width"] = self.winfo_width()
            self.app_config["window_height"] = self.winfo_height()
            self.app_config["window_x"] = self.winfo_x()
            self.app_config["window_y"] = self.winfo_y()
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
            "open_about": self._open_about_dialog,
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

        self.aspect_seg = ctk.CTkSegmentedButton(
            toolstrip,
            values=["16:9", "9:16", "Fit"],
            selected_color=tokens.accent_primary,
            corner_radius=OmniTheme.RADIUS_CONTROL,
            height=26,
            font=OmniTheme.font_caption(),
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

        # 16:9 Viewport Box (Level 1 Surface)
        self.canvas_viewport = ctk.CTkFrame(
            self.canvas_panel,
            fg_color=tokens.bg_root,
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

        insp_header = ctk.CTkFrame(self.inspector_panel, fg_color=tokens.bg_header, height=36, corner_radius=0)
        insp_header.pack(fill="x")
        self.insp_title_lbl = ctk.CTkLabel(
            insp_header,
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
            fg_color=tokens.bg_raised,
            border_width=1,
            border_color=tokens.border_default,
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
            font=ctk.CTkFont(family="Segoe UI", size=16),
            text_color=tokens.text_dim
        )
        self.cv_crosshair.place(relx=0.5, rely=0.5, anchor="center")

        self.cv_screen_title = ctk.CTkLabel(
            self.cv_screen_box,
            text="PC Primary Display (Direct3D 11)",
            font=OmniTheme.font_section(),
            text_color=tokens.text_primary
        )
        self.cv_screen_title.pack(anchor="center", pady=(60, 4))

        self.cv_screen_sub = ctk.CTkLabel(
            self.cv_screen_box,
            text="1920x1080 @ 60 FPS",
            font=OmniTheme.font_mono(10),
            text_color=tokens.text_muted
        )
        self.cv_screen_sub.pack(anchor="center")

        # PiP Mobile Camera Box (Dual mode)
        self.cv_pip_box = ctk.CTkFrame(
            self.cv_screen_box,
            fg_color=tokens.bg_header,
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
            font=ctk.CTkFont(size=9, weight="bold"),
            text_color=tokens.text_primary
        )
        self.cv_pip_lbl.pack(expand=True)

        # Active Recording Tally HUD
        self.cv_recording_hud = ctk.CTkFrame(
            self.canvas_viewport,
            fg_color=tokens.bg_raised,
            corner_radius=OmniTheme.RADIUS_CONTROL,
            border_width=1,
            border_color=tokens.status_recording
        )

        hud_row = ctk.CTkFrame(self.cv_recording_hud, fg_color="transparent")
        hud_row.pack(padx=16, pady=8)

        self.cv_tally_dot = ctk.CTkLabel(
            hud_row,
            text="● REC",
            font=ctk.CTkFont(size=11, weight="bold"),
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

    def _build_inspector_properties(self, tokens: ThemeTokens):
        # 1. Camera Sensor
        ctk.CTkLabel(self.insp_scroll, text="Camera sensor", font=OmniTheme.font_caption(), text_color=tokens.text_muted).pack(anchor="w", pady=(2, 4))
        self.prop_cam_facing = ctk.CTkSegmentedButton(
            self.insp_scroll,
            values=["Back", "Front"],
            selected_color=tokens.accent_primary,
            corner_radius=OmniTheme.RADIUS_CONTROL,
            height=OmniTheme.CONTROL_HEIGHT
        )
        self.prop_cam_facing.set("Back")
        self.prop_cam_facing.pack(fill="x", pady=(0, 10))

        # 2. Frame Rate
        ctk.CTkLabel(self.insp_scroll, text="Capture frame rate", font=OmniTheme.font_caption(), text_color=tokens.text_muted).pack(anchor="w", pady=(0, 4))
        self.prop_fps = ctk.CTkSegmentedButton(
            self.insp_scroll,
            values=["30 fps", "60 fps"],
            selected_color=tokens.accent_primary,
            corner_radius=OmniTheme.RADIUS_CONTROL,
            height=OmniTheme.CONTROL_HEIGHT
        )
        self.prop_fps.set("60 fps")
        self.prop_fps.pack(fill="x", pady=(0, 10))

        # 3. Container Format
        ctk.CTkLabel(self.insp_scroll, text="Video container", font=OmniTheme.font_caption(), text_color=tokens.text_muted).pack(anchor="w", pady=(0, 4))
        self.prop_format = ctk.CTkSegmentedButton(
            self.insp_scroll,
            values=["MP4", "MKV (Crash-Safe)"],
            selected_color=tokens.accent_primary,
            corner_radius=OmniTheme.RADIUS_CONTROL,
            height=OmniTheme.CONTROL_HEIGHT
        )
        self.prop_format.set("MP4")
        self.prop_format.pack(fill="x", pady=(0, 10))

        # 4. Input Mode (UHID)
        ctk.CTkLabel(self.insp_scroll, text="Touch input mode", font=OmniTheme.font_caption(), text_color=tokens.text_muted).pack(anchor="w", pady=(0, 4))
        self.prop_input_mode = ctk.CTkSegmentedButton(
            self.insp_scroll,
            values=["Standard Touch", "Hardware (UHID)"],
            selected_color=tokens.accent_primary,
            corner_radius=OmniTheme.RADIUS_CONTROL,
            height=OmniTheme.CONTROL_HEIGHT
        )
        self.prop_input_mode.set("Standard Touch")
        self.prop_input_mode.pack(fill="x", pady=(0, 12))

        # 5. Switches (Fluent 32px standard)
        self.prop_preview_var = ctk.BooleanVar(value=True)
        self.sw_preview = ctk.CTkSwitch(
            self.insp_scroll,
            text="Show preview window",
            variable=self.prop_preview_var,
            font=OmniTheme.font_body(),
            progress_color=tokens.accent_primary
        )
        self.sw_preview.pack(anchor="w", pady=4)

        self.prop_screen_off_var = ctk.BooleanVar(value=True)
        self.sw_screen_off = ctk.CTkSwitch(
            self.insp_scroll,
            text="Turn mobile screen off",
            variable=self.prop_screen_off_var,
            font=OmniTheme.font_body(),
            progress_color=tokens.accent_primary
        )
        self.sw_screen_off.pack(anchor="w", pady=4)

        self.prop_upload_var = ctk.BooleanVar(value=False)
        self.sw_upload = ctk.CTkSwitch(
            self.insp_scroll,
            text="Auto-upload to Drive",
            variable=self.prop_upload_var,
            font=OmniTheme.font_body(),
            progress_color=tokens.status_connected
        )
        self.sw_upload.pack(anchor="w", pady=4)

        # 6. Wi-Fi Switch Action
        self.wifi_switch_btn = ctk.CTkButton(
            self.insp_scroll,
            text="Switch to Wi-Fi ADB",
            height=OmniTheme.CONTROL_HEIGHT,
            font=OmniTheme.font_body(),
            fg_color=tokens.bg_input,
            hover_color=tokens.bg_hover,
            text_color=tokens.text_primary,
            border_width=1,
            border_color=tokens.border_subtle,
            corner_radius=OmniTheme.RADIUS_CONTROL,
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
            height=195,
            corner_radius=0
        )
        self.dock_panel.pack(fill="x", side="bottom")

        self.dock_panel.columnconfigure(0, weight=1) # Scenes
        self.dock_panel.columnconfigure(1, weight=1) # Sources
        self.dock_panel.columnconfigure(2, weight=2) # Audio Mixer
        self.dock_panel.columnconfigure(3, weight=1) # Master Controls

        # -----------------------------
        # DOCK 1: SCENES
        # -----------------------------
        d1 = ctk.CTkFrame(self.dock_panel, fg_color="transparent")
        d1.grid(row=0, column=0, sticky="nsew", padx=6, pady=8)

        ctk.CTkLabel(d1, text="Scenes", font=OmniTheme.font_section(), text_color=tokens.text_primary).pack(anchor="w", padx=8, pady=(0, 6))

        self.btn_scene_dual = self._create_scene_button(d1, "Dual Stream (PC+Cam)", "dual", active=True)
        self.btn_scene_mirror = self._create_scene_button(d1, "Screen Mirror", "mirror")
        self.btn_scene_camera = self._create_scene_button(d1, "Camera Feed", "camera")
        self.btn_scene_screen = self._create_scene_button(d1, "Screen Record", "screen")

        # -----------------------------
        # DOCK 2: SOURCES
        # -----------------------------
        d2 = ctk.CTkFrame(self.dock_panel, fg_color="transparent")
        d2.grid(row=0, column=1, sticky="nsew", padx=6, pady=8)

        ctk.CTkLabel(d2, text="Sources", font=OmniTheme.font_section(), text_color=tokens.text_primary).pack(anchor="w", padx=8, pady=(0, 6))

        self.source_pc_check = ctk.CTkCheckBox(d2, text="PC display (gdigrab)", font=OmniTheme.font_body(), text_color=tokens.text_primary)
        self.source_pc_check.select()
        self.source_pc_check.pack(anchor="w", padx=8, pady=3)

        self.source_cam_check = ctk.CTkCheckBox(d2, text="Phone camera sensor", font=OmniTheme.font_body(), text_color=tokens.text_primary)
        self.source_cam_check.select()
        self.source_cam_check.pack(anchor="w", padx=8, pady=3)

        self.source_uhid_check = ctk.CTkCheckBox(d2, text="UHID touch mouse", font=OmniTheme.font_body(), text_color=tokens.text_primary)
        self.source_uhid_check.pack(anchor="w", padx=8, pady=3)

        # -----------------------------
        # DOCK 3: AUDIO MIXER
        # -----------------------------
        d3 = ctk.CTkFrame(self.dock_panel, fg_color="transparent")
        d3.grid(row=0, column=2, sticky="nsew", padx=8, pady=8)

        ctk.CTkLabel(d3, text="Audio mixer", font=OmniTheme.font_section(), text_color=tokens.text_primary).pack(anchor="w", padx=4, pady=(0, 4))

        self.strip_mic = AudioChannelStrip(d3, channel_name="Phone microphone", initial_volume=0.85)
        self.strip_mic.pack(fill="x", padx=4, pady=(0, 4))

        self.strip_pc = AudioChannelStrip(d3, channel_name="Desktop playback", initial_volume=0.75)
        self.strip_pc.pack(fill="x", padx=4)

        # -----------------------------
        # DOCK 4: MASTER CONTROLS
        # -----------------------------
        d4 = ctk.CTkFrame(self.dock_panel, fg_color="transparent")
        d4.grid(row=0, column=3, sticky="nsew", padx=12, pady=8)

        ctk.CTkLabel(d4, text="Controls", font=OmniTheme.font_section(), text_color=tokens.text_primary).pack(anchor="w", pady=(0, 6))

        # Primary Action: 44px primary button height
        self.master_record_btn = ctk.CTkButton(
            d4,
            text="Start Recording",
            height=OmniTheme.BUTTON_PRIMARY_HEIGHT,
            font=OmniTheme.font_section(),
            fg_color=tokens.accent_primary,
            hover_color=tokens.accent_hover,
            corner_radius=OmniTheme.RADIUS_CONTROL,
            command=self._on_master_record_click
        )
        self.master_record_btn.pack(fill="x", pady=2)

        self.master_mirror_btn = ctk.CTkButton(
            d4,
            text="Launch Mirror",
            height=OmniTheme.CONTROL_HEIGHT,
            font=OmniTheme.font_body(),
            fg_color=tokens.bg_input,
            hover_color=tokens.bg_hover,
            text_color=tokens.text_primary,
            border_width=1,
            border_color=tokens.border_subtle,
            corner_radius=OmniTheme.RADIUS_CONTROL,
            command=self._on_launch_mirror
        )
        self.master_mirror_btn.pack(fill="x", pady=2)

        self.master_recordings_btn = ctk.CTkButton(
            d4,
            text="Media Library",
            height=OmniTheme.CONTROL_HEIGHT,
            font=OmniTheme.font_body(),
            fg_color=tokens.bg_input,
            hover_color=tokens.bg_hover,
            text_color=tokens.text_primary,
            border_width=1,
            border_color=tokens.border_subtle,
            corner_radius=OmniTheme.RADIUS_CONTROL,
            command=self._open_recordings_window
        )
        self.master_recordings_btn.pack(fill="x", pady=2)

        self.master_settings_btn = ctk.CTkButton(
            d4,
            text="Preferences",
            height=OmniTheme.CONTROL_HEIGHT,
            font=OmniTheme.font_body(),
            fg_color=tokens.bg_input,
            hover_color=tokens.bg_hover,
            text_color=tokens.text_primary,
            border_width=1,
            border_color=tokens.border_subtle,
            corner_radius=OmniTheme.RADIUS_CONTROL,
            command=self._open_settings_window
        )
        self.master_settings_btn.pack(fill="x", pady=2)

    def _create_scene_button(self, parent, label: str, scene_id: str, active: bool = False) -> ctk.CTkButton:
        tokens = OmniTheme.get_tokens()
        btn = ctk.CTkButton(
            parent,
            text=label,
            height=OmniTheme.CONTROL_HEIGHT,
            font=OmniTheme.font_body(),
            anchor="w",
            fg_color=tokens.accent_primary if active else tokens.bg_input,
            hover_color=tokens.accent_hover if active else tokens.bg_hover,
            text_color="#FFFFFF" if active else tokens.text_primary,
            border_width=0 if active else 1,
            border_color=tokens.border_subtle,
            corner_radius=OmniTheme.RADIUS_CONTROL,
            command=lambda sid=scene_id: self._select_scene(sid)
        )
        btn.pack(fill="x", padx=8, pady=2)
        return btn

    def _select_scene(self, scene_id: str):
        self.active_scene = scene_id
        tokens = OmniTheme.get_tokens()

        for btn, sid in [
            (self.btn_scene_dual, "dual"),
            (self.btn_scene_mirror, "mirror"),
            (self.btn_scene_camera, "camera"),
            (self.btn_scene_screen, "screen")
        ]:
            is_active = (sid == scene_id)
            btn.configure(
                fg_color=tokens.accent_primary if is_active else tokens.bg_input,
                hover_color=tokens.accent_hover if is_active else tokens.bg_hover,
                text_color="#FFFFFF" if is_active else tokens.text_primary,
                border_width=0 if is_active else 1
            )

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

        self.foot_status_chip = StatusChip(self.footer, text="STUDIO READY", state="ready")
        self.foot_status_chip.pack(side="left", padx=12, pady=2)

        self.foot_rec_time = ctk.CTkLabel(
            self.footer,
            text="REC: 00:00:00",
            font=OmniTheme.font_mono(11),
            text_color=tokens.text_muted
        )
        self.foot_rec_time.pack(side="left", padx=10)

        self.foot_fps_lbl = ctk.CTkLabel(
            self.footer,
            text="FPS: 60.0",
            font=OmniTheme.font_mono(11),
            text_color=tokens.text_dim
        )
        self.foot_fps_lbl.pack(side="left", padx=10)

        self.foot_bitrate_lbl = ctk.CTkLabel(
            self.footer,
            text="BITRATE: 8.0M",
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

        self.hotkey_legend = ctk.CTkLabel(
            self.footer,
            text="Ctrl+P: Command Palette  ·  Ctrl+Alt+D: Record",
            font=OmniTheme.font_caption(),
            text_color=tokens.text_dim
        )
        self.hotkey_legend.pack(side="right", padx=16)

    def _query_disk_space_str(self) -> str:
        try:
            rec_dir = self.controller.recordings_dir
            usage = shutil.disk_usage(rec_dir)
            free_gb = usage.free / (1024 ** 3)
            return f"DISK: {free_gb:.1f} GB free"
        except Exception:
            return "DISK: OK"

    # -------------------------------------------------------------------------
    # 5. RUNTIME THEME SWITCHING ENGINE
    # -------------------------------------------------------------------------

    def _toggle_theme(self):
        """Switch between Light Minimal and Dark Liquid Glass instantly."""
        new_theme = "light" if OmniTheme.get_tokens().is_dark else "dark"
        self.app_config["theme"] = new_theme
        OmniTheme.set_theme(new_theme)
        tokens = OmniTheme.get_tokens()

        # Update root & panels
        self.configure(fg_color=tokens.bg_root)
        self.canvas_panel.configure(fg_color=tokens.bg_panel, border_color=tokens.border_subtle)
        self.inspector_panel.configure(fg_color=tokens.bg_panel, border_color=tokens.border_subtle)
        self.dock_panel.configure(fg_color=tokens.bg_panel, border_color=tokens.border_subtle)
        self.footer.configure(fg_color=tokens.bg_header)
        self.canvas_viewport.configure(fg_color=tokens.bg_root)

        # Update components
        self.top_bar.apply_tokens(tokens)
        self.cv_empty_state.apply_tokens(tokens)
        self.strip_mic.apply_tokens(tokens)
        self.strip_pc.apply_tokens(tokens)
        self.foot_status_chip.apply_tokens(tokens)

        # Update controls
        self.master_mirror_btn.configure(fg_color=tokens.bg_input, hover_color=tokens.bg_hover, text_color=tokens.text_primary, border_color=tokens.border_subtle)
        self.master_recordings_btn.configure(fg_color=tokens.bg_input, hover_color=tokens.bg_hover, text_color=tokens.text_primary, border_color=tokens.border_subtle)
        self.master_settings_btn.configure(fg_color=tokens.bg_input, hover_color=tokens.bg_hover, text_color=tokens.text_primary, border_color=tokens.border_subtle)
        self.wifi_switch_btn.configure(fg_color=tokens.bg_input, hover_color=tokens.bg_hover, text_color=tokens.text_primary, border_color=tokens.border_subtle)

        # Re-apply DWM window frame
        self._apply_dwm()
        self.toasts.show("Theme Switched", f"Active theme: {tokens.name.title()}", level="info")

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
                pulse_color = "#DC2626" if self._pulse_phase < 8 else "#EF4444"
                try:
                    self.master_record_btn.configure(fg_color=pulse_color)
                except Exception:
                    pass

            self.after(80, _loop)

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
            {"title": "Studio Preferences & Settings", "category": "Settings", "shortcut": "Ctrl+,", "action": self._open_settings_window, "keywords": "config options format"},
            {"title": "Scene: Dual Stream", "category": "Scenes", "shortcut": "1", "action": lambda: self._select_scene("dual"), "keywords": "preset layout"},
            {"title": "Scene: Screen Mirror", "category": "Scenes", "shortcut": "2", "action": lambda: self._select_scene("mirror"), "keywords": "preset layout"},
            {"title": "Scene: Camera Viewfinder", "category": "Scenes", "shortcut": "3", "action": lambda: self._select_scene("camera"), "keywords": "preset layout"},
            {"title": "Scene: Screen Record", "category": "Scenes", "shortcut": "4", "action": lambda: self._select_scene("screen"), "keywords": "preset layout"},
            {"title": "Minimize to System Tray", "category": "Window", "shortcut": "Ctrl+W", "action": self._on_minimize_to_tray, "keywords": "hide background"},
            {"title": "Exit OmniCapture Studio", "category": "Window", "shortcut": "Ctrl+Q", "action": self._on_app_exit, "keywords": "quit close"},
        ]
        CommandPalette(self, commands)

    def _open_recordings_window(self):
        RecordingsGalleryDialog(self, self.controller, on_toast=self.toasts.show)

    def _open_settings_window(self):
        StudioSettingsDialog(
            self,
            self.app_config,
            self.controller,
            self.minimize_to_tray_var,
            self.enable_hotkeys_var,
            on_toast=self.toasts.show
        )

    def _open_diagnostics_window(self):
        DiagnosticsDialog(self, self.controller, on_toast=self.toasts.show)

    def _open_hotkeys_guide(self):
        w = ctk.CTkToplevel(self)
        w.title("Keyboard Shortcuts")
        w.geometry("440x360")
        w.resizable(False, False)
        tokens = OmniTheme.get_tokens()
        w.configure(fg_color=tokens.bg_root)

        box = ctk.CTkFrame(w, fg_color=tokens.bg_panel, corner_radius=OmniTheme.RADIUS_CARD)
        box.pack(fill="both", expand=True, padx=16, pady=16)

        ctk.CTkLabel(box, text="Global Keyboard Shortcuts", font=OmniTheme.font_section(), text_color=tokens.text_primary).pack(anchor="w", padx=14, pady=(12, 8))

        shortcuts = [
            ("Ctrl + P", "Open Command Palette"),
            ("Ctrl + Alt + D", "Start / Stop Dual Recording"),
            ("Ctrl + Alt + M", "Launch Screen Mirror"),
            ("Ctrl + Alt + C", "Launch Camera Viewfinder"),
            ("Ctrl + Alt + R", "Open Recordings Folder"),
            ("Ctrl + Shift + L", "Release Camera Sensor Lock"),
            ("F5", "Refresh Connected Devices"),
            ("1 / 2 / 3 / 4", "Switch Active Studio Scene"),
            ("Ctrl + ,", "Open Preferences Dialog"),
            ("Ctrl + W", "Minimize to System Tray"),
            ("Ctrl + Q", "Exit Application"),
        ]

        for key, desc in shortcuts:
            r = ctk.CTkFrame(box, fg_color="transparent")
            r.pack(fill="x", padx=14, pady=3)
            ctk.CTkLabel(r, text=key, font=OmniTheme.font_mono(10, weight="bold"), text_color=tokens.accent_primary, width=140, anchor="w").pack(side="left")
            ctk.CTkLabel(r, text=desc, font=OmniTheme.font_body(), text_color=tokens.text_secondary).pack(side="left")

    def _open_about_dialog(self):
        messagebox.showinfo(
            "About OmniCapture Studio",
            "OmniCapture Studio v1.3.0\n\n"
            "Hardware-Accelerated Dual PC Screen & Mobile Camera Studio.\n"
            "Engineered with Windows 11 Fluent Design, DWM Mica/Acrylic support, "
            "and synchronized multi-stream recording.\n\n"
            "Open source under the Apache 2.0 License.",
            parent=self
        )

    def _reset_window_size(self):
        self.geometry("1180x800")
        self.toasts.show("Window Layout", "Reset to default 1180x800 resolution", level="info")

    def _bind_keyboard_shortcuts(self):
        self.bind("<Control-p>", lambda e: self._open_command_palette())
        self.bind("<Control-P>", lambda e: self._open_command_palette())
        self.bind("<Control-Shift-P>", lambda e: self._open_command_palette())
        self.bind("<Control-Shift-p>", lambda e: self._open_command_palette())
        self.bind("<Control-k>", lambda e: self._open_command_palette())
        self.bind("<Control-K>", lambda e: self._open_command_palette())
        self.bind("<F5>", lambda e: self._on_manual_refresh())
        self.bind("<Control-comma>", lambda e: self._open_settings_window())
        self.bind("<Control-q>", lambda e: self._on_app_exit())
        self.bind("<Control-w>", lambda e: self._on_minimize_to_tray())

        self.bind("1", lambda e: self._select_scene("dual") if not self._is_entry_focused() else None)
        self.bind("2", lambda e: self._select_scene("mirror") if not self._is_entry_focused() else None)
        self.bind("3", lambda e: self._select_scene("camera") if not self._is_entry_focused() else None)
        self.bind("4", lambda e: self._select_scene("screen") if not self._is_entry_focused() else None)

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
            self.toasts.show("Recording Started", "Parallel dual streams recording to disk", level="success")
            self.tray.notify("OmniCapture Studio", "Dual recording in progress")
        else:
            self.foot_status_chip.set_status(f"ERROR: {msg[:25]}", state="warning")
            self.toasts.show("Recording Failed", msg, level="error")

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
            self.toasts.show("Recording Saved", f"Capture completed ({dur})", level="success")
            self.tray.notify("OmniCapture Studio", f"Recording saved ({status}, {dur})")

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
            batt = state.get("battery", {})
            lvl = batt.get("level", "")
            batt_str = f" · {lvl} ⚡" if lvl and lvl != "N/A" else ""
            device_text = f"● {model} ({conn_str}){batt_str}"
            self.top_bar.set_device_status(device_text)

            # Switch Canvas from Empty State to Active Viewport Representation
            self.cv_empty_state.place_forget()
            self.cv_content.place(relx=0.5, rely=0.5, anchor="center")
        elif status == "UNAUTHORIZED":
            self.top_bar.set_device_status("Unauthorized: unlock phone and tap 'Always allow'")
            self.cv_content.place_forget()
            self.cv_empty_state.place(relx=0.5, rely=0.5, anchor="center", relwidth=0.85, relheight=0.7)
        elif status == "OFFLINE":
            self.top_bar.set_device_status("Device offline: reconnect USB cable")
            self.cv_content.place_forget()
            self.cv_empty_state.place(relx=0.5, rely=0.5, anchor="center", relwidth=0.85, relheight=0.7)
        else:
            self.top_bar.set_device_status("Connect a phone via USB to start")
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
        self._meter_timer_active = False
        self._save_window_geometry()
        if self.controller.is_dual_recording():
            self.controller.stop_dual_recording()
        self.controller.stop_device_poller()
        self.hotkeys.stop()
        self.tray.stop()
        self.destroy()
        sys.exit(0)
