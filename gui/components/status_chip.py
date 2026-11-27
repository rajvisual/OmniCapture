from typing import Optional
import customtkinter as ctk

from gui.theme import OmniTheme, ThemeTokens

class StatusChip(ctk.CTkFrame):
    """
    Fluent Windows 11 Status Chip.
    Displays an operational status dot, concise label, and optional telemetry reading.
    Respects theme tokens without hardcoded colors.
    """

    def __init__(
        self,
        parent,
        text: str = "Studio Ready",
        state: str = "ready", # "ready" | "recording" | "warning" | "connected" | "disconnected"
        **kwargs
    ):
        tokens = OmniTheme.get_tokens()
        super().__init__(
            parent,
            fg_color=tokens.bg_input,
            border_width=1,
            border_color=tokens.border_subtle,
            corner_radius=OmniTheme.RADIUS_CONTROL,
            height=28,
            **kwargs
        )
        self.pack_propagate(False)

        self._state = state
        self._text = text

        # Dot indicator
        self.dot = ctk.CTkLabel(
            self,
            text="●",
            font=ctk.CTkFont(size=9),
            text_color=self._get_dot_color(tokens, state)
        )
        self.dot.pack(side="left", padx=(8, 4))

        # Text label
        self.label = ctk.CTkLabel(
            self,
            text=text,
            font=OmniTheme.font_caption(),
            text_color=tokens.text_primary
        )
        self.label.pack(side="left", padx=(0, 10))

    def _get_dot_color(self, tokens: ThemeTokens, state: str) -> str:
        if state == "recording":
            return tokens.status_recording
        elif state == "connected" or state == "ready":
            return tokens.status_connected
        elif state == "warning":
            return tokens.status_warning
        else:
            return tokens.text_dim

    def set_status(self, text: str, state: str = "ready"):
        self._state = state
        self._text = text
        tokens = OmniTheme.get_tokens()
        self.dot.configure(text_color=self._get_dot_color(tokens, state))
        self.label.configure(text=text)

    def apply_tokens(self, tokens: ThemeTokens):
        self.configure(
            fg_color=tokens.bg_input,
            border_color=tokens.border_subtle
        )
        self.dot.configure(text_color=self._get_dot_color(tokens, self._state))
        self.label.configure(text_color=tokens.text_primary)
