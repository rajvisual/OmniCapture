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
    OmniCapture Modern Desktop Dashboard.
    Clean, restrained design adhering to high-craft human interface guidelines:
    no pill spam, no all-caps subtitles, no nested boxed borders, and clean typography.
    """

    def __init__(self, config: Dict[str, Any]):
        super().__init__()

        self.config = config
        self.controller = GUIController(config)

        # Window styling & geometry
        OmniTheme.apply_appearance()
        self.title("OmniCapture")
        self.geometry("1080x720")
        self.minsize(940, 600)
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

        # Build clean UI layout
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
        self.after(250, self._initial_refresh)

    def _set_app_icon(self):
        """Set native window icon."""
        ico_path = resolve_resource("assets/logo/omnicapture.ico")
        if ico_path.is_file():
            try:
                self.iconbitmap(str(ico_path))
            except Exception:
                pass

    # -------------------------------------------------------------------------
    # Layout: Header
    # -------------------------------------------------------------------------

    def _build_header(self):
        """Clean top bar: App title, natural device status text, and quiet action buttons."""
        header_frame = ctk.CTkFrame(
            self,
            fg_color=OmniTheme.BG_CARD,
            corner_radius=OmniTheme.RADIUS_CARD,
            border_width=0
        )
        header_frame.pack(fill="x", padx=16, pady=(14, 8))

        # Brand / Title
        brand_frame = ctk.CTkFrame(header_frame, fg_color="transparent")
        brand_frame.pack(side="left", padx=16, pady=12)

        logo_path = resolve_resource("assets/logo/omnicapture-icon.png")
        if logo_path.is_file():
            try:
                pil_img = Image.open(str(logo_path)).resize((28, 28), Image.Resampling.LANCZOS)
                self.logo_ctk = ctk.CTkImage(light_image=pil_img, dark_image=pil_img, size=(28, 28))
                logo_lbl = ctk.CTkLabel(brand_frame, image=self.logo_ctk, text="")
                logo_lbl.pack(side="left", padx=(0, 10))
            except Exception:
                pass

        title_lbl = ctk.CTkLabel(
            brand_frame,
            text="OmniCapture",
            font=ctk.CTkFont(family="Segoe UI", size=17, weight="bold"),
            text_color=OmniTheme.TEXT_MAIN
        )
        title_lbl.pack(side="left")

        ver_lbl = ctk.CTkLabel(
            brand_frame,
            text="1.2.0",
            font=ctk.CTkFont(family="Segoe UI", size=12),
            text_color=OmniTheme.TEXT_DIM
        )
        ver_lbl.pack(side="left", padx=(8, 0))

        # Right telemetry & controls (no pill shapes, no heavy borders)
        status_frame = ctk.CTkFrame(header_frame, fg_color="transparent")
        status_frame.pack(side="right", padx=16, pady=12)

        self.device_status_lbl = ctk.CTkLabel(
            status_frame,
            text="Searching for device...",
            font=ctk.CTkFont(family="Segoe UI", size=12),
            text_color=OmniTheme.TEXT_MUTED
        )
        self.device_status_lbl.pack(side="left", padx=(0, 16))

        self.refresh_btn = ctk.CTkButton(
            status_frame,
            text="Refresh",
            width=70,
            height=28,
            font=ctk.CTkFont(family="Segoe UI", size=11),
            fg_color=OmniTheme.BG_INPUT,
            hover_color=OmniTheme.BG_CARD_HOVER,
            text_color=OmniTheme.TEXT_MAIN,
            corner_radius=OmniTheme.RADIUS_CONTROL,
            command=self._on_manual_refresh
        )
        self.refresh_btn.pack(side="left", padx=4)

        self.lock_btn = ctk.CTkButton(
            status_frame,
            text="Release camera lock",
            width=135,
            height=28,
            font=ctk.CTkFont(family="Segoe UI", size=11),
            fg_color=OmniTheme.BG_INPUT,
            hover_color=OmniTheme.BG_CARD_HOVER,
            text_color=OmniTheme.TEXT_MUTED,
            corner_radius=OmniTheme.RADIUS_CONTROL,
            command=self._on_release_lock
        )
        self.lock_btn.pack(side="left", padx=4)

    # -------------------------------------------------------------------------
    # Layout: Tab Navigation
    # -------------------------------------------------------------------------

    def _build_tabs(self):
        """Tabbed workspace without emoji noise or nested boxed containers."""
        self.tabs = ctk.CTkTabview(
            self,
            fg_color=OmniTheme.BG_ROOT,
            segmented_button_fg_color=OmniTheme.BG_CARD,
            segmented_button_selected_color=OmniTheme.ACCENT_PRIMARY,
            segmented_button_selected_hover_color=OmniTheme.ACCENT_PRIMARY_HOVER,
            segmented_button_unselected_color=OmniTheme.BG_CARD,
            segmented_button_unselected_hover_color=OmniTheme.BG_CARD_HOVER,
            text_color=OmniTheme.TEXT_MAIN,
            corner_radius=OmniTheme.RADIUS_CARD
        )
        self.tabs.pack(fill="both", expand=True, padx=16, pady=(0, 8))

        # Clean tab labels (no emoji icons in headers)
        self.tab_dual = self.tabs.add("Dual Recording")
        self.tab_mirror = self.tabs.add("Screen Mirror")
        self.tab_camera = self.tabs.add("Camera")
        self.tab_wireless = self.tabs.add("Diagnostics")
        self.tab_gallery = self.tabs.add("Recordings")
        self.tab_settings = self.tabs.add("Settings")

        self._build_dual_recording_tab()
        self._build_mirror_tab()
        self._build_camera_tab()
        self._build_wireless_tab()
        self._build_gallery_tab()
        self._build_settings_tab()

    # -------------------------------------------------------------------------
    # Tab 1: Dual Simultaneous Recording
    # -------------------------------------------------------------------------

    def _build_dual_recording_tab(self):
        tab = self.tab_dual

        card = ctk.CTkFrame(
            tab,
            fg_color=OmniTheme.BG_CARD,
            corner_radius=OmniTheme.RADIUS_CARD,
            border_width=0
        )
        card.pack(fill="x", padx=10, pady=10)

        # Title & Subtitle
        header_row = ctk.CTkFrame(card, fg_color="transparent")
        header_row.pack(fill="x", padx=20, pady=(18, 6))

        title = ctk.CTkLabel(
            header_row,
            text="Dual Recording",
            font=ctk.CTkFont(family="Segoe UI", size=16, weight="bold"),
            text_color=OmniTheme.TEXT_MAIN
        )
        title.pack(anchor="w")

        subtitle = ctk.CTkLabel(
            header_row,
            text="Record PC desktop and mobile camera concurrently into separate video files",
            font=ctk.CTkFont(family="Segoe UI", size=12),
            text_color=OmniTheme.TEXT_MUTED
        )
        subtitle.pack(anchor="w")

        # Form Controls (Natural grouping, no redundant borders)
        form_frame = ctk.CTkFrame(card, fg_color="transparent")
        form_frame.pack(fill="x", padx=20, pady=12)

        # Row 1: Pickers
        row1 = ctk.CTkFrame(form_frame, fg_color="transparent")
        row1.pack(fill="x", pady=(0, 12))

        ctk.CTkLabel(row1, text="Camera", font=ctk.CTkFont(size=11), text_color=OmniTheme.TEXT_MUTED).pack(side="left", padx=(0, 8))
        self.dual_facing_seg = ctk.CTkSegmentedButton(
            row1,
            values=["Back", "Front"],
            corner_radius=OmniTheme.RADIUS_CONTROL,
            selected_color=OmniTheme.ACCENT_PRIMARY,
            selected_hover_color=OmniTheme.ACCENT_PRIMARY_HOVER
        )
        self.dual_facing_seg.set("Back")
        self.dual_facing_seg.pack(side="left", padx=(0, 20))

        ctk.CTkLabel(row1, text="PC rate", font=ctk.CTkFont(size=11), text_color=OmniTheme.TEXT_MUTED).pack(side="left", padx=(0, 8))
        self.dual_pc_fps_seg = ctk.CTkSegmentedButton(
            row1,
            values=["30 fps", "60 fps"],
            corner_radius=OmniTheme.RADIUS_CONTROL,
            selected_color=OmniTheme.ACCENT_PRIMARY
        )
        self.dual_pc_fps_seg.set("30 fps")
        self.dual_pc_fps_seg.pack(side="left", padx=(0, 20))

        ctk.CTkLabel(row1, text="Camera rate", font=ctk.CTkFont(size=11), text_color=OmniTheme.TEXT_MUTED).pack(side="left", padx=(0, 8))
        self.dual_cam_fps_seg = ctk.CTkSegmentedButton(
            row1,
            values=["30 fps", "60 fps"],
            corner_radius=OmniTheme.RADIUS_CONTROL,
            selected_color=OmniTheme.ACCENT_PRIMARY
        )
        self.dual_cam_fps_seg.set("30 fps")
        self.dual_cam_fps_seg.pack(side="left", padx=(0, 20))

        ctk.CTkLabel(row1, text="Format", font=ctk.CTkFont(size=11), text_color=OmniTheme.TEXT_MUTED).pack(side="left", padx=(0, 8))
        self.dual_fmt_seg = ctk.CTkSegmentedButton(
            row1,
            values=["MP4", "MKV"],
            corner_radius=OmniTheme.RADIUS_CONTROL,
            selected_color=OmniTheme.ACCENT_PRIMARY
        )
        self.dual_fmt_seg.set("MP4")
        self.dual_fmt_seg.pack(side="left")

        # Row 2: Clean Switches
        row2 = ctk.CTkFrame(form_frame, fg_color="transparent")
        row2.pack(fill="x", pady=(0, 4))

        self.dual_preview_var = ctk.BooleanVar(value=True)
        self.dual_preview_switch = ctk.CTkSwitch(
            row2,
            text="Show camera preview",
            variable=self.dual_preview_var,
            progress_color=OmniTheme.ACCENT_PRIMARY
        )
        self.dual_preview_switch.pack(side="left", padx=(0, 24))

        self.dual_upload_var = ctk.BooleanVar(value=False)
        self.dual_upload_switch = ctk.CTkSwitch(
            row2,
            text="Upload to Google Drive when finished",
            variable=self.dual_upload_var,
            progress_color=OmniTheme.STATUS_CONNECTED
        )
        self.dual_upload_switch.pack(side="left")

        # Action Buttons
        self.dual_action_frame = ctk.CTkFrame(card, fg_color="transparent")
        self.dual_action_frame.pack(fill="x", padx=20, pady=(8, 18))

        self.dual_start_btn = ctk.CTkButton(
            self.dual_action_frame,
            text="Start Dual Recording",
            height=38,
            font=ctk.CTkFont(family="Segoe UI", size=13, weight="bold"),
            fg_color=OmniTheme.ACCENT_PRIMARY,
            hover_color=OmniTheme.ACCENT_PRIMARY_HOVER,
            corner_radius=OmniTheme.RADIUS_CONTROL,
            command=self._on_start_dual_recording
        )
        self.dual_start_btn.pack(anchor="w", ipadx=16)

        # Active Recording State View
        self.dual_live_card = ctk.CTkFrame(card, fg_color=OmniTheme.BG_INPUT, corner_radius=OmniTheme.RADIUS_CARD)

        live_row = ctk.CTkFrame(self.dual_live_card, fg_color="transparent")
        live_row.pack(fill="x", padx=16, pady=12)

        self.dual_timer_lbl = ctk.CTkLabel(
            live_row,
            text="00:00:00",
            font=ctk.CTkFont(family="Consolas", size=22, weight="bold"),
            text_color=OmniTheme.STATUS_RECORDING
        )
        self.dual_timer_lbl.pack(side="left", padx=(0, 20))

        self.dual_stream_stats_lbl = ctk.CTkLabel(
            live_row,
            text="PC screen: 0.00 MB  ·  Camera: 0.00 MB",
            font=ctk.CTkFont(family="Segoe UI", size=12),
            text_color=OmniTheme.TEXT_BODY
        )
        self.dual_stream_stats_lbl.pack(side="left")

        self.dual_stop_btn = ctk.CTkButton(
            live_row,
            text="Stop Recording",
            width=130,
            height=34,
            font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"),
            fg_color=OmniTheme.STATUS_RECORDING,
            hover_color=OmniTheme.STATUS_RECORDING_HOVER,
            corner_radius=OmniTheme.RADIUS_CONTROL,
            command=self._on_stop_dual_recording
        )
        self.dual_stop_btn.pack(side="right")

        # Clean Log View (No heavy borders or box-in-a-box)
        self.dual_feedback_frame = ctk.CTkFrame(
            tab,
            fg_color=OmniTheme.BG_CARD,
            corner_radius=OmniTheme.RADIUS_CARD,
            border_width=0
        )
        self.dual_feedback_frame.pack(fill="both", expand=True, padx=10, pady=(0, 10))

        log_head = ctk.CTkLabel(
            self.dual_feedback_frame,
            text="Activity",
            font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"),
            text_color=OmniTheme.TEXT_MUTED
        )
        log_head.pack(anchor="w", padx=16, pady=(12, 4))

        self.dual_log_box = ctk.CTkTextbox(
            self.dual_feedback_frame,
            fg_color=OmniTheme.BG_INPUT,
            text_color=OmniTheme.TEXT_BODY,
            font=ctk.CTkFont(family="Consolas", size=11),
            corner_radius=OmniTheme.RADIUS_CONTROL
        )
        self.dual_log_box.pack(fill="both", expand=True, padx=16, pady=(0, 14))
        self.dual_log_box.insert("1.0", "Ready to record.\nUse the button above or press Ctrl+Alt+D.\n")

    # -------------------------------------------------------------------------
    # Tab 2: Screen Mirror
    # -------------------------------------------------------------------------

    def _build_mirror_tab(self):
        tab = self.tab_mirror

        grid_frame = ctk.CTkFrame(tab, fg_color="transparent")
        grid_frame.pack(fill="both", expand=True, padx=10, pady=10)
        grid_frame.columnconfigure(0, weight=1)
        grid_frame.columnconfigure(1, weight=1)
        grid_frame.rowconfigure(0, weight=1)

        # Card 1: Mirror & Control
        card1 = ctk.CTkFrame(grid_frame, fg_color=OmniTheme.BG_CARD, corner_radius=OmniTheme.RADIUS_CARD, border_width=0)
        card1.grid(row=0, column=0, sticky="nsew", padx=(0, 6))

        c1_head = ctk.CTkLabel(card1, text="Display Mirror", font=ctk.CTkFont(size=15, weight="bold"), text_color=OmniTheme.TEXT_MAIN)
        c1_head.pack(anchor="w", padx=16, pady=(16, 12))

        ctrl_box = ctk.CTkFrame(card1, fg_color="transparent")
        ctrl_box.pack(fill="x", padx=16, pady=4)

        ctk.CTkLabel(ctrl_box, text="Touch mode", font=ctk.CTkFont(size=11), text_color=OmniTheme.TEXT_MUTED).pack(anchor="w", pady=(0, 4))
        self.mirror_mode_seg = ctk.CTkSegmentedButton(
            ctrl_box,
            values=["Standard Touch", "Hardware Mouse (UHID)"],
            selected_color=OmniTheme.ACCENT_PRIMARY,
            corner_radius=OmniTheme.RADIUS_CONTROL
        )
        self.mirror_mode_seg.set("Standard Touch")
        self.mirror_mode_seg.pack(fill="x", pady=(0, 10))

        self.mirror_screen_off_var = ctk.BooleanVar(value=False)
        ctk.CTkSwitch(ctrl_box, text="Turn phone screen off during mirror", variable=self.mirror_screen_off_var, progress_color=OmniTheme.ACCENT_PRIMARY).pack(anchor="w", pady=6)

        self.mirror_awake_var = ctk.BooleanVar(value=True)
        ctk.CTkSwitch(ctrl_box, text="Keep phone display awake while plugged in", variable=self.mirror_awake_var, progress_color=OmniTheme.ACCENT_PRIMARY).pack(anchor="w", pady=6)

        self.mirror_launch_btn = ctk.CTkButton(
            card1,
            text="Launch Mirror",
            height=36,
            font=ctk.CTkFont(size=12, weight="bold"),
            fg_color=OmniTheme.ACCENT_PRIMARY,
            hover_color=OmniTheme.ACCENT_PRIMARY_HOVER,
            corner_radius=OmniTheme.RADIUS_CONTROL,
            command=self._on_launch_mirror
        )
        self.mirror_launch_btn.pack(anchor="w", padx=16, pady=(18, 16))

        # Card 2: Mobile Screen Recording
        card2 = ctk.CTkFrame(grid_frame, fg_color=OmniTheme.BG_CARD, corner_radius=OmniTheme.RADIUS_CARD, border_width=0)
        card2.grid(row=0, column=1, sticky="nsew", padx=(6, 0))

        c2_head = ctk.CTkLabel(card2, text="Screen Recording", font=ctk.CTkFont(size=15, weight="bold"), text_color=OmniTheme.TEXT_MAIN)
        c2_head.pack(anchor="w", padx=16, pady=(16, 12))

        rec_box = ctk.CTkFrame(card2, fg_color="transparent")
        rec_box.pack(fill="x", padx=16, pady=4)

        ctk.CTkLabel(rec_box, text="Format", font=ctk.CTkFont(size=11), text_color=OmniTheme.TEXT_MUTED).pack(anchor="w", pady=(0, 4))
        self.screen_rec_fmt_seg = ctk.CTkSegmentedButton(
            rec_box,
            values=["MP4", "MKV"],
            selected_color=OmniTheme.ACCENT_PRIMARY,
            corner_radius=OmniTheme.RADIUS_CONTROL
        )
        self.screen_rec_fmt_seg.set("MP4")
        self.screen_rec_fmt_seg.pack(fill="x", pady=(0, 10))

        self.screen_rec_upload_var = ctk.BooleanVar(value=False)
        ctk.CTkSwitch(rec_box, text="Upload to Google Drive when finished", variable=self.screen_rec_upload_var, progress_color=OmniTheme.STATUS_CONNECTED).pack(anchor="w", pady=6)

        self.screen_rec_btn = ctk.CTkButton(
            card2,
            text="Start Screen Recording",
            height=36,
            font=ctk.CTkFont(size=12, weight="bold"),
            fg_color=OmniTheme.ACCENT_PRIMARY,
            hover_color=OmniTheme.ACCENT_PRIMARY_HOVER,
            corner_radius=OmniTheme.RADIUS_CONTROL,
            command=self._on_start_screen_recording
        )
        self.screen_rec_btn.pack(anchor="w", padx=16, pady=(18, 16))

    # -------------------------------------------------------------------------
    # Tab 3: Camera
    # -------------------------------------------------------------------------

    def _build_camera_tab(self):
        tab = self.tab_camera

        grid_frame = ctk.CTkFrame(tab, fg_color="transparent")
        grid_frame.pack(fill="both", expand=True, padx=10, pady=10)
        grid_frame.columnconfigure(0, weight=1)
        grid_frame.columnconfigure(1, weight=1)
        grid_frame.rowconfigure(0, weight=1)

        # Card 1: Live Camera Feed
        card1 = ctk.CTkFrame(grid_frame, fg_color=OmniTheme.BG_CARD, corner_radius=OmniTheme.RADIUS_CARD, border_width=0)
        card1.grid(row=0, column=0, sticky="nsew", padx=(0, 6))

        c1_head = ctk.CTkLabel(card1, text="Camera Feed", font=ctk.CTkFont(size=15, weight="bold"), text_color=OmniTheme.TEXT_MAIN)
        c1_head.pack(anchor="w", padx=16, pady=(16, 12))

        box1 = ctk.CTkFrame(card1, fg_color="transparent")
        box1.pack(fill="x", padx=16, pady=4)

        ctk.CTkLabel(box1, text="Sensor", font=ctk.CTkFont(size=11), text_color=OmniTheme.TEXT_MUTED).pack(anchor="w", pady=(0, 4))
        self.cam_stream_facing_seg = ctk.CTkSegmentedButton(
            box1,
            values=["Back", "Front"],
            selected_color=OmniTheme.ACCENT_PRIMARY,
            corner_radius=OmniTheme.RADIUS_CONTROL
        )
        self.cam_stream_facing_seg.set("Back")
        self.cam_stream_facing_seg.pack(fill="x", pady=(0, 10))

        self.cam_stream_mic_var = ctk.BooleanVar(value=True)
        ctk.CTkSwitch(box1, text="Capture microphone audio", variable=self.cam_stream_mic_var, progress_color=OmniTheme.ACCENT_PRIMARY).pack(anchor="w", pady=6)

        self.cam_stream_btn = ctk.CTkButton(
            card1,
            text="Launch Camera Feed",
            height=36,
            font=ctk.CTkFont(size=12, weight="bold"),
            fg_color=OmniTheme.ACCENT_PRIMARY,
            hover_color=OmniTheme.ACCENT_PRIMARY_HOVER,
            corner_radius=OmniTheme.RADIUS_CONTROL,
            command=self._on_launch_camera_stream
        )
        self.cam_stream_btn.pack(anchor="w", padx=16, pady=(18, 16))

        # Card 2: Camera Recording
        card2 = ctk.CTkFrame(grid_frame, fg_color=OmniTheme.BG_CARD, corner_radius=OmniTheme.RADIUS_CARD, border_width=0)
        card2.grid(row=0, column=1, sticky="nsew", padx=(6, 0))

        c2_head = ctk.CTkLabel(card2, text="Camera Recording", font=ctk.CTkFont(size=15, weight="bold"), text_color=OmniTheme.TEXT_MAIN)
        c2_head.pack(anchor="w", padx=16, pady=(16, 12))

        box2 = ctk.CTkFrame(card2, fg_color="transparent")
        box2.pack(fill="x", padx=16, pady=4)

        ctk.CTkLabel(box2, text="Sensor", font=ctk.CTkFont(size=11), text_color=OmniTheme.TEXT_MUTED).pack(anchor="w", pady=(0, 4))
        self.cam_rec_facing_seg = ctk.CTkSegmentedButton(
            box2,
            values=["Back", "Front"],
            selected_color=OmniTheme.ACCENT_PRIMARY,
            corner_radius=OmniTheme.RADIUS_CONTROL
        )
        self.cam_rec_facing_seg.set("Back")
        self.cam_rec_facing_seg.pack(fill="x", pady=(0, 10))

        ctk.CTkLabel(box2, text="Format", font=ctk.CTkFont(size=11), text_color=OmniTheme.TEXT_MUTED).pack(anchor="w", pady=(6, 4))
        self.cam_rec_fmt_seg = ctk.CTkSegmentedButton(
            box2,
            values=["MP4", "MKV"],
            selected_color=OmniTheme.ACCENT_PRIMARY,
            corner_radius=OmniTheme.RADIUS_CONTROL
        )
        self.cam_rec_fmt_seg.set("MP4")
        self.cam_rec_fmt_seg.pack(fill="x", pady=(0, 10))

        self.cam_rec_preview_var = ctk.BooleanVar(value=True)
        ctk.CTkSwitch(box2, text="Show live preview window", variable=self.cam_rec_preview_var, progress_color=OmniTheme.ACCENT_PRIMARY).pack(anchor="w", pady=6)

        self.cam_rec_upload_var = ctk.BooleanVar(value=False)
        ctk.CTkSwitch(box2, text="Upload to Google Drive", variable=self.cam_rec_upload_var, progress_color=OmniTheme.STATUS_CONNECTED).pack(anchor="w", pady=6)

        self.cam_rec_btn = ctk.CTkButton(
            card2,
            text="Start Camera Recording",
            height=36,
            font=ctk.CTkFont(size=12, weight="bold"),
            fg_color=OmniTheme.ACCENT_PRIMARY,
            hover_color=OmniTheme.ACCENT_PRIMARY_HOVER,
            corner_radius=OmniTheme.RADIUS_CONTROL,
            command=self._on_start_camera_recording
        )
        self.cam_rec_btn.pack(anchor="w", padx=16, pady=(18, 16))

    # -------------------------------------------------------------------------
    # Tab 4: Diagnostics & Wireless
    # -------------------------------------------------------------------------

    def _build_wireless_tab(self):
        tab = self.tab_wireless

        grid_frame = ctk.CTkFrame(tab, fg_color="transparent")
        grid_frame.pack(fill="both", expand=True, padx=10, pady=10)
        grid_frame.columnconfigure(0, weight=1)
        grid_frame.columnconfigure(1, weight=1)
        grid_frame.rowconfigure(0, weight=1)

        # Card 1: Wireless ADB
        card1 = ctk.CTkFrame(grid_frame, fg_color=OmniTheme.BG_CARD, corner_radius=OmniTheme.RADIUS_CARD, border_width=0)
        card1.grid(row=0, column=0, sticky="nsew", padx=(0, 6))

        c1_head = ctk.CTkLabel(card1, text="Wireless ADB", font=ctk.CTkFont(size=15, weight="bold"), text_color=OmniTheme.TEXT_MAIN)
        c1_head.pack(anchor="w", padx=16, pady=(16, 8))

        w_box = ctk.CTkFrame(card1, fg_color="transparent")
        w_box.pack(fill="x", padx=16, pady=4)

        self.wifi_ip_lbl = ctk.CTkLabel(w_box, text="IP: Scanning...", font=ctk.CTkFont(family="Segoe UI", size=13))
        self.wifi_ip_lbl.pack(anchor="w", pady=(4, 12))

        self.switch_wifi_btn = ctk.CTkButton(
            card1,
            text="Switch to Wi-Fi ADB",
            height=36,
            font=ctk.CTkFont(size=12, weight="bold"),
            fg_color=OmniTheme.ACCENT_PRIMARY,
            hover_color=OmniTheme.ACCENT_PRIMARY_HOVER,
            corner_radius=OmniTheme.RADIUS_CONTROL,
            command=self._on_switch_to_wireless
        )
        self.switch_wifi_btn.pack(anchor="w", padx=16, pady=(8, 16))

        # Card 2: Hardware Diagnostics
        card2 = ctk.CTkFrame(grid_frame, fg_color=OmniTheme.BG_CARD, corner_radius=OmniTheme.RADIUS_CARD, border_width=0)
        card2.grid(row=0, column=1, sticky="nsew", padx=(6, 0))

        c2_head = ctk.CTkLabel(card2, text="Hardware Diagnostics", font=ctk.CTkFont(size=15, weight="bold"), text_color=OmniTheme.TEXT_MAIN)
        c2_head.pack(anchor="w", padx=16, pady=(16, 8))

        self.diag_box = ctk.CTkTextbox(
            card2,
            fg_color=OmniTheme.BG_INPUT,
            font=ctk.CTkFont(family="Consolas", size=10),
            corner_radius=OmniTheme.RADIUS_CONTROL
        )
        self.diag_box.pack(fill="both", expand=True, padx=16, pady=(0, 10))

        self.diag_btn = ctk.CTkButton(
            card2,
            text="Run Diagnostics",
            height=32,
            font=ctk.CTkFont(size=11),
            fg_color=OmniTheme.BG_INPUT,
            hover_color=OmniTheme.BG_CARD_HOVER,
            corner_radius=OmniTheme.RADIUS_CONTROL,
            command=self._on_run_diagnostics
        )
        self.diag_btn.pack(anchor="w", padx=16, pady=(0, 16))

    # -------------------------------------------------------------------------
    # Tab 5: Recordings Gallery
    # -------------------------------------------------------------------------

    def _build_gallery_tab(self):
        tab = self.tab_gallery

        top_row = ctk.CTkFrame(tab, fg_color="transparent")
        top_row.pack(fill="x", padx=10, pady=(10, 8))

        gal_lbl = ctk.CTkLabel(top_row, text="Recordings", font=ctk.CTkFont(size=15, weight="bold"), text_color=OmniTheme.TEXT_MAIN)
        gal_lbl.pack(side="left")

        open_folder_btn = ctk.CTkButton(
            top_row,
            text="Open folder",
            width=110,
            height=28,
            font=ctk.CTkFont(size=11),
            fg_color=OmniTheme.BG_CARD,
            hover_color=OmniTheme.BG_CARD_HOVER,
            corner_radius=OmniTheme.RADIUS_CONTROL,
            command=self.controller.open_recordings_folder
        )
        open_folder_btn.pack(side="right", padx=6)

        refresh_gal_btn = ctk.CTkButton(
            top_row,
            text="Refresh",
            width=80,
            height=28,
            font=ctk.CTkFont(size=11),
            fg_color=OmniTheme.BG_CARD,
            hover_color=OmniTheme.BG_CARD_HOVER,
            corner_radius=OmniTheme.RADIUS_CONTROL,
            command=self._refresh_gallery_list
        )
        refresh_gal_btn.pack(side="right", padx=6)

        self.gallery_scroll = ctk.CTkScrollableFrame(
            tab,
            fg_color=OmniTheme.BG_CARD,
            corner_radius=OmniTheme.RADIUS_CARD,
            border_width=0
        )
        self.gallery_scroll.pack(fill="both", expand=True, padx=10, pady=(0, 10))

    def _refresh_gallery_list(self):
        for widget in self.gallery_scroll.winfo_children():
            widget.destroy()

        items = self.controller.get_recordings_list()
        if not items:
            empty_lbl = ctk.CTkLabel(
                self.gallery_scroll,
                text="No recordings found in recordings/",
                font=ctk.CTkFont(size=12),
                text_color=OmniTheme.TEXT_MUTED
            )
            empty_lbl.pack(pady=40)
            return

        for item in items:
            row = ctk.CTkFrame(self.gallery_scroll, fg_color=OmniTheme.BG_INPUT, corner_radius=OmniTheme.RADIUS_CONTROL)
            row.pack(fill="x", padx=6, pady=3)

            info_frame = ctk.CTkFrame(row, fg_color="transparent")
            info_frame.pack(side="left", fill="x", expand=True, padx=12, pady=8)

            fn_lbl = ctk.CTkLabel(info_frame, text=item["name"], font=ctk.CTkFont(family="Consolas", size=12), text_color=OmniTheme.TEXT_MAIN)
            fn_lbl.pack(anchor="w")

            meta_lbl = ctk.CTkLabel(info_frame, text=f"{item['tag']}  ·  {item['mtime_str']}  ·  {item['size_str']}", font=ctk.CTkFont(size=10), text_color=OmniTheme.TEXT_MUTED)
            meta_lbl.pack(anchor="w")

            play_btn = ctk.CTkButton(
                row,
                text="Play",
                width=60,
                height=26,
                font=ctk.CTkFont(size=11),
                fg_color=OmniTheme.BG_CARD,
                hover_color=OmniTheme.BG_CARD_HOVER,
                corner_radius=OmniTheme.RADIUS_CONTROL,
                command=lambda p=item["path"]: self.controller.open_recording_file(p)
            )
            play_btn.pack(side="right", padx=6)

            up_btn = ctk.CTkButton(
                row,
                text="Upload",
                width=65,
                height=26,
                font=ctk.CTkFont(size=11),
                fg_color=OmniTheme.BG_CARD,
                hover_color=OmniTheme.BG_CARD_HOVER,
                corner_radius=OmniTheme.RADIUS_CONTROL,
                command=lambda p=item["path"]: self._upload_recording(p)
            )
            up_btn.pack(side="right", padx=4)

    def _upload_recording(self, file_path: Path):
        self._set_status(f"Uploading {file_path.name}")
        def _worker():
            ok, msg = self.controller.uploader.upload_file(str(file_path))
            self.after(0, lambda: self._set_status(msg))
        threading.Thread(target=_worker, daemon=True).start()

    # -------------------------------------------------------------------------
    # Tab 6: Settings
    # -------------------------------------------------------------------------

    def _build_settings_tab(self):
        tab = self.tab_settings

        card = ctk.CTkFrame(tab, fg_color=OmniTheme.BG_CARD, corner_radius=OmniTheme.RADIUS_CARD, border_width=0)
        card.pack(fill="both", expand=True, padx=10, pady=10)

        c_head = ctk.CTkLabel(card, text="Settings", font=ctk.CTkFont(size=15, weight="bold"), text_color=OmniTheme.TEXT_MAIN)
        c_head.pack(anchor="w", padx=18, pady=(16, 12))

        sys_box = ctk.CTkFrame(card, fg_color="transparent")
        sys_box.pack(fill="x", padx=18, pady=4)

        ctk.CTkLabel(sys_box, text="System", font=ctk.CTkFont(size=12, weight="bold"), text_color=OmniTheme.TEXT_MAIN).pack(anchor="w", pady=(4, 6))
        ctk.CTkSwitch(sys_box, text="Minimize to system tray on close", variable=self.minimize_to_tray_var, progress_color=OmniTheme.ACCENT_PRIMARY).pack(anchor="w", pady=6)
        ctk.CTkSwitch(sys_box, text="Enable global hotkeys (Ctrl+Alt+D, Ctrl+Alt+M, Ctrl+Alt+C, Ctrl+Alt+R)", variable=self.enable_hotkeys_var, progress_color=OmniTheme.ACCENT_PRIMARY, command=self._toggle_hotkeys).pack(anchor="w", pady=6)

        drive_box = ctk.CTkFrame(card, fg_color="transparent")
        drive_box.pack(fill="x", padx=18, pady=(16, 10))

        ctk.CTkLabel(drive_box, text="Google Drive", font=ctk.CTkFont(size=12, weight="bold"), text_color=OmniTheme.TEXT_MAIN).pack(anchor="w", pady=(4, 6))
        drive_cfg = self.config.get("google_drive", {})

        p_lbl = ctk.CTkLabel(drive_box, text=f"Sync method: {drive_cfg.get('method', 'desktop')}  ·  Path: {self.controller.uploader.desktop_sync_path or 'Not detected'}", font=ctk.CTkFont(size=11), text_color=OmniTheme.TEXT_MUTED)
        p_lbl.pack(anchor="w", pady=4)

        btn_row = ctk.CTkFrame(drive_box, fg_color="transparent")
        btn_row.pack(anchor="w", pady=(8, 12))

        test_auth_btn = ctk.CTkButton(
            btn_row,
            text="Authenticate API",
            font=ctk.CTkFont(size=11),
            fg_color=OmniTheme.BG_INPUT,
            hover_color=OmniTheme.BG_CARD_HOVER,
            corner_radius=OmniTheme.RADIUS_CONTROL,
            command=self._on_test_drive_auth
        )
        test_auth_btn.pack(side="left")

    def _toggle_hotkeys(self):
        if self.enable_hotkeys_var.get():
            self.hotkeys.start()
            self._set_status("Global hotkeys enabled")
        else:
            self.hotkeys.stop()
            self._set_status("Global hotkeys disabled")

    def _on_test_drive_auth(self):
        self._set_status("Authenticating Google Drive")
        def _worker():
            test_file = get_base_dir() / "auth_test.tmp"
            test_file.write_text("OmniCapture Auth Test")
            ok, msg = self.controller.uploader._upload_via_api(test_file)
            if test_file.exists():
                test_file.unlink()
            self.after(0, lambda: self._set_status(f"Google Drive: {msg}"))
        threading.Thread(target=_worker, daemon=True).start()

    # -------------------------------------------------------------------------
    # Layout: Footer
    # -------------------------------------------------------------------------

    def _build_footer(self):
        """Minimal footer bar without period punctuation or clutter."""
        footer_frame = ctk.CTkFrame(self, fg_color=OmniTheme.BG_CARD, height=32, corner_radius=0)
        footer_frame.pack(fill="x", side="bottom")

        self.status_ticker = ctk.CTkLabel(
            footer_frame,
            text="Ready",
            font=ctk.CTkFont(family="Segoe UI", size=11),
            text_color=OmniTheme.TEXT_MUTED
        )
        self.status_ticker.pack(side="left", padx=16)

        hotkey_hint = ctk.CTkLabel(
            footer_frame,
            text="Ctrl+Alt+D: Dual Record  ·  Ctrl+Alt+M: Mirror  ·  Ctrl+Alt+C: Camera  ·  Ctrl+Alt+R: Folder",
            font=ctk.CTkFont(family="Segoe UI", size=10),
            text_color=OmniTheme.TEXT_DIM
        )
        hotkey_hint.pack(side="right", padx=16)

    def _set_status(self, message: str):
        clean_msg = message.rstrip(".")
        self.status_ticker.configure(text=clean_msg)

    # -------------------------------------------------------------------------
    # Device State Updates
    # -------------------------------------------------------------------------

    def _initial_refresh(self):
        self.controller.refresh_device_now()
        self._refresh_gallery_list()
        self._on_run_diagnostics()

    def _on_device_state_changed(self, state: Dict[str, Any]):
        self.after(0, lambda: self._update_device_ui(state))

    def _update_device_ui(self, state: Dict[str, Any]):
        status = state.get("status")
        model = state.get("model", "No Device")
        dev_id = state.get("device_id", "")
        conn_str = "Wi-Fi" if state.get("is_wireless") else "USB"

        if status == "CONNECTED":
            batt = state.get("battery", {})
            lvl = batt.get("level", "")
            batt_str = f" · {lvl}" if lvl and lvl != "N/A" else ""
            self.device_status_lbl.configure(
                text=f"● {model} ({conn_str}){batt_str}",
                text_color=OmniTheme.STATUS_CONNECTED
            )
            ip = state.get("wifi_ip")
            self.wifi_ip_lbl.configure(text=f"IP: {ip}:5555" if ip else f"Connected via {conn_str}")
        elif status == "UNAUTHORIZED":
            self.device_status_lbl.configure(
                text=f"Unauthorized: unlock phone and allow debugging",
                text_color=OmniTheme.STATUS_WARNING
            )
        elif status == "OFFLINE":
            self.device_status_lbl.configure(
                text=f"Device offline: reconnect cable",
                text_color=OmniTheme.STATUS_WARNING
            )
        else:
            self.device_status_lbl.configure(
                text="No device connected",
                text_color=OmniTheme.STATUS_DISCONNECTED
            )
            self.wifi_ip_lbl.configure(text="Device not connected")

    def _on_manual_refresh(self):
        self._set_status("Scanning devices")
        self.controller.refresh_device_now()
        self._refresh_gallery_list()
        self._set_status("Ready")

    def _on_release_lock(self):
        self._set_status("Releasing camera sensor lock")
        ok, msg = self.controller.release_camera_lock()
        self._set_status(msg)
        self.tray.notify("Camera Lock", msg)

    # -------------------------------------------------------------------------
    # Actions: Dual Recording
    # -------------------------------------------------------------------------

    def _on_start_dual_recording(self):
        facing = "back" if "Back" in self.dual_facing_seg.get() else "front"
        pc_fps = 60 if "60" in self.dual_pc_fps_seg.get() else 30
        cam_fps = 60 if "60" in self.dual_cam_fps_seg.get() else 30
        fmt = self.dual_fmt_seg.get().lower()
        preview = self.dual_preview_var.get()
        upload = self.dual_upload_var.get()

        self._set_status("Initializing dual recording")
        self.dual_log_box.insert("end", f"Starting dual recording ({facing} camera, {pc_fps} fps PC, {cam_fps} fps camera)\n")
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
            self.dual_live_card.pack(fill="x", padx=20, pady=(8, 18))
            self._set_status("Recording in progress")
            self.tray.notify("OmniCapture", "Dual recording in progress")
        else:
            self._set_status(f"Recording error: {msg}")
            self.dual_log_box.insert("end", f"Error: {msg}\n")
            self.dual_log_box.see("end")

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

        stats_str = f"PC screen: {_fmt(pc_sz)}  ·  Camera: {_fmt(cam_sz)}"
        self.after(0, lambda: self._update_dual_live_labels(time_str, stats_str))

    def _update_dual_live_labels(self, time_str: str, stats_str: str):
        self.dual_timer_lbl.configure(text=time_str)
        self.dual_stream_stats_lbl.configure(text=stats_str)

    def _on_stop_dual_recording(self):
        self._set_status("Finalizing files")
        self.controller.stop_dual_recording()

    def _on_dual_complete(self, result: Dict[str, Any]):
        def _ui_update():
            self.dual_live_card.pack_forget()
            self.dual_start_btn.pack(anchor="w", ipadx=16)

            status = result.get("status", "UNKNOWN")
            dur_fmt = result.get("duration_formatted", "00:00")
            pc_file = result.get("pc_screen_file")
            cam_file = result.get("mobile_camera_file")

            log_msg = f"\nDual recording completed ({status}, {dur_fmt})\n"
            if pc_file:
                log_msg += f"  PC screen: {pc_file.name} ({result.get('pc_screen_size_formatted')})\n"
            if cam_file:
                log_msg += f"  Camera:    {cam_file.name} ({result.get('mobile_camera_size_formatted')})\n"

            self.dual_log_box.insert("end", log_msg)
            self.dual_log_box.see("end")

            self._set_status(f"Recording finished ({status})")
            self.tray.notify("OmniCapture", f"Recording finished ({status})")
            self._refresh_gallery_list()

        self.after(0, _ui_update)

    # -------------------------------------------------------------------------
    # Actions: Mirror & Camera
    # -------------------------------------------------------------------------

    def _on_launch_mirror(self):
        uhid = "UHID" in self.mirror_mode_seg.get()
        screen_off = self.mirror_screen_off_var.get()
        stay_awake = self.mirror_awake_var.get()
        self._set_status("Launching display mirror")
        ok, msg = self.controller.launch_display_mirror(
            uhid=uhid,
            screen_off=screen_off,
            stay_awake=stay_awake,
            on_exit=lambda code: self.after(0, lambda: self._set_status("Mirror session ended"))
        )
        self._set_status(msg)

    def _on_start_screen_recording(self):
        fmt = self.screen_rec_fmt_seg.get().lower()
        upload = self.screen_rec_upload_var.get()
        self._set_status("Starting screen recording")
        ok, msg = self.controller.record_screen(
            record_format=fmt,
            auto_upload=upload,
            on_complete=lambda path, dur, sz: self.after(0, lambda: self._on_single_rec_complete(path, dur, sz, "Screen"))
        )
        self._set_status(msg)

    def _on_launch_camera_stream(self):
        facing = "back" if "Back" in self.cam_stream_facing_seg.get() else "front"
        mic = self.cam_stream_mic_var.get()
        self._set_status("Launching camera feed")
        ok, msg = self.controller.launch_stealth_camera(
            facing=facing,
            audio_mic=mic,
            on_exit=lambda code: self.after(0, lambda: self._set_status("Camera session ended"))
        )
        self._set_status(msg)

    def _on_start_camera_recording(self):
        facing = "back" if "Back" in self.cam_rec_facing_seg.get() else "front"
        fmt = self.cam_rec_fmt_seg.get().lower()
        preview = self.cam_rec_preview_var.get()
        upload = self.cam_rec_upload_var.get()

        self._set_status("Starting camera recording")
        ok, msg = self.controller.record_camera(
            facing=facing,
            record_format=fmt,
            preview=preview,
            audio_mic=True,
            auto_upload=upload,
            on_complete=lambda path, dur, sz: self.after(0, lambda: self._on_single_rec_complete(path, dur, sz, "Camera"))
        )
        self._set_status(msg)

    def _on_single_rec_complete(self, path: Optional[Path], dur: float, sz: int, mode_name: str):
        if path and sz > 0:
            sz_str = self.controller.recorder.format_size(sz)
            dur_str = self.controller.recorder.format_duration(dur)
            self._set_status(f"Saved: {path.name} ({sz_str})")
            self.tray.notify("OmniCapture", f"Saved: {path.name} ({sz_str})")
            self._refresh_gallery_list()
        else:
            self._set_status(f"{mode_name} recording failed or produced 0 bytes")

    def _on_switch_to_wireless(self):
        self._set_status("Configuring wireless ADB")
        def _worker():
            ok, msg = self.controller.switch_to_wireless_adb()
            self.after(0, lambda: self._set_status(msg))
            self.after(0, lambda: self.tray.notify("Wireless ADB", msg))
        threading.Thread(target=_worker, daemon=True).start()

    def _on_run_diagnostics(self):
        diag = self.controller.query_diagnostics()
        out = (
            f"ADB:    {diag['adb_path']} ({diag['adb_version']})\n"
            f"Scrcpy: {diag['scrcpy_path']}\n"
            f"FFmpeg: {diag['ffmpeg_path']} ({diag['ffmpeg_version']})\n\n"
            f"Sensors:\n{diag['cameras_info']}\n\n"
            f"Resolutions:\n{diag['camera_sizes']}\n"
        )
        self.diag_box.delete("1.0", "end")
        self.diag_box.insert("1.0", out)

    # -------------------------------------------------------------------------
    # Global Hotkey Handlers
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
            self.tabs.set("Dual Recording")
            self._on_start_dual_recording()

    def _on_hotkey_mirror(self):
        self._show_window()
        self.tabs.set("Screen Mirror")
        self._on_launch_mirror()

    def _on_hotkey_camera(self):
        self._show_window()
        self.tabs.set("Camera")
        self._on_launch_camera_stream()

    # -------------------------------------------------------------------------
    # Window & Tray Lifecycle
    # -------------------------------------------------------------------------

    def _show_window(self):
        self.deiconify()
        self.lift()
        self.focus_force()

    def _on_window_close(self):
        if self.minimize_to_tray_var.get():
            self.withdraw()
            self.tray.notify(
                "OmniCapture",
                "OmniCapture is running in the background. Press Ctrl+Alt+D to record or click the tray icon."
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
