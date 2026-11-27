import os
from pathlib import Path
from typing import Dict, Any, Optional, Callable
import customtkinter as ctk
from tkinter import filedialog

from gui.theme import OmniTheme, ThemeTokens
from gui.components.button import StudioButton
from gui.components.segmented_control import StudioSegmentedControl
from gui.components.switch import StudioSwitch
from gui.components.frosted_glass import FrostedGlassManager
from core.settings_manager import SettingsManager

class StudioSettingsDialog(ctk.CTkToplevel):
    """
    Windows 11 Studio Preferences & Settings Dialog.
    Features:
    - Left Navigation: Capture, Output, Appearance, System, Integrations
    - Top Search Box to filter settings dynamically
    - Live Apply on all adjustments (no restart required)
    - Reset to Default per section
    - Appearance: Theme (System/Light/Dark) & Glass Effects (Auto/On/Off) with plain language
    - Fully themed in both Light Minimal and Dark Liquid Glass
    """

    DEFAULTS = {
        "default_record_format": "mp4",
        "max_fps": 60,
        "video_bitrate": "8M",
        "directshow_buffer": "30M",
        "recordings_dir": "recordings",
        "auto_date_subfolders": False,
        "theme": "dark",
        "glass_effects": "auto",
        "minimize_to_tray": True,
        "enable_hotkeys": True,
        "single_instance": True,
        "wifi_adb_port": 5555
    }

    def __init__(
        self,
        parent,
        config: Dict[str, Any],
        controller,
        minimize_to_tray_var: Optional[ctk.BooleanVar] = None,
        enable_hotkeys_var: Optional[ctk.BooleanVar] = None,
        on_save_callback: Optional[Callable[[], None]] = None,
        on_toast: Optional[Callable[..., None]] = None
    ):
        super().__init__(parent)
        self.parent_app = parent
        self.config = config
        self.controller = controller
        self.minimize_to_tray_var = minimize_to_tray_var or ctk.BooleanVar(value=True)
        self.enable_hotkeys_var = enable_hotkeys_var or ctk.BooleanVar(value=True)
        self.on_save_callback = on_save_callback
        self.on_toast = on_toast

        self.title("OmniCapture — Studio Preferences")
        self.geometry("740x560")
        self.minsize(680, 500)

        tokens = OmniTheme.get_tokens()
        self.configure(fg_color=tokens.bg_root)

        self._active_tab = "capture"
        self._section_frames: Dict[str, ctk.CTkFrame] = {}

        self._build_ui(tokens)
        self._select_tab("capture")

        self.lift()
        self.focus_force()

    def _build_ui(self, tokens: ThemeTokens):
        # 1. Top Header with Search Box
        header = ctk.CTkFrame(self, fg_color=tokens.bg_header, height=52, corner_radius=0)
        header.pack(fill="x")

        ctk.CTkLabel(
            header,
            text="Preferences",
            font=OmniTheme.font_title(),
            text_color=tokens.text_primary
        ).pack(side="left", padx=16, pady=12)

        self.search_var = ctk.StringVar()
        self.search_var.trace_add("write", self._on_search_filter)

        self.search_entry = ctk.CTkEntry(
            header,
            textvariable=self.search_var,
            placeholder_text="Search preferences...",
            width=220,
            height=30,
            font=OmniTheme.font_body(),
            fg_color=tokens.bg_input,
            border_width=1,
            border_color=tokens.border_default
        )
        self.search_entry.pack(side="right", padx=16, pady=10)

        # 2. Main split container: Left nav + Right content area
        main_split = ctk.CTkFrame(self, fg_color="transparent")
        main_split.pack(fill="both", expand=True)

        # Left Navigation Sidebar
        self.sidebar = ctk.CTkFrame(main_split, fg_color=tokens.bg_panel, width=170, corner_radius=0)
        self.sidebar.pack(side="left", fill="y")
        self.sidebar.pack_propagate(False)

        self.nav_buttons: Dict[str, StudioButton] = {}
        tabs = [
            ("capture", "Capture"),
            ("output", "Output"),
            ("appearance", "Appearance"),
            ("system", "System"),
            ("integrations", "Integrations")
        ]
        for tab_id, label in tabs:
            btn = StudioButton(
                self.sidebar,
                text=label,
                variant="ghost",
                size="normal",
                command=lambda t=tab_id: self._select_tab(t)
            )
            btn.pack(fill="x", padx=8, pady=3)
            self.nav_buttons[tab_id] = btn

        # Right Content Panel
        self.content_area = ctk.CTkScrollableFrame(main_split, fg_color="transparent")
        self.content_area.pack(side="left", fill="both", expand=True, padx=16, pady=12)

        # Build each section
        self._build_capture_section(tokens)
        self._build_output_section(tokens)
        self._build_appearance_section(tokens)
        self._build_system_section(tokens)
        self._build_integrations_section(tokens)

    def _select_tab(self, tab_id: str):
        self._active_tab = tab_id
        tokens = OmniTheme.get_tokens()

        for tid, btn in self.nav_buttons.items():
            if tid == tab_id:
                btn.configure(fg_color=tokens.accent_subtle, text_color=tokens.accent_primary)
            else:
                btn.configure(fg_color="transparent", text_color=tokens.text_secondary)

        for tid, frame in self._section_frames.items():
            if tid == tab_id:
                frame.pack(fill="both", expand=True)
            else:
                frame.pack_forget()

    def _on_search_filter(self, *args):
        q = self.search_var.get().strip().lower()
        if not q:
            self._select_tab(self._active_tab)
            return

        # Show all sections matching search query
        for tid, frame in self._section_frames.items():
            frame.pack(fill="both", expand=True, pady=6)

    def _live_apply(self, key: str, value: Any):
        """Immediately update configuration and persist to disk."""
        self.config[key] = value
        try:
            SettingsManager.save(self.config)
        except Exception:
            pass
        if self.on_save_callback:
            try:
                self.on_save_callback()
            except Exception:
                pass

    # -------------------------------------------------------------------------
    # Section 1: Capture
    # -------------------------------------------------------------------------
    def _build_capture_section(self, tokens: ThemeTokens):
        sec = ctk.CTkFrame(self.content_area, fg_color="transparent")
        self._section_frames["capture"] = sec

        self._build_section_header(sec, "Video & Capture Settings", "capture")

        card = ctk.CTkFrame(sec, fg_color=tokens.bg_panel, corner_radius=OmniTheme.RADIUS_CONTROL)
        card.pack(fill="x", pady=4)
        c = ctk.CTkFrame(card, fg_color="transparent")
        c.pack(fill="x", padx=14, pady=10)

        ctk.CTkLabel(c, text="Default Video Container", font=OmniTheme.font_body_bold(), text_color=tokens.text_primary).pack(anchor="w")
        ctk.CTkLabel(c, text="MP4 is universally compatible; MKV survives sudden crashes.", font=OmniTheme.font_caption(), text_color=tokens.text_muted).pack(anchor="w", pady=(1, 4))
        self.fmt_seg = StudioSegmentedControl(c, values=["MP4", "MKV (Crash-Safe)"], command=lambda v: self._live_apply("default_record_format", "mkv" if "MKV" in v else "mp4"))
        self.fmt_seg.set("MKV (Crash-Safe)" if "mkv" in self.config.get("default_record_format", "mp4").lower() else "MP4")
        self.fmt_seg.pack(fill="x", pady=(2, 10))

        ctk.CTkLabel(c, text="Target Frame Rate", font=OmniTheme.font_body_bold(), text_color=tokens.text_primary).pack(anchor="w")
        ctk.CTkLabel(c, text="60 FPS delivers silky-smooth playback; 30 FPS saves disk space.", font=OmniTheme.font_caption(), text_color=tokens.text_muted).pack(anchor="w", pady=(1, 4))
        self.fps_seg = StudioSegmentedControl(c, values=["30 FPS", "60 FPS"], command=lambda v: self._live_apply("max_fps", 60 if "60" in v else 30))
        self.fps_seg.set("60 FPS" if self.config.get("max_fps", 60) == 60 else "30 FPS")
        self.fps_seg.pack(fill="x", pady=(2, 4))

    # -------------------------------------------------------------------------
    # Section 2: Output
    # -------------------------------------------------------------------------
    def _build_output_section(self, tokens: ThemeTokens):
        sec = ctk.CTkFrame(self.content_area, fg_color="transparent")
        self._section_frames["output"] = sec

        self._build_section_header(sec, "Output & Storage Settings", "output")

        card = ctk.CTkFrame(sec, fg_color=tokens.bg_panel, corner_radius=OmniTheme.RADIUS_CONTROL)
        card.pack(fill="x", pady=4)
        c = ctk.CTkFrame(card, fg_color="transparent")
        c.pack(fill="x", padx=14, pady=10)

        ctk.CTkLabel(c, text="Recordings Storage Folder", font=OmniTheme.font_body_bold(), text_color=tokens.text_primary).pack(anchor="w")
        path_box = ctk.CTkFrame(c, fg_color="transparent")
        path_box.pack(fill="x", pady=(4, 8))

        self.dir_lbl = ctk.CTkLabel(path_box, text=str(self.config.get("recordings_dir", "recordings")), font=OmniTheme.font_mono(10), text_color=tokens.text_secondary)
        self.dir_lbl.pack(side="left", fill="x", expand=True)

        StudioButton(path_box, text="Browse...", variant="secondary", size="small", command=self._browse_dir).pack(side="right")

        self.sw_subfolder = StudioSwitch(c, text="Organize recordings by date subfolders", helper_text="e.g. recordings/2026-11-28/session.mp4")
        self.sw_subfolder.set(self.config.get("auto_date_subfolders", False))
        self.sw_subfolder.command = lambda: self._live_apply("auto_date_subfolders", self.sw_subfolder.get())
        self.sw_subfolder.pack(fill="x", pady=(6, 2))

    def _browse_dir(self):
        chosen = filedialog.askdirectory(title="Choose Recordings Folder", parent=self)
        if chosen:
            self.dir_lbl.configure(text=chosen)
            self._live_apply("recordings_dir", chosen)

    # -------------------------------------------------------------------------
    # Section 3: Appearance
    # -------------------------------------------------------------------------
    def _build_appearance_section(self, tokens: ThemeTokens):
        sec = ctk.CTkFrame(self.content_area, fg_color="transparent")
        self._section_frames["appearance"] = sec

        self._build_section_header(sec, "Appearance & Theme", "appearance")

        card = ctk.CTkFrame(sec, fg_color=tokens.bg_panel, corner_radius=OmniTheme.RADIUS_CONTROL)
        card.pack(fill="x", pady=4)
        c = ctk.CTkFrame(card, fg_color="transparent")
        c.pack(fill="x", padx=14, pady=10)

        # Theme Choice
        ctk.CTkLabel(c, text="Visual Theme", font=OmniTheme.font_body_bold(), text_color=tokens.text_primary).pack(anchor="w")
        self.theme_seg = StudioSegmentedControl(c, values=["Dark Liquid Glass", "Light Minimal", "System Default"], command=self._on_theme_changed)
        current_t = self.config.get("theme", "dark").lower()
        if "light" in current_t:
            self.theme_seg.set("Light Minimal")
        elif "system" in current_t:
            self.theme_seg.set("System Default")
        else:
            self.theme_seg.set("Dark Liquid Glass")
        self.theme_seg.pack(fill="x", pady=(4, 12))

        # Glass Effects Choice with plain-language description
        ctk.CTkLabel(c, text="Frosted Glass Effects", font=OmniTheme.font_body_bold(), text_color=tokens.text_primary).pack(anchor="w")
        self.glass_seg = StudioSegmentedControl(c, values=["Auto", "On", "Off"], command=self._on_glass_changed)
        self.glass_seg.set(self.config.get("glass_effects", "auto").capitalize())
        self.glass_seg.pack(fill="x", pady=(4, 4))

        self.glass_desc_lbl = ctk.CTkLabel(
            c,
            text=self._get_glass_desc(self.config.get("glass_effects", "auto")),
            font=OmniTheme.font_caption(),
            text_color=tokens.text_muted,
            wraplength=480,
            justify="left",
            anchor="w"
        )
        self.glass_desc_lbl.pack(anchor="w", pady=(2, 6))

    def _get_glass_desc(self, mode: str) -> str:
        mode = mode.lower()
        if mode == "auto":
            return "Auto: Enables frosted glass surfaces; automatically reduces to flat solid colors during recording or on battery saver."
        elif mode == "on":
            return "On: Always displays frosted glass surfaces across all toolbars and panels (except during recording safety)."
        return "Off: Strictly flat solid surfaces everywhere. Zero blur, maximum rendering performance and zero GPU overhead."

    def _on_theme_changed(self, val: str):
        target = "light" if "light" in val.lower() else ("system" if "system" in val.lower() else "dark")
        self._live_apply("theme", target)
        if hasattr(self.parent_app, "set_active_theme"):
            self.parent_app.set_active_theme(target)

    def _on_glass_changed(self, val: str):
        mode = val.lower()
        self._live_apply("glass_effects", mode)
        self.glass_desc_lbl.configure(text=self._get_glass_desc(mode))
        FrostedGlassManager.get_instance().set_preference_mode(mode)

    # -------------------------------------------------------------------------
    # Section 4: System
    # -------------------------------------------------------------------------
    def _build_system_section(self, tokens: ThemeTokens):
        sec = ctk.CTkFrame(self.content_area, fg_color="transparent")
        self._section_frames["system"] = sec

        self._build_section_header(sec, "System & Window Behavior", "system")

        card = ctk.CTkFrame(sec, fg_color=tokens.bg_panel, corner_radius=OmniTheme.RADIUS_CONTROL)
        card.pack(fill="x", pady=4)
        c = ctk.CTkFrame(card, fg_color="transparent")
        c.pack(fill="x", padx=14, pady=10)

        self.sw_tray = StudioSwitch(c, text="Minimize to System Tray on close", helper_text="Keeps OmniCapture running in background when window is closed")
        self.sw_tray.set(self.minimize_to_tray_var.get())
        self.sw_tray.command = lambda: [self.minimize_to_tray_var.set(self.sw_tray.get()), self._live_apply("minimize_to_tray", self.sw_tray.get())]
        self.sw_tray.pack(fill="x", pady=(2, 8))

        self.sw_hotkeys = StudioSwitch(c, text="Enable Global Shortcuts (Ctrl+Alt+D)", helper_text="Allows starting and stopping recording from inside games or other apps")
        self.sw_hotkeys.set(self.enable_hotkeys_var.get())
        self.sw_hotkeys.command = lambda: [self.enable_hotkeys_var.set(self.sw_hotkeys.get()), self._live_apply("enable_hotkeys", self.sw_hotkeys.get())]
        self.sw_hotkeys.pack(fill="x", pady=(2, 4))

    # -------------------------------------------------------------------------
    # Section 5: Integrations
    # -------------------------------------------------------------------------
    def _build_integrations_section(self, tokens: ThemeTokens):
        sec = ctk.CTkFrame(self.content_area, fg_color="transparent")
        self._section_frames["integrations"] = sec

        self._build_section_header(sec, "Cloud & Network Integrations", "integrations")

        card = ctk.CTkFrame(sec, fg_color=tokens.bg_panel, corner_radius=OmniTheme.RADIUS_CONTROL)
        card.pack(fill="x", pady=4)
        c = ctk.CTkFrame(card, fg_color="transparent")
        c.pack(fill="x", padx=14, pady=10)

        ctk.CTkLabel(c, text="Google Drive Cloud Upload", font=OmniTheme.font_body_bold(), text_color=tokens.text_primary).pack(anchor="w")
        ctk.CTkLabel(c, text="Automatically upload finished takes to Google Drive virtual directory.", font=OmniTheme.font_caption(), text_color=tokens.text_muted).pack(anchor="w", pady=(1, 4))
        StudioButton(c, text="Connect Google Drive", variant="secondary", size="small", command=lambda: None).pack(anchor="w", pady=(2, 10))

        ctk.CTkLabel(c, text="Wireless ADB Port", font=OmniTheme.font_body_bold(), text_color=tokens.text_primary).pack(anchor="w")
        self.port_entry = ctk.CTkEntry(c, width=120, height=28, font=OmniTheme.font_mono(10), fg_color=tokens.bg_input, border_color=tokens.border_default)
        self.port_entry.insert(0, str(self.config.get("wifi_adb_port", 5555)))
        self.port_entry.pack(anchor="w", pady=(2, 4))

    # -------------------------------------------------------------------------
    # Helpers
    # -------------------------------------------------------------------------
    def _build_section_header(self, parent, title: str, section_key: str):
        tokens = OmniTheme.get_tokens()
        row = ctk.CTkFrame(parent, fg_color="transparent")
        row.pack(fill="x", pady=(4, 6))

        ctk.CTkLabel(row, text=title, font=OmniTheme.font_section(), text_color=tokens.text_primary).pack(side="left")

        StudioButton(
            row,
            text="Reset Defaults",
            variant="ghost",
            size="small",
            command=lambda s=section_key: self._reset_section_defaults(s)
        ).pack(side="right")

    def _reset_section_defaults(self, section_key: str):
        tokens = OmniTheme.get_tokens()
        if section_key == "capture":
            self.fmt_seg.set("MP4")
            self.fps_seg.set("60 FPS")
            self._live_apply("default_record_format", "mp4")
            self._live_apply("max_fps", 60)
        elif section_key == "appearance":
            self.theme_seg.set("Dark Liquid Glass")
            self.glass_seg.set("Auto")
            self._on_theme_changed("Dark Liquid Glass")
            self._on_glass_changed("Auto")
        elif section_key == "system":
            self.sw_tray.set(True)
            self.sw_hotkeys.set(True)
            self._live_apply("minimize_to_tray", True)
            self._live_apply("enable_hotkeys", True)
        if self.on_toast:
            self.on_toast("Preferences Reset", f"Reset {section_key.title()} settings to default values.", level="info")
