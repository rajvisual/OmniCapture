import os
import sys
import time
import subprocess
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
    OmniCapture Modern Windows 11 Dark Mode Desktop Dashboard.
    """

    def __init__(self, config: Dict[str, Any]):
        super().__init__()

        self.config = config
        self.controller = GUIController(config)

        # Window styling & geometry
        OmniTheme.apply_appearance()
        self.title("OmniCapture — High-Performance Android & PC Desktop Capture Suite")
        self.geometry("1120x760")
        self.minsize(980, 640)
        self.configure(fg_color=OmniTheme.BG_ROOT)

        # Set window icon
        self._set_app_icon()

        # System tray and hotkey managers
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

        # Build UI layout
        self._build_header()
        self._build_tabs()
        self._build_footer()

        # Wire up close behavior & device polling
        self.protocol("WM_DELETE_WINDOW", self._on_window_close)
        self.controller.register_device_listener(self._on_device_state_changed)
        self.controller.start_device_poller(interval_sec=2.5)

        # Start tray and hotkeys
        self.tray.start()
        if self.enable_hotkeys_var.get():
            self.hotkeys.start()

        # Initial device refresh
        self.after(300, self._initial_refresh)

    def _set_app_icon(self):
        """Set native window icon."""
        ico_path = resolve_resource("assets/logo/omnicapture.ico")
        if ico_path.is_file():
            try:
                self.iconbitmap(str(ico_path))
            except Exception:
                pass

    # -------------------------------------------------------------------------
    # Layout Builders
    # -------------------------------------------------------------------------

    def _build_header(self):
        """Top Header: Branding, Live Device Pill, Battery & Action Buttons."""
        header_frame = ctk.CTkFrame(
            self,
            fg_color=OmniTheme.BG_CARD,
            corner_radius=12,
            border_width=1,
            border_color=OmniTheme.BG_CARD_BORDER
        )
        header_frame.pack(fill="x", padx=16, pady=(12, 8))

        # Brand column
        brand_frame = ctk.CTkFrame(header_frame, fg_color="transparent")
        brand_frame.pack(side="left", padx=16, pady=10)

        # Brand logo
        logo_path = resolve_resource("assets/logo/omnicapture-icon.png")
        if logo_path.is_file():
            try:
                pil_img = Image.open(str(logo_path)).resize((34, 34), Image.Resampling.LANCZOS)
                self.logo_ctk = ctk.CTkImage(light_image=pil_img, dark_image=pil_img, size=(34, 34))
                logo_lbl = ctk.CTkLabel(brand_frame, image=self.logo_ctk, text="")
                logo_lbl.pack(side="left", padx=(0, 10))
            except Exception:
                pass

        titles_col = ctk.CTkFrame(brand_frame, fg_color="transparent")
        titles_col.pack(side="left")

        title_row = ctk.CTkFrame(titles_col, fg_color="transparent")
        title_row.pack(anchor="w")

        title_lbl = ctk.CTkLabel(
            title_row,
            text="OmniCapture",
            font=ctk.CTkFont(family="Segoe UI", size=20, weight="bold"),
            text_color=OmniTheme.TEXT_MAIN
        )
        title_lbl.pack(side="left", padx=(0, 8))

        badge_lbl = ctk.CTkLabel(
            title_row,
            text="v1.2.0-production",
            font=ctk.CTkFont(family="Segoe UI", size=10, weight="bold"),
            fg_color=OmniTheme.BG_CARD_BORDER,
            text_color=OmniTheme.ACCENT_CYAN,
            corner_radius=6,
            padx=6,
            pady=2
        )
        badge_lbl.pack(side="left")

        sub_lbl = ctk.CTkLabel(
            titles_col,
            text="High-Performance Android & PC Desktop Capture Suite",
            font=ctk.CTkFont(family="Segoe UI", size=11),
            text_color=OmniTheme.TEXT_MUTED
        )
        sub_lbl.pack(anchor="w")

        # Right status & quick actions column
        status_frame = ctk.CTkFrame(header_frame, fg_color="transparent")
        status_frame.pack(side="right", padx=16, pady=10)

        # Connection badge pill
        self.device_pill = ctk.CTkLabel(
            status_frame,
            text="○ Searching for device...",
            font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"),
            text_color=OmniTheme.STATUS_DISCONNECTED,
            fg_color=OmniTheme.BG_INPUT,
            corner_radius=16,
            padx=14,
            pady=6
        )
        self.device_pill.pack(side="left", padx=6)

        # Battery pill
        self.battery_pill = ctk.CTkLabel(
            status_frame,
            text="🔋 --%",
            font=ctk.CTkFont(family="Segoe UI", size=12),
            text_color=OmniTheme.TEXT_MUTED,
            fg_color=OmniTheme.BG_INPUT,
            corner_radius=16,
            padx=10,
            pady=6
        )
        self.battery_pill.pack(side="left", padx=6)

        # Quick Refresh Button
        self.refresh_btn = ctk.CTkButton(
            status_frame,
            text="🔄 Refresh",
            width=80,
            height=32,
            font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"),
            fg_color=OmniTheme.BG_INPUT,
            hover_color=OmniTheme.BG_CARD_HOVER,
            text_color=OmniTheme.TEXT_MAIN,
            command=self._on_manual_refresh
        )
        self.refresh_btn.pack(side="left", padx=4)

        # Release Camera Lock Button
        self.lock_btn = ctk.CTkButton(
            status_frame,
            text="🔓 Release Camera Lock",
            width=140,
            height=32,
            font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"),
            fg_color=OmniTheme.BG_INPUT,
            hover_color=OmniTheme.BG_CARD_HOVER,
            text_color=OmniTheme.ACCENT_AMBER,
            command=self._on_release_lock
        )
        self.lock_btn.pack(side="left", padx=4)

    def _build_tabs(self):
        """Build the Tabview containing the 6 application cards/modes."""
        self.tabs = ctk.CTkTabview(
            self,
            fg_color=OmniTheme.BG_ROOT,
            segmented_button_fg_color=OmniTheme.BG_CARD,
            segmented_button_selected_color=OmniTheme.ACCENT_CYAN,
            segmented_button_selected_hover_color=OmniTheme.ACCENT_CYAN_HOVER,
            segmented_button_unselected_color=OmniTheme.BG_CARD,
            segmented_button_unselected_hover_color=OmniTheme.BG_CARD_HOVER,
            text_color=OmniTheme.TEXT_MAIN,
            corner_radius=12
        )
        self.tabs.pack(fill="both", expand=True, padx=16, pady=(0, 8))

        # Add tabs
        self.tab_dual = self.tabs.add("🎬 Dual Recording (Hero)")
        self.tab_mirror = self.tabs.add("📱 Display Mirror & Control")
        self.tab_camera = self.tabs.add("📷 Stealth Camera")
        self.tab_wireless = self.tabs.add("📶 Wireless & Diagnostics")
        self.tab_gallery = self.tabs.add("📁 Recordings Gallery")
        self.tab_settings = self.tabs.add("⚙️ Settings & Cloud")

        # Build each tab's contents
        self._build_dual_recording_tab()
        self._build_mirror_tab()
        self._build_camera_tab()
        self._build_wireless_tab()
        self._build_gallery_tab()
        self._build_settings_tab()

    # -------------------------------------------------------------------------
    # TAB 1: Dual Simultaneous Recording (Creator Hero Mode)
    # -------------------------------------------------------------------------

    def _build_dual_recording_tab(self):
        tab = self.tab_dual

        # Main Hero Card
        hero_card = ctk.CTkFrame(
            tab,
            fg_color=OmniTheme.BG_CARD,
            corner_radius=12,
            border_width=2,
            border_color=OmniTheme.ACCENT_PURPLE
        )
        hero_card.pack(fill="x", padx=10, pady=10)

        # Hero Header Banner
        banner_row = ctk.CTkFrame(hero_card, fg_color="transparent")
        banner_row.pack(fill="x", padx=18, pady=(16, 8))

        hero_icon_lbl = ctk.CTkLabel(
            banner_row,
            text="🎬",
            font=ctk.CTkFont(size=26)
        )
        hero_icon_lbl.pack(side="left", padx=(0, 10))

        hero_titles = ctk.CTkFrame(banner_row, fg_color="transparent")
        hero_titles.pack(side="left")

        hero_title = ctk.CTkLabel(
            hero_titles,
            text="Dual Simultaneous Recording (PC Desktop + Mobile Camera)",
            font=ctk.CTkFont(family="Segoe UI", size=18, weight="bold"),
            text_color=OmniTheme.TEXT_MAIN
        )
        hero_title.pack(anchor="w")

        hero_desc = ctk.CTkLabel(
            hero_titles,
            text="Concurrently captures your PC desktop screen (via FFmpeg) and your smartphone camera (via scrcpy) into 2 separate files.",
            font=ctk.CTkFont(family="Segoe UI", size=12),
            text_color=OmniTheme.TEXT_MUTED
        )
        hero_desc.pack(anchor="w")

        # Configuration Grid
        cfg_frame = ctk.CTkFrame(
            hero_card,
            fg_color=OmniTheme.BG_INPUT,
            corner_radius=10,
            border_width=1,
            border_color=OmniTheme.BG_CARD_BORDER
        )
        cfg_frame.pack(fill="x", padx=18, pady=10)

        # Row 1: Camera Sensor, PC FPS, Cam FPS, Format
        row1 = ctk.CTkFrame(cfg_frame, fg_color="transparent")
        row1.pack(fill="x", padx=14, pady=10)

        # Mobile camera facing
        f_lbl = ctk.CTkLabel(row1, text="Mobile Camera:", font=ctk.CTkFont(size=12, weight="bold"), text_color=OmniTheme.TEXT_BODY)
        f_lbl.pack(side="left", padx=(0, 6))
        self.dual_facing_seg = ctk.CTkSegmentedButton(
            row1,
            values=["Back (Main Sensor)", "Front (Selfie)"],
            selected_color=OmniTheme.ACCENT_CYAN,
            selected_hover_color=OmniTheme.ACCENT_CYAN_HOVER
        )
        self.dual_facing_seg.set("Back (Main Sensor)")
        self.dual_facing_seg.pack(side="left", padx=(0, 20))

        # PC FPS
        pc_fps_lbl = ctk.CTkLabel(row1, text="PC Screen FPS:", font=ctk.CTkFont(size=12, weight="bold"), text_color=OmniTheme.TEXT_BODY)
        pc_fps_lbl.pack(side="left", padx=(0, 6))
        self.dual_pc_fps_seg = ctk.CTkSegmentedButton(
            row1,
            values=["30 FPS", "60 FPS"],
            selected_color=OmniTheme.ACCENT_CYAN
        )
        self.dual_pc_fps_seg.set("30 FPS")
        self.dual_pc_fps_seg.pack(side="left", padx=(0, 20))

        # Camera FPS
        cam_fps_lbl = ctk.CTkLabel(row1, text="Camera FPS:", font=ctk.CTkFont(size=12, weight="bold"), text_color=OmniTheme.TEXT_BODY)
        cam_fps_lbl.pack(side="left", padx=(0, 6))
        self.dual_cam_fps_seg = ctk.CTkSegmentedButton(
            row1,
            values=["30 FPS", "60 FPS"],
            selected_color=OmniTheme.ACCENT_CYAN
        )
        self.dual_cam_fps_seg.set("30 FPS")
        self.dual_cam_fps_seg.pack(side="left", padx=(0, 20))

        # Format
        fmt_lbl = ctk.CTkLabel(row1, text="Format:", font=ctk.CTkFont(size=12, weight="bold"), text_color=OmniTheme.TEXT_BODY)
        fmt_lbl.pack(side="left", padx=(0, 6))
        self.dual_fmt_seg = ctk.CTkSegmentedButton(
            row1,
            values=["MP4", "MKV"],
            selected_color=OmniTheme.ACCENT_CYAN
        )
        self.dual_fmt_seg.set("MP4")
        self.dual_fmt_seg.pack(side="left")

        # Row 2: Toggles
        row2 = ctk.CTkFrame(cfg_frame, fg_color="transparent")
        row2.pack(fill="x", padx=14, pady=(0, 10))

        self.dual_preview_var = ctk.BooleanVar(value=True)
        self.dual_preview_switch = ctk.CTkSwitch(
            row2,
            text="Show live mobile camera preview window on PC",
            variable=self.dual_preview_var,
            progress_color=OmniTheme.ACCENT_CYAN
        )
        self.dual_preview_switch.pack(side="left", padx=(0, 24))

        self.dual_upload_var = ctk.BooleanVar(value=False)
        self.dual_upload_switch = ctk.CTkSwitch(
            row2,
            text="Auto-upload both recordings to Google Drive when finished",
            variable=self.dual_upload_var,
            progress_color=OmniTheme.ACCENT_GREEN
        )
        self.dual_upload_switch.pack(side="left")

        # Action Container (Switches between Idle Start & Active Live Monitor)
        self.dual_action_frame = ctk.CTkFrame(hero_card, fg_color="transparent")
        self.dual_action_frame.pack(fill="x", padx=18, pady=(4, 16))

        # Start Button (Idle)
        self.dual_start_btn = ctk.CTkButton(
            self.dual_action_frame,
            text="🔴  START DUAL SIMULTANEOUS RECORDING",
            height=48,
            font=ctk.CTkFont(family="Segoe UI", size=14, weight="bold"),
            fg_color=OmniTheme.ACCENT_RED,
            hover_color=OmniTheme.ACCENT_RED_HOVER,
            command=self._on_start_dual_recording
        )
        self.dual_start_btn.pack(fill="x")

        # Live Recording Card (Shown during recording)
        self.dual_live_card = ctk.CTkFrame(
            hero_card,
            fg_color="#24141E",
            corner_radius=10,
            border_width=1,
            border_color=OmniTheme.ACCENT_RED
        )

        live_row = ctk.CTkFrame(self.dual_live_card, fg_color="transparent")
        live_row.pack(fill="x", padx=16, pady=12)

        self.dual_timer_lbl = ctk.CTkLabel(
            live_row,
            text="⏱  00:00:00",
            font=ctk.CTkFont(family="Consolas", size=24, weight="bold"),
            text_color=OmniTheme.ACCENT_RED
        )
        self.dual_timer_lbl.pack(side="left", padx=(0, 24))

        self.dual_stream_stats_lbl = ctk.CTkLabel(
            live_row,
            text="Stream 1 [PC]: 0.00 MB  |  Stream 2 [Camera]: 0.00 MB",
            font=ctk.CTkFont(family="Segoe UI", size=13),
            text_color=OmniTheme.TEXT_BODY
        )
        self.dual_stream_stats_lbl.pack(side="left")

        self.dual_stop_btn = ctk.CTkButton(
            live_row,
            text="⏹  STOP & FINALIZE",
            width=160,
            height=38,
            font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"),
            fg_color=OmniTheme.ACCENT_RED,
            hover_color=OmniTheme.ACCENT_RED_HOVER,
            command=self._on_stop_dual_recording
        )
        self.dual_stop_btn.pack(side="right")

        # Status / Feedback Card
        self.dual_feedback_frame = ctk.CTkFrame(
            tab,
            fg_color=OmniTheme.BG_CARD,
            corner_radius=10,
            border_width=1,
            border_color=OmniTheme.BG_CARD_BORDER
        )
        self.dual_feedback_frame.pack(fill="both", expand=True, padx=10, pady=(0, 10))

        feedback_header = ctk.CTkLabel(
            self.dual_feedback_frame,
            text="Dual Recording Status & Output Logs",
            font=ctk.CTkFont(family="Segoe UI", size=13, weight="bold"),
            text_color=OmniTheme.TEXT_MUTED
        )
        feedback_header.pack(anchor="w", padx=16, pady=(10, 4))

        self.dual_log_box = ctk.CTkTextbox(
            self.dual_feedback_frame,
            fg_color=OmniTheme.BG_INPUT,
            text_color=OmniTheme.TEXT_BODY,
            font=ctk.CTkFont(family="Consolas", size=11),
            corner_radius=8
        )
        self.dual_log_box.pack(fill="both", expand=True, padx=16, pady=(0, 12))
        self.dual_log_box.insert("1.0", "Ready to start Dual Simultaneous Recording.\nPress 'START DUAL SIMULTANEOUS RECORDING' or hit global hotkey [Ctrl + Alt + D].\n")

    # -------------------------------------------------------------------------
    # TAB 2: Display Mirror & Control
    # -------------------------------------------------------------------------

    def _build_mirror_tab(self):
        tab = self.tab_mirror

        grid_frame = ctk.CTkFrame(tab, fg_color="transparent")
        grid_frame.pack(fill="both", expand=True, padx=10, pady=10)
        grid_frame.columnconfigure(0, weight=1)
        grid_frame.columnconfigure(1, weight=1)
        grid_frame.rowconfigure(0, weight=1)

        # Card 1: Interactive Display Controller
        card1 = ctk.CTkFrame(grid_frame, fg_color=OmniTheme.BG_CARD, corner_radius=12, border_width=1, border_color=OmniTheme.BG_CARD_BORDER)
        card1.grid(row=0, column=0, sticky="nsew", padx=(0, 6))

        c1_head = ctk.CTkLabel(card1, text="📱  Display Mirror & PC Controller", font=ctk.CTkFont(size=16, weight="bold"), text_color=OmniTheme.TEXT_MAIN)
        c1_head.pack(anchor="w", padx=16, pady=(16, 4))
        c1_desc = ctk.CTkLabel(card1, text="Mirror phone screen with full PC mouse & keyboard control at 60 FPS.", font=ctk.CTkFont(size=11), text_color=OmniTheme.TEXT_MUTED)
        c1_desc.pack(anchor="w", padx=16, pady=(0, 14))

        # Controls
        ctrl_box = ctk.CTkFrame(card1, fg_color=OmniTheme.BG_INPUT, corner_radius=10)
        ctrl_box.pack(fill="x", padx=16, pady=6)

        ctk.CTkLabel(ctrl_box, text="Touch Input Mode:", font=ctk.CTkFont(size=12, weight="bold")).pack(anchor="w", padx=12, pady=(10, 4))
        self.mirror_mode_seg = ctk.CTkSegmentedButton(
            ctrl_box,
            values=["Standard Touch", "Hardware Mouse (UHID POCO Bypass)"],
            selected_color=OmniTheme.ACCENT_CYAN
        )
        self.mirror_mode_seg.set("Standard Touch")
        self.mirror_mode_seg.pack(fill="x", padx=12, pady=(0, 10))

        self.mirror_screen_off_var = ctk.BooleanVar(value=False)
        ctk.CTkSwitch(ctrl_box, text="Turn phone screen OFF to save heat & battery", variable=self.mirror_screen_off_var, progress_color=OmniTheme.ACCENT_CYAN).pack(anchor="w", padx=12, pady=6)

        self.mirror_awake_var = ctk.BooleanVar(value=True)
        ctk.CTkSwitch(ctrl_box, text="Keep phone display awake while connected", variable=self.mirror_awake_var, progress_color=OmniTheme.ACCENT_CYAN).pack(anchor="w", padx=12, pady=(6, 12))

        # Mirror Launch Button
        self.mirror_launch_btn = ctk.CTkButton(
            card1,
            text="📱  LAUNCH DISPLAY CONTROLLER",
            height=44,
            font=ctk.CTkFont(size=13, weight="bold"),
            fg_color=OmniTheme.ACCENT_CYAN,
            hover_color=OmniTheme.ACCENT_CYAN_HOVER,
            text_color="#000000",
            command=self._on_launch_mirror
        )
        self.mirror_launch_btn.pack(fill="x", padx=16, pady=(16, 16))

        # Card 2: Record Screen -> PC
        card2 = ctk.CTkFrame(grid_frame, fg_color=OmniTheme.BG_CARD, corner_radius=12, border_width=1, border_color=OmniTheme.BG_CARD_BORDER)
        card2.grid(row=0, column=1, sticky="nsew", padx=(6, 0))

        c2_head = ctk.CTkLabel(card2, text="🔴  Direct Mobile Screen Recording", font=ctk.CTkFont(size=16, weight="bold"), text_color=OmniTheme.TEXT_MAIN)
        c2_head.pack(anchor="w", padx=16, pady=(16, 4))
        c2_desc = ctk.CTkLabel(card2, text="Stream and record mobile gameplay or apps directly to high-bitrate video file.", font=ctk.CTkFont(size=11), text_color=OmniTheme.TEXT_MUTED)
        c2_desc.pack(anchor="w", padx=16, pady=(0, 14))

        rec_box = ctk.CTkFrame(card2, fg_color=OmniTheme.BG_INPUT, corner_radius=10)
        rec_box.pack(fill="x", padx=16, pady=6)

        ctk.CTkLabel(rec_box, text="Format:", font=ctk.CTkFont(size=12, weight="bold")).pack(anchor="w", padx=12, pady=(10, 4))
        self.screen_rec_fmt_seg = ctk.CTkSegmentedButton(
            rec_box,
            values=["MP4 (Standard)", "MKV (Crash-Safe)"],
            selected_color=OmniTheme.ACCENT_CYAN
        )
        self.screen_rec_fmt_seg.set("MP4 (Standard)")
        self.screen_rec_fmt_seg.pack(fill="x", padx=12, pady=(0, 10))

        self.screen_rec_upload_var = ctk.BooleanVar(value=False)
        ctk.CTkSwitch(rec_box, text="Auto-upload to Google Drive when finished", variable=self.screen_rec_upload_var, progress_color=OmniTheme.ACCENT_GREEN).pack(anchor="w", padx=12, pady=(6, 12))

        self.screen_rec_btn = ctk.CTkButton(
            card2,
            text="🔴  START SCREEN RECORDING",
            height=44,
            font=ctk.CTkFont(size=13, weight="bold"),
            fg_color=OmniTheme.ACCENT_RED,
            hover_color=OmniTheme.ACCENT_RED_HOVER,
            command=self._on_start_screen_recording
        )
        self.screen_rec_btn.pack(fill="x", padx=16, pady=(16, 16))

    # -------------------------------------------------------------------------
    # TAB 3: Stealth Camera Stream & Recording
    # -------------------------------------------------------------------------

    def _build_camera_tab(self):
        tab = self.tab_camera

        grid_frame = ctk.CTkFrame(tab, fg_color="transparent")
        grid_frame.pack(fill="both", expand=True, padx=10, pady=10)
        grid_frame.columnconfigure(0, weight=1)
        grid_frame.columnconfigure(1, weight=1)
        grid_frame.rowconfigure(0, weight=1)

        # Card 1: Stealth Stream Viewfinder
        card1 = ctk.CTkFrame(grid_frame, fg_color=OmniTheme.BG_CARD, corner_radius=12, border_width=1, border_color=OmniTheme.BG_CARD_BORDER)
        card1.grid(row=0, column=0, sticky="nsew", padx=(0, 6))

        c1_head = ctk.CTkLabel(card1, text="📷  Stealth Camera Viewfinder", font=ctk.CTkFont(size=16, weight="bold"), text_color=OmniTheme.TEXT_MAIN)
        c1_head.pack(anchor="w", padx=16, pady=(16, 4))
        c1_desc = ctk.CTkLabel(card1, text="Direct raw sensor stream to PC window. Phone camera app NEVER opens.", font=ctk.CTkFont(size=11), text_color=OmniTheme.TEXT_MUTED)
        c1_desc.pack(anchor="w", padx=16, pady=(0, 14))

        box1 = ctk.CTkFrame(card1, fg_color=OmniTheme.BG_INPUT, corner_radius=10)
        box1.pack(fill="x", padx=16, pady=6)

        ctk.CTkLabel(box1, text="Camera Sensor:", font=ctk.CTkFont(size=12, weight="bold")).pack(anchor="w", padx=12, pady=(10, 4))
        self.cam_stream_facing_seg = ctk.CTkSegmentedButton(
            box1,
            values=["Back (Standard)", "Front (Selfie)"],
            selected_color=OmniTheme.ACCENT_CYAN
        )
        self.cam_stream_facing_seg.set("Back (Standard)")
        self.cam_stream_facing_seg.pack(fill="x", padx=12, pady=(0, 10))

        self.cam_stream_mic_var = ctk.BooleanVar(value=True)
        ctk.CTkSwitch(box1, text="Capture phone microphone audio", variable=self.cam_stream_mic_var, progress_color=OmniTheme.ACCENT_CYAN).pack(anchor="w", padx=12, pady=(6, 12))

        self.cam_stream_btn = ctk.CTkButton(
            card1,
            text="📷  LAUNCH STEALTH VIEWFINDER",
            height=44,
            font=ctk.CTkFont(size=13, weight="bold"),
            fg_color=OmniTheme.ACCENT_CYAN,
            hover_color=OmniTheme.ACCENT_CYAN_HOVER,
            text_color="#000000",
            command=self._on_launch_camera_stream
        )
        self.cam_stream_btn.pack(fill="x", padx=16, pady=(16, 16))

        # Card 2: Record Camera -> PC
        card2 = ctk.CTkFrame(grid_frame, fg_color=OmniTheme.BG_CARD, corner_radius=12, border_width=1, border_color=OmniTheme.BG_CARD_BORDER)
        card2.grid(row=0, column=1, sticky="nsew", padx=(6, 0))

        c2_head = ctk.CTkLabel(card2, text="🎥  Record Mobile Camera -> PC File", font=ctk.CTkFont(size=16, weight="bold"), text_color=OmniTheme.TEXT_MAIN)
        c2_head.pack(anchor="w", padx=16, pady=(16, 4))
        c2_desc = ctk.CTkLabel(card2, text="Records camera stream directly into local MP4/MKV with audio.", font=ctk.CTkFont(size=11), text_color=OmniTheme.TEXT_MUTED)
        c2_desc.pack(anchor="w", padx=16, pady=(0, 14))

        box2 = ctk.CTkFrame(card2, fg_color=OmniTheme.BG_INPUT, corner_radius=10)
        box2.pack(fill="x", padx=16, pady=6)

        ctk.CTkLabel(box2, text="Camera Sensor:", font=ctk.CTkFont(size=12, weight="bold")).pack(anchor="w", padx=12, pady=(10, 4))
        self.cam_rec_facing_seg = ctk.CTkSegmentedButton(
            box2,
            values=["Back (Standard)", "Front (Selfie)"],
            selected_color=OmniTheme.ACCENT_CYAN
        )
        self.cam_rec_facing_seg.set("Back (Standard)")
        self.cam_rec_facing_seg.pack(fill="x", padx=12, pady=(0, 10))

        ctk.CTkLabel(box2, text="Container Format:", font=ctk.CTkFont(size=12, weight="bold")).pack(anchor="w", padx=12, pady=(6, 4))
        self.cam_rec_fmt_seg = ctk.CTkSegmentedButton(
            box2,
            values=["MP4", "MKV"],
            selected_color=OmniTheme.ACCENT_CYAN
        )
        self.cam_rec_fmt_seg.set("MP4")
        self.cam_rec_fmt_seg.pack(fill="x", padx=12, pady=(0, 10))

        self.cam_rec_preview_var = ctk.BooleanVar(value=True)
        ctk.CTkSwitch(box2, text="Show live preview window on PC", variable=self.cam_rec_preview_var, progress_color=OmniTheme.ACCENT_CYAN).pack(anchor="w", padx=12, pady=6)

        self.cam_rec_upload_var = ctk.BooleanVar(value=False)
        ctk.CTkSwitch(box2, text="Auto-upload to Google Drive", variable=self.cam_rec_upload_var, progress_color=OmniTheme.ACCENT_GREEN).pack(anchor="w", padx=12, pady=(6, 12))

        self.cam_rec_btn = ctk.CTkButton(
            card2,
            text="🎥  START CAMERA RECORDING",
            height=44,
            font=ctk.CTkFont(size=13, weight="bold"),
            fg_color=OmniTheme.ACCENT_RED,
            hover_color=OmniTheme.ACCENT_RED_HOVER,
            command=self._on_start_camera_recording
        )
        self.cam_rec_btn.pack(fill="x", padx=16, pady=(16, 16))

    # -------------------------------------------------------------------------
    # TAB 4: Wireless ADB & Diagnostics
    # -------------------------------------------------------------------------

    def _build_wireless_tab(self):
        tab = self.tab_wireless

        grid_frame = ctk.CTkFrame(tab, fg_color="transparent")
        grid_frame.pack(fill="both", expand=True, padx=10, pady=10)
        grid_frame.columnconfigure(0, weight=1)
        grid_frame.columnconfigure(1, weight=1)
        grid_frame.rowconfigure(0, weight=1)

        # Left Card: Wireless ADB
        card1 = ctk.CTkFrame(grid_frame, fg_color=OmniTheme.BG_CARD, corner_radius=12, border_width=1, border_color=OmniTheme.BG_CARD_BORDER)
        card1.grid(row=0, column=0, sticky="nsew", padx=(0, 6))

        c1_head = ctk.CTkLabel(card1, text="📶  Wireless ADB (Wi-Fi Capture)", font=ctk.CTkFont(size=16, weight="bold"), text_color=OmniTheme.TEXT_MAIN)
        c1_head.pack(anchor="w", padx=16, pady=(16, 4))
        c1_desc = ctk.CTkLabel(card1, text="Switch connected phone to Wi-Fi TCP/IP mode so you can unplug the USB cable.", font=ctk.CTkFont(size=11), text_color=OmniTheme.TEXT_MUTED)
        c1_desc.pack(anchor="w", padx=16, pady=(0, 14))

        w_box = ctk.CTkFrame(card1, fg_color=OmniTheme.BG_INPUT, corner_radius=10)
        w_box.pack(fill="x", padx=16, pady=6)

        self.wifi_ip_lbl = ctk.CTkLabel(w_box, text="Phone Wi-Fi IP:  Scanning...", font=ctk.CTkFont(family="Segoe UI", size=13))
        self.wifi_ip_lbl.pack(anchor="w", padx=12, pady=(12, 6))

        w_instr = ctk.CTkLabel(
            w_box,
            text="HOW IT WORKS:\n1. Ensure phone & PC are on the SAME Wi-Fi network.\n2. Click the button below to enable TCP/IP port 5555.\n3. Unplug USB cable and enjoy wireless streaming!",
            font=ctk.CTkFont(size=11),
            text_color=OmniTheme.TEXT_MUTED,
            justify="left"
        )
        w_instr.pack(anchor="w", padx=12, pady=(0, 12))

        self.switch_wifi_btn = ctk.CTkButton(
            card1,
            text="📶  SWITCH TO WIRELESS ADB",
            height=44,
            font=ctk.CTkFont(size=13, weight="bold"),
            fg_color=OmniTheme.ACCENT_CYAN,
            hover_color=OmniTheme.ACCENT_CYAN_HOVER,
            text_color="#000000",
            command=self._on_switch_to_wireless
        )
        self.switch_wifi_btn.pack(fill="x", padx=16, pady=(16, 16))

        # Right Card: Hardware & Camera Diagnostics
        card2 = ctk.CTkFrame(grid_frame, fg_color=OmniTheme.BG_CARD, corner_radius=12, border_width=1, border_color=OmniTheme.BG_CARD_BORDER)
        card2.grid(row=0, column=1, sticky="nsew", padx=(6, 0))

        c2_head = ctk.CTkLabel(card2, text="🔍  Hardware & Camera Diagnostics", font=ctk.CTkFont(size=16, weight="bold"), text_color=OmniTheme.TEXT_MAIN)
        c2_head.pack(anchor="w", padx=16, pady=(16, 4))

        self.diag_box = ctk.CTkTextbox(
            card2,
            fg_color=OmniTheme.BG_INPUT,
            font=ctk.CTkFont(family="Consolas", size=10),
            corner_radius=8
        )
        self.diag_box.pack(fill="both", expand=True, padx=16, pady=(0, 10))

        self.diag_btn = ctk.CTkButton(
            card2,
            text="🔍  RUN FULL HARDWARE INSPECTION",
            height=40,
            font=ctk.CTkFont(size=12, weight="bold"),
            fg_color=OmniTheme.BG_INPUT,
            hover_color=OmniTheme.BG_CARD_HOVER,
            command=self._on_run_diagnostics
        )
        self.diag_btn.pack(fill="x", padx=16, pady=(0, 16))

    # -------------------------------------------------------------------------
    # TAB 5: Recordings Gallery
    # -------------------------------------------------------------------------

    def _build_gallery_tab(self):
        tab = self.tab_gallery

        top_row = ctk.CTkFrame(tab, fg_color="transparent")
        top_row.pack(fill="x", padx=10, pady=(10, 6))

        gal_lbl = ctk.CTkLabel(top_row, text="📁  Recent Video Recordings", font=ctk.CTkFont(size=16, weight="bold"), text_color=OmniTheme.TEXT_MAIN)
        gal_lbl.pack(side="left")

        open_folder_btn = ctk.CTkButton(
            top_row,
            text="📂  Open Folder in Explorer",
            width=180,
            font=ctk.CTkFont(size=12, weight="bold"),
            fg_color=OmniTheme.BG_CARD,
            hover_color=OmniTheme.BG_CARD_HOVER,
            command=self.controller.open_recordings_folder
        )
        open_folder_btn.pack(side="right", padx=6)

        refresh_gal_btn = ctk.CTkButton(
            top_row,
            text="🔄  Refresh Gallery",
            width=130,
            font=ctk.CTkFont(size=12, weight="bold"),
            fg_color=OmniTheme.BG_CARD,
            hover_color=OmniTheme.BG_CARD_HOVER,
            command=self._refresh_gallery_list
        )
        refresh_gal_btn.pack(side="right", padx=6)

        # Scrollable gallery container
        self.gallery_scroll = ctk.CTkScrollableFrame(
            tab,
            fg_color=OmniTheme.BG_CARD,
            corner_radius=12,
            border_width=1,
            border_color=OmniTheme.BG_CARD_BORDER
        )
        self.gallery_scroll.pack(fill="both", expand=True, padx=10, pady=(0, 10))

    def _refresh_gallery_list(self):
        """Re-populate the gallery scrollable container with existing video files."""
        # Clear existing children
        for widget in self.gallery_scroll.winfo_children():
            widget.destroy()

        items = self.controller.get_recordings_list()
        if not items:
            empty_lbl = ctk.CTkLabel(
                self.gallery_scroll,
                text="No recordings found in recordings/ yet.\nStart a recording from the Dual Recording, Mirror, or Camera tabs!",
                font=ctk.CTkFont(size=13),
                text_color=OmniTheme.TEXT_MUTED
            )
            empty_lbl.pack(pady=40)
            return

        for item in items:
            row = ctk.CTkFrame(self.gallery_scroll, fg_color=OmniTheme.BG_INPUT, corner_radius=8)
            row.pack(fill="x", padx=8, pady=4)

            # Icon tag
            tag_color = OmniTheme.ACCENT_CYAN if item["tag"] == "PC Screen" else (OmniTheme.ACCENT_PURPLE if item["tag"] == "Mobile Camera" else OmniTheme.ACCENT_AMBER)
            tag_lbl = ctk.CTkLabel(
                row,
                text=item["tag"],
                font=ctk.CTkFont(size=10, weight="bold"),
                text_color=tag_color,
                fg_color=OmniTheme.BG_CARD,
                corner_radius=6,
                padx=8,
                pady=2
            )
            tag_lbl.pack(side="left", padx=10, pady=8)

            # File name & date
            info_frame = ctk.CTkFrame(row, fg_color="transparent")
            info_frame.pack(side="left", fill="x", expand=True, padx=6)

            fn_lbl = ctk.CTkLabel(info_frame, text=item["name"], font=ctk.CTkFont(family="Consolas", size=12, weight="bold"), text_color=OmniTheme.TEXT_MAIN)
            fn_lbl.pack(anchor="w")

            meta_lbl = ctk.CTkLabel(info_frame, text=f"{item['mtime_str']}  |  Size: {item['size_str']}", font=ctk.CTkFont(size=10), text_color=OmniTheme.TEXT_MUTED)
            meta_lbl.pack(anchor="w")

            # Actions
            play_btn = ctk.CTkButton(
                row,
                text="▶  Play",
                width=70,
                height=28,
                font=ctk.CTkFont(size=11, weight="bold"),
                fg_color=OmniTheme.ACCENT_GREEN,
                hover_color=OmniTheme.ACCENT_GREEN_HOVER,
                text_color="#000000",
                command=lambda p=item["path"]: self.controller.open_recording_file(p)
            )
            play_btn.pack(side="right", padx=6)

            up_btn = ctk.CTkButton(
                row,
                text="☁  Upload",
                width=75,
                height=28,
                font=ctk.CTkFont(size=11, weight="bold"),
                fg_color=OmniTheme.BG_CARD,
                hover_color=OmniTheme.BG_CARD_HOVER,
                command=lambda p=item["path"]: self._upload_recording(p)
            )
            up_btn.pack(side="right", padx=4)

    def _upload_recording(self, file_path: Path):
        self._set_status(f"Uploading {file_path.name} to Google Drive...")
        def _worker():
            ok, msg = self.controller.uploader.upload_file(str(file_path))
            self.after(0, lambda: self._set_status(f"Google Drive: {msg}"))
        threading.Thread(target=_worker, daemon=True).start()

    # -------------------------------------------------------------------------
    # TAB 6: Settings & Cloud
    # -------------------------------------------------------------------------

    def _build_settings_tab(self):
        tab = self.tab_settings

        card = ctk.CTkFrame(tab, fg_color=OmniTheme.BG_CARD, corner_radius=12, border_width=1, border_color=OmniTheme.BG_CARD_BORDER)
        card.pack(fill="both", expand=True, padx=10, pady=10)

        c_head = ctk.CTkLabel(card, text="⚙️  Application & Cloud Settings", font=ctk.CTkFont(size=16, weight="bold"), text_color=OmniTheme.TEXT_MAIN)
        c_head.pack(anchor="w", padx=16, pady=(16, 12))

        # System preferences
        sys_box = ctk.CTkFrame(card, fg_color=OmniTheme.BG_INPUT, corner_radius=10)
        sys_box.pack(fill="x", padx=16, pady=6)

        ctk.CTkLabel(sys_box, text="System Preferences:", font=ctk.CTkFont(size=13, weight="bold")).pack(anchor="w", padx=12, pady=(10, 4))
        ctk.CTkSwitch(sys_box, text="Minimize to Windows System Tray on close (Keep running in background)", variable=self.minimize_to_tray_var, progress_color=OmniTheme.ACCENT_CYAN).pack(anchor="w", padx=12, pady=6)
        ctk.CTkSwitch(sys_box, text="Enable Global Windows Hotkeys (Ctrl+Alt+D, Ctrl+Alt+M, Ctrl+Alt+C, Ctrl+Alt+R)", variable=self.enable_hotkeys_var, progress_color=OmniTheme.ACCENT_CYAN, command=self._toggle_hotkeys).pack(anchor="w", padx=12, pady=(6, 12))

        # Google Drive settings
        drive_box = ctk.CTkFrame(card, fg_color=OmniTheme.BG_INPUT, corner_radius=10)
        drive_box.pack(fill="x", padx=16, pady=10)

        ctk.CTkLabel(drive_box, text="Google Drive Cloud Sync:", font=ctk.CTkFont(size=13, weight="bold")).pack(anchor="w", padx=12, pady=(10, 4))
        drive_cfg = self.config.get("google_drive", {})

        p_lbl = ctk.CTkLabel(drive_box, text=f"Sync Method:  {drive_cfg.get('method', 'desktop').upper()}  |  Desktop Drive Path: {self.controller.uploader.desktop_sync_path or 'Not Detected'}", font=ctk.CTkFont(size=11), text_color=OmniTheme.TEXT_MUTED)
        p_lbl.pack(anchor="w", padx=12, pady=4)

        btn_row = ctk.CTkFrame(drive_box, fg_color="transparent")
        btn_row.pack(anchor="w", padx=12, pady=(6, 12))

        test_auth_btn = ctk.CTkButton(
            btn_row,
            text="🔐 Authenticate Google Drive API",
            font=ctk.CTkFont(size=11, weight="bold"),
            fg_color=OmniTheme.BG_CARD,
            hover_color=OmniTheme.BG_CARD_HOVER,
            command=self._on_test_drive_auth
        )
        test_auth_btn.pack(side="left", padx=(0, 8))

    def _toggle_hotkeys(self):
        if self.enable_hotkeys_var.get():
            self.hotkeys.start()
            self._set_status("Global Windows Hotkeys activated!")
        else:
            self.hotkeys.stop()
            self._set_status("Global Windows Hotkeys paused.")

    def _on_test_drive_auth(self):
        self._set_status("Testing Google Drive authentication...")
        def _worker():
            test_file = get_base_dir() / "auth_test.tmp"
            test_file.write_text("OmniCapture Auth Test")
            ok, msg = self.controller.uploader._upload_via_api(test_file)
            if test_file.exists():
                test_file.unlink()
            self.after(0, lambda: self._set_status(f"Drive Auth Result: {msg}"))
        threading.Thread(target=_worker, daemon=True).start()

    # -------------------------------------------------------------------------
    # Footer
    # -------------------------------------------------------------------------

    def _build_footer(self):
        """Bottom Footer Bar with Status Ticker and Hotkeys Legend."""
        footer_frame = ctk.CTkFrame(self, fg_color=OmniTheme.BG_CARD, height=36, corner_radius=0)
        footer_frame.pack(fill="x", side="bottom")

        self.status_ticker = ctk.CTkLabel(
            footer_frame,
            text="Ready — All systems operational.",
            font=ctk.CTkFont(family="Segoe UI", size=11),
            text_color=OmniTheme.TEXT_MUTED
        )
        self.status_ticker.pack(side="left", padx=16)

        hotkey_hint = ctk.CTkLabel(
            footer_frame,
            text="Shortcuts: Ctrl+Alt+D (Dual Record)  |  Ctrl+Alt+M (Mirror)  |  Ctrl+Alt+C (Camera)  |  Ctrl+Alt+R (Folder)",
            font=ctk.CTkFont(family="Segoe UI", size=10),
            text_color=OmniTheme.TEXT_DIM
        )
        hotkey_hint.pack(side="right", padx=16)

    def _set_status(self, message: str):
        self.status_ticker.configure(text=message)

    # -------------------------------------------------------------------------
    # Device State Updates (from Poller Callback)
    # -------------------------------------------------------------------------

    def _initial_refresh(self):
        self.controller.refresh_device_now()
        self._refresh_gallery_list()
        self._on_run_diagnostics()

    def _on_device_state_changed(self, state: Dict[str, Any]):
        """Runs whenever the background poller detects state changes."""
        self.after(0, lambda: self._update_device_ui(state))

    def _update_device_ui(self, state: Dict[str, Any]):
        status = state.get("status")
        model = state.get("model", "No Device")
        dev_id = state.get("device_id", "")
        conn_str = "Wi-Fi 📶" if state.get("is_wireless") else "USB 🔌"

        if status == "CONNECTED":
            self.device_pill.configure(
                text=f"● Connected: {model} ({dev_id}) [{conn_str}]",
                text_color=OmniTheme.STATUS_CONNECTED
            )
            batt = state.get("battery", {})
            lvl = batt.get("level", "N/A")
            b_stat = batt.get("status", "")
            self.battery_pill.configure(text=f"🔋 {lvl} ({b_stat})" if lvl != "N/A" else "🔋 Connected")

            ip = state.get("wifi_ip")
            if ip:
                self.wifi_ip_lbl.configure(text=f"Phone Wi-Fi IP:  {ip}:5555")
            else:
                self.wifi_ip_lbl.configure(text="Phone Wi-Fi IP:  Connected via USB")
        elif status == "UNAUTHORIZED":
            self.device_pill.configure(
                text=f"⚠️ {model} [UNAUTHORIZED - UNLOCK PHONE & TAP ALLOW]",
                text_color=OmniTheme.ACCENT_AMBER
            )
            self.battery_pill.configure(text="🔋 Unauthorized")
        elif status == "OFFLINE":
            self.device_pill.configure(
                text=f"⚠️ {model} [OFFLINE - RECONNECT USB]",
                text_color=OmniTheme.STATUS_OFFLINE
            )
            self.battery_pill.configure(text="🔋 Offline")
        else:
            self.device_pill.configure(
                text="○ No Device Connected (Plug in phone & enable USB Debugging)",
                text_color=OmniTheme.STATUS_DISCONNECTED
            )
            self.battery_pill.configure(text="🔋 --%")
            self.wifi_ip_lbl.configure(text="Phone Wi-Fi IP:  Device not connected")

    def _on_manual_refresh(self):
        self._set_status("Refreshing devices...")
        self.controller.refresh_device_now()
        self._refresh_gallery_list()
        self._set_status("Device scan complete.")

    def _on_release_lock(self):
        self._set_status("Releasing camera sensor lock...")
        ok, msg = self.controller.release_camera_lock()
        self._set_status(msg)
        self.tray.notify("Camera Lock", msg)

    # -------------------------------------------------------------------------
    # Actions: Dual Simultaneous Recording
    # -------------------------------------------------------------------------

    def _on_start_dual_recording(self):
        facing = "back" if "Back" in self.dual_facing_seg.get() else "front"
        pc_fps = 60 if "60" in self.dual_pc_fps_seg.get() else 30
        cam_fps = 60 if "60" in self.dual_cam_fps_seg.get() else 30
        fmt = self.dual_fmt_seg.get().lower()
        preview = self.dual_preview_var.get()
        upload = self.dual_upload_var.get()

        self._set_status("Initializing Dual Simultaneous Recording...")
        self.dual_log_box.insert("end", f"\n[INIT] Starting Dual Recording (PC: {pc_fps} FPS, Mobile: {cam_fps} FPS, Facing: {facing})...\n")
        self.dual_log_box.see("end")

        ok, msg = self.controller.start_dual_recording(
            facing=facing,
            pc_fps=pc_fps,
            camera_fps=cam_fps,
            record_format=fmt,
            preview=preview,
            auto_upload=upload,
            on_tick=self._on_dual_tick,
            on_complete=self._on_dual_complete
        )

        if ok:
            self.dual_start_btn.pack_forget()
            self.dual_live_card.pack(fill="x", padx=18, pady=(4, 16))
            self._set_status("🔴 DUAL SIMULTANEOUS RECORDING ACTIVE!")
            self.tray.notify("OmniCapture", "Dual Simultaneous Recording ACTIVE!")
        else:
            self._set_status(f"Dual Recording Error: {msg}")
            self.dual_log_box.insert("end", f"[ERROR] {msg}\n")
            self.dual_log_box.see("end")

    def _on_dual_tick(self, elapsed: float, pc_sz: int, cam_sz: int):
        m, s = divmod(int(elapsed), 60)
        h, m = divmod(m, 60)
        time_str = f"⏱  {h:02d}:{m:02d}:{s:02d}"

        def _fmt(b: int) -> str:
            for u in ["B", "KB", "MB", "GB"]:
                if b < 1024.0:
                    return f"{b:.2f} {u}"
                b /= 1024.0
            return f"{b:.2f} TB"

        stats_str = f"Stream 1 [PC Screen]: {_fmt(pc_sz)}  |  Stream 2 [Mobile Cam]: {_fmt(cam_sz)}"
        self.after(0, lambda: self._update_dual_live_labels(time_str, stats_str))

    def _update_dual_live_labels(self, time_str: str, stats_str: str):
        self.dual_timer_lbl.configure(text=time_str)
        self.dual_stream_stats_lbl.configure(text=stats_str)

    def _on_stop_dual_recording(self):
        self._set_status("Stopping and finalizing both video files...")
        self.controller.stop_dual_recording()

    def _on_dual_complete(self, result: Dict[str, Any]):
        """Invoked when dual recording finishes."""
        def _ui_update():
            self.dual_live_card.pack_forget()
            self.dual_start_btn.pack(fill="x")

            status = result.get("status", "UNKNOWN")
            dur_fmt = result.get("duration_formatted", "00:00")
            pc_file = result.get("pc_screen_file")
            cam_file = result.get("mobile_camera_file")

            log_msg = f"\n{'='*55}\nDUAL RECORDING COMPLETED: [{status}]\nDuration: {dur_fmt}\n"
            if pc_file:
                log_msg += f"  [✓] PC Screen:       {pc_file.name} ({result.get('pc_screen_size_formatted')})\n"
            else:
                log_msg += "  [✗] PC Screen:       FAILED or 0 bytes\n"

            if cam_file:
                log_msg += f"  [✓] Mobile Camera:   {cam_file.name} ({result.get('mobile_camera_size_formatted')})\n"
            else:
                log_msg += "  [✗] Mobile Camera:   FAILED or 0 bytes\n"
            log_msg += f"{'='*55}\n"

            self.dual_log_box.insert("end", log_msg)
            self.dual_log_box.see("end")

            self._set_status(f"Dual Recording Finished: {status}")
            self.tray.notify("OmniCapture", f"Dual Recording Finished: {status} ({dur_fmt})")
            self._refresh_gallery_list()

        self.after(0, _ui_update)

    # -------------------------------------------------------------------------
    # Actions: Mirror & Camera
    # -------------------------------------------------------------------------

    def _on_launch_mirror(self):
        uhid = "UHID" in self.mirror_mode_seg.get()
        screen_off = self.mirror_screen_off_var.get()
        stay_awake = self.mirror_awake_var.get()
        self._set_status("Launching Display Mirror & Touch Controller...")
        ok, msg = self.controller.launch_display_mirror(
            uhid=uhid,
            screen_off=screen_off,
            stay_awake=stay_awake,
            on_exit=lambda code: self.after(0, lambda: self._set_status("Display Mirror session ended."))
        )
        self._set_status(msg)

    def _on_start_screen_recording(self):
        fmt = "mkv" if "MKV" in self.screen_rec_fmt_seg.get() else "mp4"
        upload = self.screen_rec_upload_var.get()
        self._set_status("Starting Mobile Screen Recording...")
        ok, msg = self.controller.record_screen(
            record_format=fmt,
            auto_upload=upload,
            on_complete=lambda path, dur, sz: self.after(0, lambda: self._on_single_rec_complete(path, dur, sz, "Mobile Screen"))
        )
        self._set_status(msg)

    def _on_launch_camera_stream(self):
        facing = "back" if "Back" in self.cam_stream_facing_seg.get() else "front"
        mic = self.cam_stream_mic_var.get()
        self._set_status(f"Launching Stealth {facing.capitalize()} Camera stream...")
        ok, msg = self.controller.launch_stealth_camera(
            facing=facing,
            audio_mic=mic,
            on_exit=lambda code: self.after(0, lambda: self._set_status("Camera stream session ended."))
        )
        self._set_status(msg)

    def _on_start_camera_recording(self):
        facing = "back" if "Back" in self.cam_rec_facing_seg.get() else "front"
        fmt = self.cam_rec_fmt_seg.get().lower()
        preview = self.cam_rec_preview_var.get()
        upload = self.cam_rec_upload_var.get()

        self._set_status(f"Starting Mobile Camera Recording ({facing.capitalize()})...")
        ok, msg = self.controller.record_camera(
            facing=facing,
            record_format=fmt,
            preview=preview,
            audio_mic=True,
            auto_upload=upload,
            on_complete=lambda path, dur, sz: self.after(0, lambda: self._on_single_rec_complete(path, dur, sz, "Mobile Camera"))
        )
        self._set_status(msg)

    def _on_single_rec_complete(self, path: Optional[Path], dur: float, sz: int, mode_name: str):
        if path and sz > 0:
            sz_str = self.controller.recorder.format_size(sz)
            dur_str = self.controller.recorder.format_duration(dur)
            self._set_status(f"{mode_name} Recording Saved: {path.name} ({sz_str}, {dur_str})")
            self.tray.notify("OmniCapture", f"{mode_name} Saved: {path.name} ({sz_str})")
            self._refresh_gallery_list()
        else:
            self._set_status(f"{mode_name} Recording failed or produced 0 bytes.")

    def _on_switch_to_wireless(self):
        self._set_status("Configuring Wireless ADB on port 5555...")
        def _worker():
            ok, msg = self.controller.switch_to_wireless_adb()
            self.after(0, lambda: self._set_status(f"Wireless ADB: {msg}"))
            self.after(0, lambda: self.tray.notify("Wireless ADB", msg))
        threading.Thread(target=_worker, daemon=True).start()

    def _on_run_diagnostics(self):
        diag = self.controller.query_diagnostics()
        out = (
            f"=== RUNTIME & BINARIES ===\n"
            f"ADB Binary:    {diag['adb_path']} ({diag['adb_version']})\n"
            f"Scrcpy Engine: {diag['scrcpy_path']}\n"
            f"FFmpeg Engine: {diag['ffmpeg_path']} ({diag['ffmpeg_version']})\n\n"
            f"=== CAMERA2 SENSORS ===\n{diag['cameras_info']}\n\n"
            f"=== RESOLUTIONS ===\n{diag['camera_sizes']}\n"
        )
        self.diag_box.delete("1.0", "end")
        self.diag_box.insert("1.0", out)

    # -------------------------------------------------------------------------
    # Global Hotkey Handlers
    # -------------------------------------------------------------------------

    def _setup_hotkeys(self):
        # 1: Ctrl+Alt+D (Dual Recording)
        # 2: Ctrl+Alt+M (Mirror)
        # 3: Ctrl+Alt+C (Camera)
        # 4: Ctrl+Alt+R (Folder)
        self.hotkeys.register(1, 0x0002 | 0x0001, ord("D"), self._on_hotkey_dual_record)
        self.hotkeys.register(2, 0x0002 | 0x0001, ord("M"), self._on_hotkey_mirror)
        self.hotkeys.register(3, 0x0002 | 0x0001, ord("C"), self._on_hotkey_camera)
        self.hotkeys.register(4, 0x0002 | 0x0001, ord("R"), self.controller.open_recordings_folder)

    def _on_hotkey_dual_record(self):
        if self.controller.is_dual_recording():
            self._on_stop_dual_recording()
        else:
            self._show_window()
            self.tabs.set("🎬 Dual Recording (Hero)")
            self._on_start_dual_recording()

    def _on_hotkey_mirror(self):
        self._show_window()
        self.tabs.set("📱 Display Mirror & Control")
        self._on_launch_mirror()

    def _on_hotkey_camera(self):
        self._show_window()
        self.tabs.set("📷 Stealth Camera")
        self._on_launch_camera_stream()

    # -------------------------------------------------------------------------
    # Window & Tray Lifecycle
    # -------------------------------------------------------------------------

    def _show_window(self):
        """Restore window from minimized / tray state."""
        self.deiconify()
        self.lift()
        self.focus_force()

    def _on_window_close(self):
        """Handle WM_DELETE_WINDOW."""
        if self.minimize_to_tray_var.get():
            self.withdraw()
            self.tray.notify(
                "OmniCapture Minimized",
                "OmniCapture is running in the system tray. Use shortcuts (Ctrl+Alt+D) or click the tray icon to restore."
            )
        else:
            self._on_app_exit()

    def _on_app_exit(self):
        """Clean shutdown of all background components."""
        if self.controller.is_dual_recording():
            self.controller.stop_dual_recording()
        self.controller.stop_device_poller()
        self.hotkeys.stop()
        self.tray.stop()
        self.destroy()
        sys.exit(0)
