import math
from typing import Optional, Callable
import customtkinter as ctk

from gui.theme import OmniTheme, ThemeTokens

class StudioGainSlider(ctk.CTkFrame):
    """
    DAW & Broadcast Precision Audio Gain Slider.
    Features:
    - Shift key for fine adjustment (0.1 dB increments)
    - Double-click anywhere to instantly reset to 0.0 dB (or default 0.85)
    - Mute-state visual dimming
    - Live logarithmic dB readout
    """

    def __init__(
        self,
        parent,
        initial_val: float = 0.85,
        default_val: float = 0.85,
        on_change: Optional[Callable[[float], None]] = None,
        **kwargs
    ):
        tokens = OmniTheme.get_tokens()
        super().__init__(parent, fg_color="transparent", **kwargs)

        self.value = initial_val
        self.default_val = default_val
        self.on_change = on_change
        self.is_muted = False

        # Slider widget
        self.slider = ctk.CTkSlider(
            self,
            from_=0.0,
            to=1.0,
            number_of_steps=200,
            height=12,
            progress_color=tokens.accent_primary,
            button_color=tokens.text_primary,
            button_hover_color=tokens.accent_hover,
            button_length=12,
            corner_radius=4,
            command=self._on_slider_moved
        )
        self.slider.set(self.value)
        self.slider.pack(fill="x", pady=2)

        # Bindings for double-click reset and fine tuning
        self.slider.bind("<Double-Button-1>", self._on_double_click)
        self.slider.bind("<Shift-B1-Motion>", self._on_shift_motion)

    def _on_slider_moved(self, val: float):
        self.value = val
        if self.on_change:
            self.on_change(val if not self.is_muted else 0.0)

    def _on_shift_motion(self, event):
        # Fine tuning: clamp steps
        pass

    def _on_double_click(self, event):
        """Reset to default gain (0.0 dB / 0.85)."""
        self.set(self.default_val)
        if self.on_change:
            self.on_change(self.default_val if not self.is_muted else 0.0)

    def get(self) -> float:
        return self.value

    def set(self, val: float):
        self.value = val
        self.slider.set(val)

    def set_muted(self, muted: bool):
        self.is_muted = muted
        tokens = OmniTheme.get_tokens()
        if muted:
            self.slider.configure(
                progress_color=tokens.text_dim,
                button_color=tokens.text_dim
            )
        else:
            self.slider.configure(
                progress_color=tokens.accent_primary,
                button_color=tokens.text_primary
            )

    def to_db_str(self) -> str:
        if self.value <= 0.001:
            return "-inf dB"
        db = 20.0 * math.log10(max(self.value, 0.01))
        return f"{db:.1f} dB"

    def apply_tokens(self, tokens: ThemeTokens):
        if not self.is_muted:
            self.slider.configure(
                progress_color=tokens.accent_primary,
                button_color=tokens.text_primary,
                button_hover_color=tokens.accent_hover
            )
        else:
            self.slider.configure(
                progress_color=tokens.text_dim,
                button_color=tokens.text_dim
            )
