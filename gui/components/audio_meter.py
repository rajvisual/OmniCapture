import math
import random
from typing import Optional, Callable
import customtkinter as ctk

from gui.theme import OmniTheme, ThemeTokens

class AudioChannelStrip(ctk.CTkFrame):
    """
    Professional Digital Audio Workstation (DAW) & OBS Studio style Audio Channel Strip.
    Features:
    - 32px control standards, 8px corner radius
    - Channel Name label in Segoe UI Variable
    - Mute button with active visual feedback (distinct red only when muted)
    - Precise Gain Slider with dB numerical readouts (-inf to 0.0 dB)
    - Multi-stage Peak Level VU Meter with green/yellow/red decibel transitions
    """

    def __init__(
        self,
        parent,
        channel_name: str,
        initial_volume: float = 0.85,
        on_volume_change: Optional[Callable[[float], None]] = None,
        on_mute_toggle: Optional[Callable[[bool], None]] = None,
        **kwargs
    ):
        tokens = OmniTheme.get_tokens()
        super().__init__(parent, fg_color="transparent", **kwargs)

        self.channel_name = channel_name
        self.volume = initial_volume
        self.is_muted = False
        self._current_level = 0.0
        self.on_volume_change = on_volume_change
        self.on_mute_toggle = on_mute_toggle

        self._build_ui(tokens)

    def _build_ui(self, tokens: ThemeTokens):
        # Header Row: Channel Name, dB Readout, Mute Button
        header_row = ctk.CTkFrame(self, fg_color="transparent")
        header_row.pack(fill="x", pady=(0, 2))

        self.name_label = ctk.CTkLabel(
            header_row,
            text=self.channel_name,
            font=OmniTheme.font_body_bold(),
            text_color=tokens.text_primary,
            anchor="w"
        )
        self.name_label.pack(side="left")

        self.db_label = ctk.CTkLabel(
            header_row,
            text=self._vol_to_db_str(self.volume),
            font=OmniTheme.font_mono(10),
            text_color=tokens.text_muted
        )
        self.db_label.pack(side="right", padx=(4, 0))

        self.mute_btn = ctk.CTkButton(
            header_row,
            text="Mute",
            width=48,
            height=24,
            font=OmniTheme.font_caption(),
            fg_color=tokens.bg_input,
            hover_color=tokens.bg_hover,
            text_color=tokens.text_secondary,
            border_width=1,
            border_color=tokens.border_subtle,
            corner_radius=OmniTheme.RADIUS_CONTROL,
            command=self._toggle_mute
        )
        self.mute_btn.pack(side="right", padx=(4, 4))

        # Slider Row: 32px height container
        slider_row = ctk.CTkFrame(self, fg_color="transparent", height=20)
        slider_row.pack(fill="x", pady=(2, 2))

        self.slider = ctk.CTkSlider(
            slider_row,
            from_=0.0,
            to=1.0,
            number_of_steps=100,
            height=10,
            progress_color=tokens.accent_primary,
            button_color=tokens.text_primary,
            button_hover_color=tokens.accent_hover,
            button_length=12,
            corner_radius=4,
            command=self._on_slider_moved
        )
        self.slider.set(self.volume)
        self.slider.pack(fill="x")

        # Meter Row: Multi-segment VU Level Bar
        self.meter_container = ctk.CTkFrame(
            self,
            fg_color=tokens.vu_bg,
            height=4,
            corner_radius=2
        )
        self.meter_container.pack(fill="x", pady=(2, 4))
        self.meter_container.pack_propagate(False)

        self.meter_bar = ctk.CTkProgressBar(
            self.meter_container,
            height=4,
            corner_radius=2,
            progress_color=tokens.vu_green,
            fg_color=tokens.vu_bg
        )
        self.meter_bar.pack(fill="both", expand=True)
        self.meter_bar.set(0.0)

    def _vol_to_db_str(self, val: float) -> str:
        if val <= 0.001:
            return "-inf dB"
        db = 20.0 * math.log10(max(val, 0.01))
        return f"{db:.1f} dB"

    def _on_slider_moved(self, val: float):
        self.volume = val
        if not self.is_muted:
            self.db_label.configure(text=self._vol_to_db_str(val))
        if self.on_volume_change:
            self.on_volume_change(val if not self.is_muted else 0.0)

    def _toggle_mute(self):
        self.is_muted = not self.is_muted
        tokens = OmniTheme.get_tokens()
        if self.is_muted:
            self.mute_btn.configure(
                text="Muted",
                fg_color=tokens.status_recording,
                hover_color=tokens.status_recording_hover,
                text_color=tokens.text_primary if not tokens.is_dark else "#FFFFFF",
                border_color=tokens.status_recording
            )
            self.db_label.configure(text="Muted", text_color=tokens.status_recording)
            self.meter_bar.set(0.0)
            self._current_level = 0.0
        else:
            self.mute_btn.configure(
                text="Mute",
                fg_color=tokens.bg_input,
                hover_color=tokens.bg_hover,
                text_color=tokens.text_secondary,
                border_color=tokens.border_subtle
            )
            self.db_label.configure(text=self._vol_to_db_str(self.volume), text_color=tokens.text_muted)

        if self.on_mute_toggle:
            self.on_mute_toggle(self.is_muted)

    def set_level(self, level: float):
        """Update live audio level (0.0 to 1.0) with smooth dynamic color transitions."""
        if self.is_muted:
            if self._current_level != 0.0:
                self._current_level = 0.0
                self.meter_bar.set(0.0)
            return

        level = max(0.0, min(1.0, level * self.volume))
        if abs(level - self._current_level) < 0.005 and level == 0.0:
            return
        self._current_level = level
        self.meter_bar.set(level)

        tokens = OmniTheme.get_tokens()
        if level > 0.85:
            self.meter_bar.configure(progress_color=tokens.vu_red)
        elif level > 0.65:
            self.meter_bar.configure(progress_color=tokens.vu_yellow)
        else:
            self.meter_bar.configure(progress_color=tokens.vu_green)

    def simulate_audio_activity(self, active: bool = True):
        """Simulate realistic ambient room audio levels for preview and recording telemetry."""
        if not active or self.is_muted:
            self.set_level(0.0)
            return

        base = random.uniform(0.12, 0.48)
        if random.random() > 0.75:
            base += random.uniform(0.15, 0.35)
        self.set_level(base)

    def apply_tokens(self, tokens: ThemeTokens):
        """Update component colors on runtime theme switch."""
        self.name_label.configure(text_color=tokens.text_primary)
        if not self.is_muted:
            self.db_label.configure(text_color=tokens.text_muted)
            self.mute_btn.configure(
                fg_color=tokens.bg_input,
                hover_color=tokens.bg_hover,
                text_color=tokens.text_secondary,
                border_color=tokens.border_subtle
            )
        else:
            self.mute_btn.configure(
                fg_color=tokens.status_recording,
                hover_color=tokens.status_recording_hover,
                border_color=tokens.status_recording
            )
            self.db_label.configure(text_color=tokens.status_recording)

        self.slider.configure(
            progress_color=tokens.accent_primary,
            button_color=tokens.text_primary,
            button_hover_color=tokens.accent_hover
        )
        self.meter_container.configure(fg_color=tokens.vu_bg)
        self.meter_bar.configure(fg_color=tokens.vu_bg)
