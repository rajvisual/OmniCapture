import os
import sys
import time
import subprocess
import threading
from pathlib import Path
from typing import Optional, Dict, Any, List

import customtkinter as ctk
from PIL import Image

from gui.theme import OmniTheme
from gui.controller import GUIController
from gui.tray import SystemTrayManager
from gui.hotkeys import GlobalHotkeyManager
from core.resource_path import resolve_resource, get_base_dir, get_recordings_dir

class OmniCaptureApp(ctk.CTk):
    """
    OmniCapture Broadcast Studio Dashboard.
    Inspired by OBS Studio, Streamlabs, and modern creator capture consoles:
    - Center Stage: Live 16:9 Studio Canvas & Viewfinder
    - Right Inspector: Contextual Properties & Hardware Settings
    - Bottom Production Dock: Scenes, Sources, Audio Mixer, and Master Controls
    - System Status Bar: Live broadcast telemetry (REC timer, FPS, bitrate, battery)
    """

    def __init__(self, config: Dict[str, Any]):
        super().__init__()

        self.config = config
        self.controller = GUIController(config)

        # Active Studio Scene / Preset: "dual" | "mirror" | "camera" | "screen"
        self.active_scene = "dual"

        # Appearance & Window Configuration
        OmniTheme.apply_appearance()
        self.title("OmniCapture Studio")
        self.geometry("1160x780")
        self.minsize(1020, 680)
        self.configure(fg_color=OmniTheme.BG_ROOT)

        self._set_app_icon()

        # System Preferences
        self.minimize_to_tray_var = ctk.BooleanVar(value=True)
        self.enable_hotkeys_var = ctk.BooleanVar(value=True)

        self.tray = SystemTrayManager(
            on_show=self._show_window,
            on_exit=self._on_app_exit,
            on_dual_record=self._on_hotkey_dual_record,
            on_mirror=self._on_hotkey_mirror,
            on_camera=self._on_hotkey_camera,
            on_open_recordings=self.controller.open_recordings_folder
        )

        self.hotkeys = GlobalHotkeyManager(root_window=self)
        self._setup_hotkeys()

        # Build Studio Architecture
        self._build_top_toolbar()
        self._build_center_and_inspector()
        self._build_bottom_production_dock()
        self._build_status_footer()

        # Wire window events & device poller
        self.protocol("WM_DELETE_WINDOW", self._on_window_close)
        self.controller.register_device_listener(self._on_device_state_changed)
        self.controller.start_device_poller(interval_sec=2.5)

        self.tray.start()
        if self.enable_hotkeys_var.get():
            self.hotkeys.start()

        self.after(200, self._initial_refresh)

    def _set_app_icon(self):
        ico_path = resolve_resource("assets/logo/omnicapture.ico")
        if ico_path.is_file():
            try:
                self.iconbitmap(str(ico_path))
            except Exception:
                pass

    # -------------------------------------------------------------------------
    # TOP TOOLBAR (Header)
    # -------------------------------------------------------------------------

    def _build_top_toolbar(self):
        bar = ctk.CTkFrame(self, fg_color=OmniTheme.BG_DOCK, height=44, corner_radius=0)
        bar.pack(fill="x", side="top")

        # Brand / Studio Title
        brand = ctk.CTkFrame(bar, fg_color="transparent")
        brand.pack(side="left", padx=16, pady=8)

        logo_path = resolve_resource("assets/logo/omnicapture-icon.png")
        if logo_path.is_file():
            try:
                pil_img = Image.open(str(logo_path)).resize((22, 22), Image.Resampling.LANCZOS)
                self.logo_ctk = ctk.CTkImage(light_image=pil_img, dark_image=pil_img, size=(22, 22))
                logo_lbl = ctk.CTkLabel(brand, image=self.logo_ctk, text="")
                logo_lbl.pack(side="left", padx=(0, 8))
            except Exception:
                pass

        title = ctk.CTkLabel(
            brand,
            text="OmniCapture Studio",
            font=ctk.CTkFont(family="Segoe UI", size=14, weight="bold"),
            text_color=OmniTheme.TEXT_MAIN
        )
        title.pack(side="left")

        ver = ctk.CTkLabel(
            brand,
            text="1.2.0",
            font=ctk.CTkFont(family="Segoe UI", size=11),
            text_color=OmniTheme.TEXT_DIM
        )
        ver.pack(side="left", padx=(6, 0))

        # Center Status Pill / Telemetry
        center_status = ctk.CTkFrame(bar, fg_color="transparent")
        center_status.pack(side="left", expand=True)

        self.top_device_lbl = ctk.CTkLabel(
            center_status,
            text="Searching for Android device...",
            font=ctk.CTkFont(family="Segoe UI", size=12),
            text_color=OmniTheme.TEXT_MUTED
        )
        self.top_device_lbl.pack(side="left")

        # Right Quick Controls
        actions = ctk.CTkFrame(bar, fg_color="transparent")
        actions.pack(side="right", padx=16, pady=8)

        refresh_btn = ctk.CTkButton(
            actions,
            text="Refresh",
            width=65,
            height=26,
            font=ctk.CTkFont(size=11),
            fg_color=OmniTheme.BG_INPUT,
            hover_color=OmniTheme.BG_CARD_HOVER,
            corner_radius=OmniTheme.RADIUS_CONTROL,
            command=self._on_manual_refresh
        )
        refresh_btn.pack(side="left", padx=4)

        unlock_btn = ctk.CTkButton(
            actions,
            text="Release lock",
            width=90,
            height=26,
            font=ctk.CTkFont(size=11),
            fg_color=OmniTheme.BG_INPUT,
            hover_color=OmniTheme.BG_CARD_HOVER,
            text_color=OmniTheme.TEXT_MUTED,
            corner_radius=OmniTheme.RADIUS_CONTROL,
            command=self._on_release_lock
        )
        unlock_btn.pack(side="left", padx=4)

    # -------------------------------------------------------------------------
    # MAIN STAGE: Live Canvas Viewport (Center) + Properties Inspector (Right)
    # -------------------------------------------------------------------------

    def _build_center_and_inspector(self):
        middle_container = ctk.CTkFrame(self, fg_color=OmniTheme.BG_ROOT, corner_radius=0)
        middle_container.pack(fill="both", expand=True, padx=12, pady=(10, 8))

        middle_container.columnconfigure(0, weight=3) # Canvas
        middle_container.columnconfigure(1, weight=1) # Inspector
        middle_container.rowconfigure(0, weight=1)

        # -----------------------------
        # 1. STUDIO CANVAS (Viewfinder)
        # -----------------------------
        self.canvas_frame = ctk.CTkFrame(
            middle_container,
            fg_color=OmniTheme.BG_CANVAS,
            corner_radius=OmniTheme.RADIUS_CARD,
            border_width=1,
            border_color=OmniTheme.BG_CARD_BORDER
        )
        self.canvas_frame.grid(row=0, column=0, sticky="nsew", padx=(0, 8))

        # Canvas Header Overlay (Mode indicator & resolution badge)
        canvas_top = ctk.CTkFrame(self.canvas_frame, fg_color="transparent", height=32)
        canvas_top.pack(fill="x", padx=16, pady=12)

        self.canvas_mode_lbl = ctk.CTkLabel(
            canvas_top,
            text="PREVIEW: DUAL RECORDING",
            font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"),
            text_color=OmniTheme.TEXT_MUTED
        )
        self.canvas_mode_lbl.pack(side="left")

        self.canvas_stats_lbl = ctk.CTkLabel(
            canvas_top,
            text="1920x1080  ·  60 FPS  ·  Low-Latency NVMe",
            font=ctk.CTkFont(family="Consolas", size=11),
            text_color=OmniTheme.TEXT_DIM
        )
        self.canvas_stats_lbl.pack(side="right")

        # Visual Canvas Viewport
        self.canvas_viewport = ctk.CTkFrame(self.canvas_frame, fg_color="#08090D", corner_radius=6)
        self.canvas_viewport.pack(fill="both", expand=True, padx=16, pady=(0, 16))

        # Canvas Interactive Visualizer Box
        self._build_canvas_visualizer()

        # -----------------------------
        # 2. PROPERTIES INSPECTOR (Right)
        # -----------------------------
        self.inspector_frame = ctk.CTkFrame(
            middle_container,
            fg_color=OmniTheme.BG_DOCK,
            corner_radius=OmniTheme.RADIUS_CARD,
            border_width=1,
            border_color=OmniTheme.BG_CARD_BORDER
        )
        self.inspector_frame.grid(row=0, column=1, sticky="nsew", padx=(0, 0))

        # Inspector Header
        insp_header = ctk.CTkFrame(self.inspector_frame, fg_color=OmniTheme.BG_DOCK_HEADER, height=34, corner_radius=0)
        insp_header.pack(fill="x")
        ctk.CTkLabel(
            insp_header,
            text="PROPERTIES",
            font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"),
            text_color=OmniTheme.TEXT_MUTED
        ).pack(side="left", padx=14, pady=8)

        # Inspector Form Content (Scrollable for compact screens)
        self.insp_scroll = ctk.CTkScrollableFrame(self.inspector_frame, fg_color="transparent")
        self.insp_scroll.pack(fill="both", expand=True, padx=12, pady=10)

        self._build_inspector_properties()

    def _build_canvas_visualizer(self):
        """Build the dynamic visual representation inside the 16:9 canvas."""
        # Clean container
        self.cv_content = ctk.CTkFrame(self.canvas_viewport, fg_color="transparent")
        self.cv_content.place(relx=0.5, rely=0.5, anchor="center")

        # Viewport Representation Layout
        self.cv_screen_box = ctk.CTkFrame(
            self.cv_content,
            fg_color="#13141B",
            border_width=1,
            border_color="#2A2C3A",
            width=360,
            height=200,
            corner_radius=6
        )
        self.cv_screen_box.pack(pady=6)
        self.cv_screen_box.pack_propagate(False)

        self.cv_screen_title = ctk.CTkLabel(
            self.cv_screen_box,
            text="PC Primary Display (gdigrab)",
            font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"),
            text_color=OmniTheme.TEXT_MAIN
        )
        self.cv_screen_title.pack(anchor="center", pady=(50, 4))

        self.cv_screen_sub = ctk.CTkLabel(
            self.cv_screen_box,
            text="1920x1080 @ 60 FPS",
            font=ctk.CTkFont(family="Consolas", size=11),
            text_color=OmniTheme.TEXT_MUTED
        )
        self.cv_screen_sub.pack(anchor="center")

        # PiP Camera Box (Visible in Dual Recording mode)
        self.cv_pip_box = ctk.CTkFrame(
            self.cv_screen_box,
            fg_color="#1C1E29",
            border_width=1,
            border_color=OmniTheme.ACCENT_PRIMARY,
            width=100,
            height=65,
            corner_radius=4
        )
        self.cv_pip_box.place(relx=0.95, rely=0.92, anchor="se")
        self.cv_pip_box.pack_propagate(False)

        ctk.CTkLabel(
            self.cv_pip_box,
            text="Mobile Cam",
            font=ctk.CTkFont(size=9, weight="bold"),
            text_color=OmniTheme.TEXT_MAIN
        ).pack(expand=True)

        # Active Recording Tally Overlay (Hidden when idle)
        self.cv_recording_hud = ctk.CTkFrame(self.canvas_viewport, fg_color="#180A0F", corner_radius=6, border_width=1, border_color=OmniTheme.STATUS_RECORDING)

        hud_row = ctk.CTkFrame(self.cv_recording_hud, fg_color="transparent")
        hud_row.pack(padx=16, pady=8)

        self.cv_tally_dot = ctk.CTkLabel(hud_row, text="● REC", font=ctk.CTkFont(size=12, weight="bold"), text_color=OmniTheme.STATUS_RECORDING)
        self.cv_tally_dot.pack(side="left", padx=(0, 10))

        self.cv_tally_timer = ctk.CTkLabel(hud_row, text="00:00:00", font=ctk.CTkFont(family="Consolas", size=14, weight="bold"), text_color=OmniTheme.TEXT_MAIN)
        self.cv_tally_timer.pack(side="left", padx=(0, 16))

        self.cv_tally_stats = ctk.CTkLabel(hud_row, text="PC: 0.0 MB  ·  Cam: 0.0 MB", font=ctk.CTkFont(family="Segoe UI", size=11), text_color=OmniTheme.TEXT_MUTED)
        self.cv_tally_stats.pack(side="left")

    def _build_inspector_properties(self):
        """Build contextual property controls in the right Inspector panel."""
        # 1. Camera Sensor
        ctk.CTkLabel(self.insp_scroll, text="Camera sensor", font=ctk.CTkFont(size=11), text_color=OmniTheme.TEXT_MUTED).pack(anchor="w", pady=(2, 4))
        self.prop_cam_facing = ctk.CTkSegmentedButton(
            self.insp_scroll,
            values=["Back", "Front"],
            selected_color=OmniTheme.ACCENT_PRIMARY,
            corner_radius=OmniTheme.RADIUS_CONTROL
        )
        self.prop_cam_facing.set("Back")
        self.prop_cam_facing.pack(fill="x", pady=(0, 12))

        # 2. Frame Rates
        ctk.CTkLabel(self.insp_scroll, text="Capture frame rate", font=ctk.CTkFont(size=11), text_color=OmniTheme.TEXT_MUTED).pack(anchor="w", pady=(0, 4))
        self.prop_fps = ctk.CTkSegmentedButton(
            self.insp_scroll,
            values=["30 fps", "60 fps"],
            selected_color=OmniTheme.ACCENT_PRIMARY,
            corner_radius=OmniTheme.RADIUS_CONTROL
        )
        self.prop_fps.set("60 fps")
        self.prop_fps.pack(fill="x", pady=(0, 12))

        # 3. Video Container Format
        ctk.CTkLabel(self.insp_scroll, text="Video container", font=ctk.CTkFont(size=11), text_color=OmniTheme.TEXT_MUTED).pack(anchor="w", pady=(0, 4))
        self.prop_format = ctk.CTkSegmentedButton(
            self.insp_scroll,
            values=["MP4", "MKV (Crash-Safe)"],
            selected_color=OmniTheme.ACCENT_PRIMARY,
            corner_radius=OmniTheme.RADIUS_CONTROL
        )
        self.prop_format.set("MP4")
        self.prop_format.pack(fill="x", pady=(0, 12))

        # 4. Input Mode (UHID)
        ctk.CTkLabel(self.insp_scroll, text="Touch input mode", font=ctk.CTkFont(size=11), text_color=OmniTheme.TEXT_MUTED).pack(anchor="w", pady=(0, 4))
        self.prop_input_mode = ctk.CTkSegmentedButton(
            self.insp_scroll,
            values=["Standard Touch", "Hardware (UHID)"],
            selected_color=OmniTheme.ACCENT_PRIMARY,
            corner_radius=OmniTheme.RADIUS_CONTROL
        )
        self.prop_input_mode.set("Standard Touch")
        self.prop_input_mode.pack(fill="x", pady=(0, 14))

        # 5. Toggles
        self.prop_preview_var = ctk.BooleanVar(value=True)
        ctk.CTkSwitch(self.insp_scroll, text="Show preview window", variable=self.prop_preview_var, progress_color=OmniTheme.ACCENT_PRIMARY).pack(anchor="w", pady=4)

        self.prop_screen_off_var = ctk.BooleanVar(value=True)
        ctk.CTkSwitch(self.insp_scroll, text="Turn mobile screen off", variable=self.prop_screen_off_var, progress_color=OmniTheme.ACCENT_PRIMARY).pack(anchor="w", pady=4)

        self.prop_upload_var = ctk.BooleanVar(value=False)
        ctk.CTkSwitch(self.insp_scroll, text="Auto-upload to Drive", variable=self.prop_upload_var, progress_color=OmniTheme.STATUS_CONNECTED).pack(anchor="w", pady=4)

        # Quick Wi-Fi switch button
        self.wifi_switch_btn = ctk.CTkButton(
            self.insp_scroll,
            text="Switch to Wi-Fi ADB",
            height=30,
            font=ctk.CTkFont(size=11),
            fg_color=OmniTheme.BG_INPUT,
            hover_color=OmniTheme.BG_CARD_HOVER,
            corner_radius=OmniTheme.RADIUS_CONTROL,
            command=self._on_switch_to_wireless
        )
        self.wifi_switch_btn.pack(fill="x", pady=(14, 4))

    # -------------------------------------------------------------------------
    # BOTTOM PRODUCTION DOCK: The 4 Classic Studio Docks
    # -------------------------------------------------------------------------

    def _build_bottom_production_dock(self):
        """The 4 OBS docks: Scenes, Sources, Audio Mixer, and Master Controls."""
        dock_container = ctk.CTkFrame(self, fg_color=OmniTheme.BG_DOCK, height=195, corner_radius=0)
        dock_container.pack(fill="x", side="bottom")

        dock_container.columnconfigure(0, weight=1) # Scenes
        dock_container.columnconfigure(1, weight=1) # Sources
        dock_container.columnconfigure(2, weight=2) # Audio Mixer
        dock_container.columnconfigure(3, weight=1) # Controls

        # -----------------------------
        # DOCK 1: SCENES / MODES
        # -----------------------------
        d1 = ctk.CTkFrame(dock_container, fg_color="transparent")
        d1.grid(row=0, column=0, sticky="nsew", padx=6, pady=8)

        ctk.CTkLabel(d1, text="SCENES", font=ctk.CTkFont(size=10, weight="bold"), text_color=OmniTheme.TEXT_MUTED).pack(anchor="w", padx=8, pady=(0, 6))

        self.btn_scene_dual = self._create_scene_button(d1, "Dual Recording", "dual", active=True)
        self.btn_scene_mirror = self._create_scene_button(d1, "Screen Mirror", "mirror")
        self.btn_scene_camera = self._create_scene_button(d1, "Camera Feed", "camera")
        self.btn_scene_screen = self._create_scene_button(d1, "Screen Record", "screen")

        # -----------------------------
        # DOCK 2: SOURCES
        # -----------------------------
        d2 = ctk.CTkFrame(dock_container, fg_color="transparent")
        d2.grid(row=0, column=1, sticky="nsew", padx=6, pady=8)

        ctk.CTkLabel(d2, text="SOURCES", font=ctk.CTkFont(size=10, weight="bold"), text_color=OmniTheme.TEXT_MUTED).pack(anchor="w", padx=8, pady=(0, 6))

        self.source_pc_check = ctk.CTkCheckBox(d2, text="PC Primary Screen", font=ctk.CTkFont(size=11), text_color=OmniTheme.TEXT_MAIN)
        self.source_pc_check.select()
        self.source_pc_check.pack(anchor="w", padx=8, pady=3)

        self.source_cam_check = ctk.CTkCheckBox(d2, text="Phone Camera Sensor", font=ctk.CTkFont(size=11), text_color=OmniTheme.TEXT_MAIN)
        self.source_cam_check.select()
        self.source_cam_check.pack(anchor="w", padx=8, pady=3)

        self.source_uhid_check = ctk.CTkCheckBox(d2, text="UHID Mouse Touch", font=ctk.CTkFont(size=11), text_color=OmniTheme.TEXT_MAIN)
        self.source_uhid_check.pack(anchor="w", padx=8, pady=3)

        # -----------------------------
        # DOCK 3: AUDIO MIXER
        # -----------------------------
        d3 = ctk.CTkFrame(dock_container, fg_color="transparent")
        d3.grid(row=0, column=2, sticky="nsew", padx=6, pady=8)

        ctk.CTkLabel(d3, text="AUDIO MIXER", font=ctk.CTkFont(size=10, weight="bold"), text_color=OmniTheme.TEXT_MUTED).pack(anchor="w", padx=8, pady=(0, 6))

        # Track 1: Phone Microphone
        mic_row = ctk.CTkFrame(d3, fg_color="transparent")
        mic_row.pack(fill="x", padx=8, pady=2)
        ctk.CTkLabel(mic_row, text="Phone Mic", font=ctk.CTkFont(size=11), text_color=OmniTheme.TEXT_MAIN, width=70, anchor="w").pack(side="left")
        self.mic_slider = ctk.CTkSlider(mic_row, from_=0, to=100, number_of_steps=100, height=12, progress_color=OmniTheme.STATUS_CONNECTED)
        self.mic_slider.set(85)
        self.mic_slider.pack(side="left", fill="x", expand=True, padx=8)

        # VU Meter Visual Simulation Bar (Green/Yellow/Red audio level)
        self.mic_vu = ctk.CTkProgressBar(d3, height=4, progress_color=OmniTheme.VU_GREEN, fg_color="#101815")
        self.mic_vu.set(0.65)
        self.mic_vu.pack(fill="x", padx=(86, 16), pady=(0, 6))

        # Track 2: Desktop Playback
        pc_audio_row = ctk.CTkFrame(d3, fg_color="transparent")
        pc_audio_row.pack(fill="x", padx=8, pady=2)
        ctk.CTkLabel(pc_audio_row, text="PC Audio", font=ctk.CTkFont(size=11), text_color=OmniTheme.TEXT_MAIN, width=70, anchor="w").pack(side="left")
        self.pc_audio_slider = ctk.CTkSlider(pc_audio_row, from_=0, to=100, number_of_steps=100, height=12, progress_color=OmniTheme.STATUS_CONNECTED)
        self.pc_audio_slider.set(75)
        self.pc_audio_slider.pack(side="left", fill="x", expand=True, padx=8)

        self.pc_vu = ctk.CTkProgressBar(d3, height=4, progress_color=OmniTheme.VU_GREEN, fg_color="#101815")
        self.pc_vu.set(0.50)
        self.pc_vu.pack(fill="x", padx=(86, 16), pady=(0, 2))

        # -----------------------------
        # DOCK 4: MASTER CONTROLS
        # -----------------------------
        d4 = ctk.CTkFrame(dock_container, fg_color="transparent")
        d4.grid(row=0, column=3, sticky="nsew", padx=12, pady=8)

        ctk.CTkLabel(d4, text="CONTROLS", font=ctk.CTkFont(size=10, weight="bold"), text_color=OmniTheme.TEXT_MUTED).pack(anchor="w", pady=(0, 6))

        # Primary Master Action (Switches between Start and Stop)
        self.master_record_btn = ctk.CTkButton(
            d4,
            text="Start Recording",
            height=34,
            font=ctk.CTkFont(size=12, weight="bold"),
            fg_color=OmniTheme.ACCENT_PRIMARY,
            hover_color=OmniTheme.ACCENT_PRIMARY_HOVER,
            corner_radius=OmniTheme.RADIUS_CONTROL,
            command=self._on_master_record_click
        )
        self.master_record_btn.pack(fill="x", pady=2)

        # Secondary Actions
        self.master_mirror_btn = ctk.CTkButton(
            d4,
            text="Launch Mirror",
            height=28,
            font=ctk.CTkFont(size=11),
            fg_color=OmniTheme.BG_INPUT,
            hover_color=OmniTheme.BG_CARD_HOVER,
            corner_radius=OmniTheme.RADIUS_CONTROL,
            command=self._on_launch_mirror
        )
        self.master_mirror_btn.pack(fill="x", pady=2)

        self.master_recordings_btn = ctk.CTkButton(
            d4,
            text="Recordings",
            height=28,
            font=ctk.CTkFont(size=11),
            fg_color=OmniTheme.BG_INPUT,
            hover_color=OmniTheme.BG_CARD_HOVER,
            corner_radius=OmniTheme.RADIUS_CONTROL,
            command=self._open_recordings_window
        )
        self.master_recordings_btn.pack(fill="x", pady=2)

        self.master_settings_btn = ctk.CTkButton(
            d4,
            text="Settings",
            height=28,
            font=ctk.CTkFont(size=11),
            fg_color=OmniTheme.BG_INPUT,
            hover_color=OmniTheme.BG_CARD_HOVER,
            corner_radius=OmniTheme.RADIUS_CONTROL,
            command=self._open_settings_window
        )
        self.master_settings_btn.pack(fill="x", pady=2)

    def _create_scene_button(self, parent, label: str, scene_id: str, active: bool = False) -> ctk.CTkButton:
        btn = ctk.CTkButton(
            parent,
            text=label,
            height=28,
            font=ctk.CTkFont(size=11),
            anchor="w",
            fg_color=OmniTheme.ACCENT_PRIMARY if active else OmniTheme.BG_INPUT,
            hover_color=OmniTheme.BG_CARD_HOVER,
            corner_radius=OmniTheme.RADIUS_CONTROL,
            command=lambda sid=scene_id: self._select_scene(sid)
        )
        btn.pack(fill="x", padx=8, pady=2)
        return btn

    def _select_scene(self, scene_id: str):
        """Switch active scene and update canvas + inspector."""
        self.active_scene = scene_id
        # Update button highlights
        self.btn_scene_dual.configure(fg_color=OmniTheme.ACCENT_PRIMARY if scene_id == "dual" else OmniTheme.BG_INPUT)
        self.btn_scene_mirror.configure(fg_color=OmniTheme.ACCENT_PRIMARY if scene_id == "mirror" else OmniTheme.BG_INPUT)
        self.btn_scene_camera.configure(fg_color=OmniTheme.ACCENT_PRIMARY if scene_id == "camera" else OmniTheme.BG_INPUT)
        self.btn_scene_screen.configure(fg_color=OmniTheme.ACCENT_PRIMARY if scene_id == "screen" else OmniTheme.BG_INPUT)

        # Update Canvas
        if scene_id == "dual":
            self.canvas_mode_lbl.configure(text="PREVIEW: DUAL RECORDING")
            self.cv_screen_title.configure(text="PC Screen + Mobile Camera")
            self.cv_screen_sub.configure(text="Parallel dual streams @ 60 FPS")
            self.cv_pip_box.place(relx=0.95, rely=0.92, anchor="se")
            self.source_pc_check.select()
            self.source_cam_check.select()
            self.master_record_btn.configure(text="Start Dual Record")
        elif scene_id == "mirror":
            self.canvas_mode_lbl.configure(text="PREVIEW: SCREEN MIRROR")
            self.cv_screen_title.configure(text="Android Display Mirror")
            self.cv_screen_sub.configure(text="Direct3D 11 Interactive Touch @ 60 FPS")
            self.cv_pip_box.place_forget()
            self.source_pc_check.deselect()
            self.source_cam_check.deselect()
            self.master_record_btn.configure(text="Launch Mirror")
        elif scene_id == "camera":
            self.canvas_mode_lbl.configure(text="PREVIEW: CAMERA FEED")
            self.cv_screen_title.configure(text="Raw Camera2 Sensor Viewfinder")
            self.cv_screen_sub.configure(text="Screen off / No camera app opened")
            self.cv_pip_box.place_forget()
            self.source_pc_check.deselect()
            self.source_cam_check.select()
            self.master_record_btn.configure(text="Start Camera Record")
        elif scene_id == "screen":
            self.canvas_mode_lbl.configure(text="PREVIEW: SCREEN RECORD")
            self.cv_screen_title.configure(text="Mobile Display Recorder")
            self.cv_screen_sub.configure(text="Direct-to-PC storage")
            self.cv_pip_box.place_forget()
            self.source_pc_check.deselect()
            self.source_cam_check.deselect()
            self.master_record_btn.configure(text="Start Screen Record")

    # -------------------------------------------------------------------------
    # STATUS FOOTER BAR: Broadcast Telemetry
    # -------------------------------------------------------------------------

    def _build_status_footer(self):
        footer = ctk.CTkFrame(self, fg_color=OmniTheme.BG_ROOT, height=28, corner_radius=0)
        footer.pack(fill="x", side="bottom")

        self.foot_status_lbl = ctk.CTkLabel(
            footer,
            text="STUDIO READY",
            font=ctk.CTkFont(family="Segoe UI", size=10, weight="bold"),
            text_color=OmniTheme.STATUS_CONNECTED
        )
        self.foot_status_lbl.pack(side="left", padx=16)

        self.foot_rec_time = ctk.CTkLabel(
            footer,
            text="REC: 00:00:00",
            font=ctk.CTkFont(family="Consolas", size=10),
            text_color=OmniTheme.TEXT_MUTED
        )
        self.foot_rec_time.pack(side="left", padx=12)

        self.foot_fps_lbl = ctk.CTkLabel(
            footer,
            text="FPS: 60.0",
            font=ctk.CTkFont(family="Consolas", size=10),
            text_color=OmniTheme.TEXT_DIM
        )
        self.foot_fps_lbl.pack(side="left", padx=12)

        self.foot_bitrate_lbl = ctk.CTkLabel(
            footer,
            text="BITRATE: 8.0M",
            font=ctk.CTkFont(family="Consolas", size=10),
            text_color=OmniTheme.TEXT_DIM
        )
        self.foot_bitrate_lbl.pack(side="left", padx=12)

        hotkey_legend = ctk.CTkLabel(
            footer,
            text="Ctrl+Alt+D: Record  ·  Ctrl+Alt+M: Mirror  ·  Ctrl+Alt+C: Camera  ·  Ctrl+Alt+R: Folder",
            font=ctk.CTkFont(family="Segoe UI", size=10),
            text_color=OmniTheme.TEXT_DIM
        )
        hotkey_legend.pack(side="right", padx=16)

    # -------------------------------------------------------------------------
    # Master Action Dispatcher
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

    # -------------------------------------------------------------------------
    # Dual Recording Execution & Tally HUD
    # -------------------------------------------------------------------------

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

        if ok:
            self.master_record_btn.configure(
                text="Stop Recording",
                fg_color=OmniTheme.STATUS_RECORDING,
                hover_color=OmniTheme.STATUS_RECORDING_HOVER
            )
            self.cv_recording_hud.place(relx=0.5, rely=0.08, anchor="n")
            self.foot_status_lbl.configure(text="RECORDING", text_color=OmniTheme.STATUS_RECORDING)
            self.tray.notify("OmniCapture Studio", "Dual recording in progress")
        else:
            self.foot_status_lbl.configure(text=f"ERROR: {msg[:35]}", text_color=OmniTheme.STATUS_WARNING)

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
        self.controller.stop_dual_recording()

    def _on_dual_complete(self, result: Dict[str, Any]):
        def _ui():
            self.master_record_btn.configure(
                text="Start Dual Record",
                fg_color=OmniTheme.ACCENT_PRIMARY,
                hover_color=OmniTheme.ACCENT_PRIMARY_HOVER
            )
            self.cv_recording_hud.place_forget()
            status = result.get("status", "COMPLETE")
            dur = result.get("duration_formatted", "00:00")
            self.foot_status_lbl.configure(text="STUDIO READY", text_color=OmniTheme.STATUS_CONNECTED)
            self.foot_rec_time.configure(text="REC: 00:00:00")
            self.tray.notify("OmniCapture Studio", f"Recording saved ({status}, {dur})")

        self.after(0, _ui)

    # -------------------------------------------------------------------------
    # Single Stream Handlers
    # -------------------------------------------------------------------------

    def _on_launch_mirror(self):
        uhid = "Hardware" in self.prop_input_mode.get()
        screen_off = self.prop_screen_off_var.get()
        self.controller.launch_display_mirror(
            uhid=uhid,
            screen_off=screen_off,
            stay_awake=True,
            on_exit=lambda code: None
        )

    def _on_start_screen_recording(self):
        fmt = "mkv" if "MKV" in self.prop_format.get() else "mp4"
        upload = self.prop_upload_var.get()
        self.controller.record_screen(
            record_format=fmt,
            auto_upload=upload,
            on_complete=lambda path, dur, sz: self._on_single_complete(path, "Screen")
        )

    def _on_start_camera_recording(self):
        facing = "back" if "Back" in self.prop_cam_facing.get() else "front"
        fmt = "mkv" if "MKV" in self.prop_format.get() else "mp4"
        preview = self.prop_preview_var.get()
        upload = self.prop_upload_var.get()
        self.controller.record_camera(
            facing=facing,
            record_format=fmt,
            preview=preview,
            audio_mic=True,
            auto_upload=upload,
            on_complete=lambda path, dur, sz: self._on_single_complete(path, "Camera")
        )

    def _on_single_complete(self, path: Optional[Path], mode_name: str):
        if path:
            self.tray.notify("OmniCapture Studio", f"{mode_name} saved: {path.name}")

    def _on_switch_to_wireless(self):
        def _worker():
            ok, msg = self.controller.switch_to_wireless_adb()
            self.after(0, lambda: self.tray.notify("Wireless ADB", msg))
        threading.Thread(target=_worker, daemon=True).start()

    # -------------------------------------------------------------------------
    # Overlays: Recordings Gallery & Settings Dialogs
    # -------------------------------------------------------------------------

    def _open_recordings_window(self):
        """Open clean modal for recordings management."""
        w = ctk.CTkToplevel(self)
        w.title("Recordings Gallery")
        w.geometry("680x480")
        w.configure(fg_color=OmniTheme.BG_ROOT)

        top = ctk.CTkFrame(w, fg_color="transparent")
        top.pack(fill="x", padx=16, pady=12)

        ctk.CTkLabel(top, text="Recent Recordings", font=ctk.CTkFont(size=14, weight="bold")).pack(side="left")
        ctk.CTkButton(top, text="Open Folder", width=100, height=28, fg_color=OmniTheme.BG_INPUT, command=self.controller.open_recordings_folder).pack(side="right", padx=4)

        scroll = ctk.CTkScrollableFrame(w, fg_color=OmniTheme.BG_DOCK, corner_radius=6)
        scroll.pack(fill="both", expand=True, padx=16, pady=(0, 16))

        items = self.controller.get_recordings_list()
        if not items:
            ctk.CTkLabel(scroll, text="No recordings found in recordings/", text_color=OmniTheme.TEXT_MUTED).pack(pady=40)
            return

        for it in items:
            row = ctk.CTkFrame(scroll, fg_color=OmniTheme.BG_INPUT, corner_radius=4)
            row.pack(fill="x", padx=4, pady=3)

            col = ctk.CTkFrame(row, fg_color="transparent")
            col.pack(side="left", fill="x", expand=True, padx=10, pady=8)

            ctk.CTkLabel(col, text=it["name"], font=ctk.CTkFont(family="Consolas", size=11), text_color=OmniTheme.TEXT_MAIN).pack(anchor="w")
            ctk.CTkLabel(col, text=f"{it['tag']}  ·  {it['mtime_str']}  ·  {it['size_str']}", font=ctk.CTkFont(size=10), text_color=OmniTheme.TEXT_MUTED).pack(anchor="w")

            ctk.CTkButton(row, text="Play", width=55, height=24, font=ctk.CTkFont(size=10), fg_color=OmniTheme.BG_CARD, command=lambda p=it["path"]: self.controller.open_recording_file(p)).pack(side="right", padx=6)
            ctk.CTkButton(row, text="Upload", width=55, height=24, font=ctk.CTkFont(size=10), fg_color=OmniTheme.BG_CARD, command=lambda p=it["path"]: self.controller.uploader.upload_file(str(p))).pack(side="right")

    def _open_settings_window(self):
        """Open clean settings dialog."""
        w = ctk.CTkToplevel(self)
        w.title("Studio Settings")
        w.geometry("520x360")
        w.configure(fg_color=OmniTheme.BG_ROOT)

        box = ctk.CTkFrame(w, fg_color=OmniTheme.BG_DOCK, corner_radius=6)
        box.pack(fill="both", expand=True, padx=16, pady=16)

        ctk.CTkLabel(box, text="System Preferences", font=ctk.CTkFont(size=13, weight="bold")).pack(anchor="w", padx=16, pady=(16, 8))
        ctk.CTkSwitch(box, text="Minimize to system tray on close", variable=self.minimize_to_tray_var, progress_color=OmniTheme.ACCENT_PRIMARY).pack(anchor="w", padx=16, pady=6)
        ctk.CTkSwitch(box, text="Enable global hotkeys (Ctrl+Alt+D, Ctrl+Alt+M)", variable=self.enable_hotkeys_var, progress_color=OmniTheme.ACCENT_PRIMARY).pack(anchor="w", padx=16, pady=6)

        ctk.CTkLabel(box, text="Google Drive Cloud Sync", font=ctk.CTkFont(size=13, weight="bold")).pack(anchor="w", padx=16, pady=(16, 8))
        p = self.controller.uploader.desktop_sync_path or "Auto-detecting virtual drive (G:\\)"
        ctk.CTkLabel(box, text=f"Sync target: {p}", font=ctk.CTkFont(size=11), text_color=OmniTheme.TEXT_MUTED).pack(anchor="w", padx=16, pady=4)

    # -------------------------------------------------------------------------
    # Telemetry & Poller Updates
    # -------------------------------------------------------------------------

    def _initial_refresh(self):
        self.controller.refresh_device_now()

    def _on_device_state_changed(self, state: Dict[str, Any]):
        self.after(0, lambda: self._update_device_ui(state))

    def _update_device_ui(self, state: Dict[str, Any]):
        status = state.get("status")
        model = state.get("model", "No Device")
        conn_str = "Wi-Fi" if state.get("is_wireless") else "USB"

        if status == "CONNECTED":
            batt = state.get("battery", {})
            lvl = batt.get("level", "")
            batt_str = f" · {lvl}" if lvl and lvl != "N/A" else ""
            self.top_device_lbl.configure(
                text=f"● {model} ({conn_str}){batt_str}",
                text_color=OmniTheme.STATUS_CONNECTED
            )
        elif status == "UNAUTHORIZED":
            self.top_device_lbl.configure(
                text="Unauthorized: unlock phone and allow USB debugging",
                text_color=OmniTheme.STATUS_WARNING
            )
        elif status == "OFFLINE":
            self.top_device_lbl.configure(
                text="Device offline: reconnect cable",
                text_color=OmniTheme.STATUS_WARNING
            )
        else:
            self.top_device_lbl.configure(
                text="No device connected (plug in phone & enable USB debugging)",
                text_color=OmniTheme.TEXT_MUTED
            )

    def _on_manual_refresh(self):
        self.controller.refresh_device_now()

    def _on_release_lock(self):
        ok, msg = self.controller.release_camera_lock()
        self.tray.notify("Camera Lock", msg)

    # -------------------------------------------------------------------------
    # Hotkeys & Tray
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

    def _on_window_close(self):
        if self.minimize_to_tray_var.get():
            self.withdraw()
            self.tray.notify(
                "OmniCapture Studio",
                "Studio running in background. Press Ctrl+Alt+D to record or click the tray icon."
            )
        else:
            self._on_app_exit()

    def _on_app_exit(self):
        if self.controller.is_dual_recording():
            self.controller.stop_dual_recording()
        self.controller.stop_device_poller()
        self.hotkeys.stop()
        self.tray.stop()
        self.destroy()
        sys.exit(0)
