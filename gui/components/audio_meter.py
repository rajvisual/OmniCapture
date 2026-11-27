import math
import random
from typing import Optional, Callable
import customtkinter as ctk

from gui.theme import OmniTheme

class AudioChannelStrip(ctk.CTkFrame):
    """
    Professional Digital Audio Workstation (DAW) & OBS Studio style Audio Channel Strip.
    Features:
    - Channel Label and Source identifier
    - Mute button with active visual state
    - Precise Gain Slider with dB numerical readouts
    - Segmented Peak Level VU Meter with realistic green/yellow/red decibel gradient
    - Peak Hold tick indicator
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
        super().__init__(parent, fg_color="transparent", **kwargs)

        self.channel_name = channel_name
        self.volume = initial_volume
        self.is_muted = False
        self.on_volume_change = on_volume_change
        self.on_mute_toggle = on_mute_toggle

        # Audio VU state
        self._current_level = 0.0
        self._peak_level = 0.0
        self._animating = False

        self._build_ui()

    def _build_ui(self):
        # Row 1: Channel Label, dB readout, and Mute Button
        header_row = ctk.CTkFrame(self, fg_color="transparent")
        header_row.pack(fill="x", pady=(0, 2))

        self.name_label = ctk.CTkLabel(
            header_row,
            text=self.channel_name,
            font=ctk.CTkFont(family="Segoe UI", size=10, weight="bold"),
            text_color=OmniTheme.TEXT_MAIN,
            anchor="w"
        )
        self.name_label.pack(side="left")

        self.db_label = ctk.CTkLabel(
            header_row,
            text=self._vol_to_db_str(self.volume),
            font=OmniTheme.font_mono(9),
            text_color=OmniTheme.TEXT_MUTED
        )
        self.db_label.pack(side="right", padx=(4, 0))

        self.mute_btn = ctk.CTkButton(
            header_row,
            text="Mute",
            width=38,
            height=18,
            font=ctk.CTkFont(family="Segoe UI", size=9),
            fg_color=OmniTheme.BG_INPUT,
            hover_color=OmniTheme.BG_CARD_HOVER,
            text_color=OmniTheme.TEXT_BODY,
            corner_radius=OmniTheme.RADIUS_CONTROL,
            command=self._toggle_mute
        )
        self.mute_btn.pack(side="right", padx=(4, 4))

        # Row 2: Slider control
        slider_row = ctk.CTkFrame(self, fg_color="transparent")
        slider_row.pack(fill="x", pady=(1, 2))

        self.slider = ctk.CTkSlider(
            slider_row,
            from_=0.0,
            to=1.0,
            number_of_steps=100,
            height=10,
            progress_color=OmniTheme.ACCENT_PRIMARY,
            button_color=OmniTheme.TEXT_MAIN,
            button_hover_color="#FFFFFF",
            button_length=12,
            command=self._on_slider_moved
        )
        self.slider.set(self.volume)
        self.slider.pack(fill="x")

        # Row 3: Professional 3-tier VU Level Meter
        meter_container = ctk.CTkFrame(self, fg_color=OmniTheme.VU_BG, height=6, corner_radius=2)
        meter_container.pack(fill="x", pady=(1, 6))
        meter_container.pack_propagate(False)

        self.meter_bar = ctk.CTkProgressBar(
            meter_container,
            height=4,
            corner_radius=2,
            progress_color=OmniTheme.VU_GREEN,
            fg_color=OmniTheme.VU_BG
        )
        self.meter_bar.pack(fill="both", expand=True)
        self.meter_bar.set(0.0)

    def _vol_to_db_str(self, val: float) -> str:
        if val <= 0.001:
            return "-inf dB"
        # Map 0.0..1.0 to -40 dB .. 0 dB
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
        if self.is_muted:
            self.mute_btn.configure(
                text="MUTED",
                fg_color=OmniTheme.STATUS_RECORDING,
                hover_color=OmniTheme.STATUS_RECORDING_HOVER,
                text_color="#FFFFFF"
            )
            self.db_label.configure(text="MUTED", text_color=OmniTheme.STATUS_RECORDING)
            self.meter_bar.set(0.0)
        else:
            self.mute_btn.configure(
                text="Mute",
                fg_color=OmniTheme.BG_INPUT,
                hover_color=OmniTheme.BG_CARD_HOVER,
                text_color=OmniTheme.TEXT_BODY
            )
            self.db_label.configure(text=self._vol_to_db_str(self.volume), text_color=OmniTheme.TEXT_MUTED)

        if self.on_mute_toggle:
            self.on_mute_toggle(self.is_muted)

    def set_level(self, level: float):
        """Update live audio level (0.0 to 1.0) with gradient color shifting."""
        if self.is_muted:
            self.meter_bar.set(0.0)
            return

        level = max(0.0, min(1.0, level * self.volume))
        self.meter_bar.set(level)

        # Dynamic color shift: Green -> Yellow -> Red
        if level > 0.85:
            self.meter_bar.configure(progress_color=OmniTheme.VU_RED)
        elif level > 0.65:
            self.meter_bar.configure(progress_color=OmniTheme.VU_YELLOW)
        else:
            self.meter_bar.configure(progress_color=OmniTheme.VU_GREEN)

    def simulate_audio_activity(self, active: bool = True):
        """Simulate realistic live ambient audio fluctuation for testing / recording telemetry."""
        if not active or self.is_muted:
            self.set_level(0.0)
            return

        # Natural room noise + speech fluctuation
        base = random.uniform(0.15, 0.55)
        if random.random() > 0.8:
            base += random.uniform(0.15, 0.35)
        self.set_level(base)
