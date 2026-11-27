import sys
import tkinter as tk
from typing import Optional
import customtkinter as ctk

from gui.theme import OmniTheme, ThemeTokens
from gui.components import (
    StudioButton,
    StudioSegmentedControl,
    StudioSwitch,
    SourceRow,
    SceneListItem,
    StudioGainSlider,
    StudioAudioMeterCanvas,
    AudioChannelStrip,
    StatusChip,
    SectionHeader,
    Divider,
    InputField,
    Tooltip,
    get_icon
)

class ComponentGalleryWindow(ctk.CTkToplevel):
    """
    Developer-Only Design System Component Gallery.
    Displays every state of every component in the shared design system.
    Supports real-time theme toggling (Dark Liquid Glass <-> Light Minimal)
    and reports live DPI scaling.
    """

    def __init__(self, parent=None):
        super().__init__(parent)

        self.title("OmniCapture Design System — Component Gallery")
        self.geometry("960x820")
        self.minsize(800, 600)

        tokens = OmniTheme.get_tokens()
        self.configure(fg_color=tokens.bg_root)

        # Register theme listener so gallery re-styles in real-time
        OmniTheme.register_listener(self._on_theme_changed)

        self._build_ui(tokens)
        self.lift()
        self.focus_force()

    def _build_ui(self, tokens: ThemeTokens):
        # 1. Header with live theme toggle and DPI badge
        header = ctk.CTkFrame(self, fg_color=tokens.bg_header, height=52, corner_radius=0)
        header.pack(fill="x")
        header.pack_propagate(False)

        ctk.CTkLabel(
            header,
            text="Component Gallery",
            font=OmniTheme.font_headline(),
            text_color=tokens.text_primary
        ).pack(side="left", padx=20, pady=12)

        # DPI Readout
        dpi_scale = self._get_dpi_scale()
        self.dpi_lbl = ctk.CTkLabel(
            header,
            text=f"DPI: {int(dpi_scale * 100)}% ({int(dpi_scale * 96)} DPI)",
            font=OmniTheme.font_mono(11),
            text_color=tokens.text_dim,
            fg_color=tokens.bg_input,
            corner_radius=4,
            padx=8,
            pady=2
        )
        self.dpi_lbl.pack(side="left", padx=12, pady=12)

        # Theme Segmented Switch
        self.theme_seg = StudioSegmentedControl(
            header,
            values=["Dark Liquid Glass", "Light Minimal"],
            command=self._on_theme_seg_toggle
        )
        self.theme_seg.set("Dark Liquid Glass" if tokens.is_dark else "Light Minimal")
        self.theme_seg.pack(side="right", padx=20, pady=10)

        # 2. Main Scrollable Showcase
        self.scroll = ctk.CTkScrollableFrame(self, fg_color="transparent")
        self.scroll.pack(fill="both", expand=True, padx=20, pady=12)

        self._build_buttons_section(tokens)
        self._build_segmented_section(tokens)
        self._build_form_controls_section(tokens)
        self._build_sources_and_scenes_section(tokens)
        self._build_audio_section(tokens)
        self._build_status_chips_section(tokens)
        self._build_icons_section(tokens)

    def _get_dpi_scale(self) -> float:
        try:
            return self.winfo_fpixels('1i') / 96.0
        except Exception:
            return 1.0

    def _on_theme_seg_toggle(self, val: str):
        target = "dark" if "Dark" in val else "light"
        OmniTheme.set_theme(target)

    def _on_theme_changed(self, tokens: ThemeTokens):
        self.configure(fg_color=tokens.bg_root)
        # Recursively update all gallery widgets
        self._walk_and_apply(self, tokens)

    def _walk_and_apply(self, widget, tokens: ThemeTokens):
        if hasattr(widget, "apply_tokens"):
            try:
                widget.apply_tokens(tokens)
            except Exception:
                pass
        for child in widget.winfo_children():
            self._walk_and_apply(child, tokens)

    # -------------------------------------------------------------------------
    # Gallery Showcase Sections
    # -------------------------------------------------------------------------

    def _build_buttons_section(self, tokens: ThemeTokens):
        SectionHeader(self.scroll, "Buttons & Action States", badge_text="6 variants").pack(fill="x", pady=(8, 4))

        card = ctk.CTkFrame(self.scroll, fg_color=tokens.bg_panel, corner_radius=OmniTheme.RADIUS_CARD)
        card.pack(fill="x", pady=4)

        row = ctk.CTkFrame(card, fg_color="transparent")
        row.pack(fill="x", padx=16, pady=14)

        # Master Record (44px)
        StudioButton(row, text="Start Recording", variant="primary", size="large", icon=get_icon("record")).pack(side="left", padx=6)
        # Danger Active (44px)
        StudioButton(row, text="Stop Recording", variant="danger", size="large", icon=get_icon("stop")).pack(side="left", padx=6)
        # Secondary (32px)
        StudioButton(row, text="Secondary", variant="secondary").pack(side="left", padx=6)
        # Ghost (32px)
        StudioButton(row, text="Ghost", variant="ghost").pack(side="left", padx=6)
        # Icon Only (32px)
        StudioButton(row, text="", variant="icon", icon=get_icon("settings"), disabled_reason="Configure studio hardware settings").pack(side="left", padx=6)
        # Disabled with Tooltip
        StudioButton(row, text="Disabled", variant="secondary", disabled_reason="Requires active Android USB connection").set_disabled(True, "Requires active Android USB connection")

    def _build_segmented_section(self, tokens: ThemeTokens):
        SectionHeader(self.scroll, "Segmented Controls & Navigation", badge_text="32px · Arrow Keys").pack(fill="x", pady=(16, 4))

        card = ctk.CTkFrame(self.scroll, fg_color=tokens.bg_panel, corner_radius=OmniTheme.RADIUS_CARD)
        card.pack(fill="x", pady=4)

        row = ctk.CTkFrame(card, fg_color="transparent")
        row.pack(fill="x", padx=16, pady=14)

        col1 = ctk.CTkFrame(row, fg_color="transparent")
        col1.pack(side="left", fill="x", expand=True, padx=8)
        ctk.CTkLabel(col1, text="Aspect Ratio Toggle", font=OmniTheme.font_caption(), text_color=tokens.text_muted).pack(anchor="w")
        seg1 = StudioSegmentedControl(col1, values=["16:9", "9:16", "Fit Window"])
        seg1.set("16:9")
        seg1.pack(fill="x", pady=4)

        col2 = ctk.CTkFrame(row, fg_color="transparent")
        col2.pack(side="left", fill="x", expand=True, padx=8)
        ctk.CTkLabel(col2, text="Video Container Format", font=OmniTheme.font_caption(), text_color=tokens.text_muted).pack(anchor="w")
        seg2 = StudioSegmentedControl(col2, values=["MP4", "MKV (Crash-Safe)"])
        seg2.set("MP4")
        seg2.pack(fill="x", pady=4)

    def _build_form_controls_section(self, tokens: ThemeTokens):
        SectionHeader(self.scroll, "Switches & Form Inputs", badge_text="Focus Rings").pack(fill="x", pady=(16, 4))

        card = ctk.CTkFrame(self.scroll, fg_color=tokens.bg_panel, corner_radius=OmniTheme.RADIUS_CARD)
        card.pack(fill="x", pady=4)

        col = ctk.CTkFrame(card, fg_color="transparent")
        col.pack(fill="x", padx=16, pady=14)

        StudioSwitch(
            col,
            text="Turn mobile screen off during capture",
            helper_text="Reduces phone thermal throttling and battery consumption significantly"
        ).pack(fill="x", pady=4)

        StudioSwitch(
            col,
            text="Google Drive auto-sync virtual storage",
            helper_text="Instant sync to G:\\My Drive\\OmniCapture on recording complete"
        ).pack(fill="x", pady=4)

        Divider(col).pack(fill="x", pady=10)

        ctk.CTkLabel(col, text="Recording Output Path", font=OmniTheme.font_caption(), text_color=tokens.text_muted).pack(anchor="w")
        InputField(col, placeholder="C:\\Users\\User\\Videos\\OmniCapture").pack(fill="x", pady=(4, 2))

    def _build_sources_and_scenes_section(self, tokens: ThemeTokens):
        SectionHeader(self.scroll, "Dock List Elements (Scenes & Sources)", badge_text="Inline Edit · Eye Toggle").pack(fill="x", pady=(16, 4))

        card = ctk.CTkFrame(self.scroll, fg_color=tokens.bg_panel, corner_radius=OmniTheme.RADIUS_CARD)
        card.pack(fill="x", pady=4)

        row = ctk.CTkFrame(card, fg_color="transparent")
        row.pack(fill="x", padx=16, pady=14)

        col_scenes = ctk.CTkFrame(row, fg_color="transparent")
        col_scenes.pack(side="left", fill="both", expand=True, padx=8)
        ctk.CTkLabel(col_scenes, text="Scenes List (Double-click to rename)", font=OmniTheme.font_caption(), text_color=tokens.text_muted).pack(anchor="w")
        SceneListItem(col_scenes, scene_id="s1", number=1, title="Dual Recording (Active)", is_active=True).pack(fill="x", pady=2)
        SceneListItem(col_scenes, scene_id="s2", number=2, title="Android Display Mirror", is_active=False).pack(fill="x", pady=2)
        SceneListItem(col_scenes, scene_id="s3", number=3, title="Raw Camera2 Viewfinder", is_active=False).pack(fill="x", pady=2)

        col_sources = ctk.CTkFrame(row, fg_color="transparent")
        col_sources.pack(side="left", fill="both", expand=True, padx=8)
        ctk.CTkLabel(col_sources, text="Sources Rows (Eye toggle + status dot)", font=OmniTheme.font_caption(), text_color=tokens.text_muted).pack(anchor="w")
        SourceRow(col_sources, name="PC Screen Capture", initial_checked=True, initial_active=True).pack(fill="x", pady=2)
        SourceRow(col_sources, name="Mobile Camera Feed", initial_checked=True, initial_active=True).pack(fill="x", pady=2)
        SourceRow(col_sources, name="UHID Touch Mouse", initial_checked=False, initial_active=False).pack(fill="x", pady=2)

    def _build_audio_section(self, tokens: ThemeTokens):
        SectionHeader(self.scroll, "DAW Audio Channel Strips", badge_text="Ballistics · Peak-Hold · Clip").pack(fill="x", pady=(16, 4))

        card = ctk.CTkFrame(self.scroll, fg_color=tokens.bg_panel, corner_radius=OmniTheme.RADIUS_CARD)
        card.pack(fill="x", pady=4)

        col = ctk.CTkFrame(card, fg_color="transparent")
        col.pack(fill="x", padx=16, pady=14)

        strip = AudioChannelStrip(col, channel_name="Desktop Audio (Stereo Mix)", initial_volume=0.85)
        strip.pack(fill="x", pady=4)
        strip.set_level(0.72)

        strip2 = AudioChannelStrip(col, channel_name="Microphone (Audio-Technica AT2020)", initial_volume=0.75)
        strip2.pack(fill="x", pady=4)
        strip2.set_level(0.45)

    def _build_status_chips_section(self, tokens: ThemeTokens):
        SectionHeader(self.scroll, "Status Chips & Telemetry Badges", badge_text="Semantic Tokens").pack(fill="x", pady=(16, 4))

        card = ctk.CTkFrame(self.scroll, fg_color=tokens.bg_panel, corner_radius=OmniTheme.RADIUS_CARD)
        card.pack(fill="x", pady=4)

        row = ctk.CTkFrame(card, fg_color="transparent")
        row.pack(fill="x", padx=16, pady=14)

        StatusChip(row, text="Studio Ready", state="ready").pack(side="left", padx=6)
        StatusChip(row, text="REC 00:04:12", state="recording").pack(side="left", padx=6)
        StatusChip(row, text="Low Disk Space", state="warning").pack(side="left", padx=6)
        StatusChip(row, text="Galaxy S20 USB", state="connected").pack(side="left", padx=6)
        StatusChip(row, text="Uploading to Drive", state="uploading").pack(side="left", padx=6)
        StatusChip(row, text="Disconnected", state="disconnected").pack(side="left", padx=6)

    def _build_icons_section(self, tokens: ThemeTokens):
        SectionHeader(self.scroll, "Vector Icon Library (16px Native)", badge_text="19 Icons · High DPI").pack(fill="x", pady=(16, 4))

        card = ctk.CTkFrame(self.scroll, fg_color=tokens.bg_panel, corner_radius=OmniTheme.RADIUS_CARD)
        card.pack(fill="x", pady=4)

        grid = ctk.CTkFrame(card, fg_color="transparent")
        grid.pack(fill="x", padx=16, pady=14)

        icon_list = [
            ("monitor", "Monitor"), ("camera", "Camera"), ("mic", "Microphone"), ("speaker", "Speaker"),
            ("record", "Record"), ("stop", "Stop"), ("folder", "Folder"), ("settings", "Settings"),
            ("refresh", "Refresh"), ("close", "Close"), ("search", "Search"), ("eye", "Eye Open"),
            ("eye_closed", "Eye Closed"), ("lock", "Lock"), ("wifi", "Wi-Fi"), ("usb", "USB"),
            ("battery", "Battery"), ("chevron_down", "Chevron Down"), ("chevron_right", "Chevron Right")
        ]

        for i, (name, lbl) in enumerate(icon_list):
            r = i // 7
            c = i % 7
            box = ctk.CTkFrame(grid, fg_color=tokens.bg_input, corner_radius=4, width=110, height=36)
            box.grid(row=r, column=c, padx=4, pady=4, sticky="nsew")
            box.pack_propagate(False)

            ctk.CTkLabel(box, text="", image=get_icon(name)).pack(side="left", padx=(8, 4))
            ctk.CTkLabel(box, text=lbl, font=OmniTheme.font_caption(), text_color=tokens.text_primary).pack(side="left", padx=(0, 6))

    def destroy(self):
        OmniTheme.unregister_listener(self._on_theme_changed)
        super().destroy()
