from typing import Optional, Callable
import customtkinter as ctk

from gui.theme import OmniTheme, ThemeTokens
from gui.components.primitives import Tooltip

class StudioButton(ctk.CTkButton):
    """
    Standard Windows 11 Studio Button.
    Variants: 'primary' | 'secondary' | 'ghost' | 'danger' | 'icon'
    Heights: 32px standard, 44px for primary record
    States: default, hover, pressed, focus ring, disabled with tooltip
    """

    def __init__(
        self,
        parent,
        text: str = "",
        variant: str = "secondary",
        size: str = "normal", # "normal" (32px) | "large" (44px) | "small" (28px)
        icon: Optional[ctk.CTkImage] = None,
        disabled_reason: Optional[str] = None,
        command: Optional[Callable[[], None]] = None,
        **kwargs
    ):
        self.variant = variant
        self.size_mode = size
        self.disabled_reason = disabled_reason
        self._tooltip: Optional[Tooltip] = None

        tokens = OmniTheme.get_tokens()
        custom_height = kwargs.pop("height", None)
        height = custom_height or (44 if size == "large" else (28 if size == "small" else OmniTheme.CONTROL_HEIGHT))
        width = 32 if variant == "icon" and not text else kwargs.pop("width", 80)

        super().__init__(
            parent,
            text=text,
            image=icon,
            height=height,
            width=width,
            corner_radius=OmniTheme.RADIUS_CONTROL,
            font=OmniTheme.font_body_bold() if (variant == "primary" or size == "large") else OmniTheme.font_body(),
            command=command,
            **kwargs
        )

        self._apply_variant_colors(tokens)

        # Focus ring and hover border bindings
        self.bind("<FocusIn>", self._on_focus_in, add="+")
        self.bind("<FocusOut>", self._on_focus_out, add="+")
        if self.variant == "secondary":
            self.bind("<Enter>", self._on_enter_secondary, add="+")
            self.bind("<Leave>", self._on_leave_secondary, add="+")

        if self.disabled_reason:
            self._tooltip = Tooltip(self, self.disabled_reason)

    def _on_enter_secondary(self, _event=None):
        if self.cget("state") != "disabled":
            tokens = OmniTheme.get_tokens()
            self.configure(border_color=tokens.border_button_hover)

    def _on_leave_secondary(self, _event=None):
        if self.cget("state") != "disabled":
            tokens = OmniTheme.get_tokens()
            self.configure(border_color=tokens.border_button)

    def _apply_variant_colors(self, tokens: ThemeTokens):
        if self.variant == "primary":
            self.configure(
                fg_color=tokens.accent_primary,
                hover_color=tokens.accent_hover,
                text_color="#FFFFFF" if not tokens.is_dark else tokens.text_primary,
                border_width=0
            )
        elif self.variant == "danger":
            self.configure(
                fg_color=tokens.status_recording,
                hover_color=tokens.status_recording_hover,
                text_color="#FFFFFF",
                border_width=0
            )
        elif self.variant == "ghost":
            self.configure(
                fg_color="transparent",
                hover_color=tokens.bg_hover,
                text_color=tokens.text_secondary,
                border_width=0
            )
        elif self.variant == "icon":
            self.configure(
                fg_color="transparent",
                hover_color=tokens.bg_hover,
                text_color=tokens.text_primary,
                border_width=1,
                border_color=tokens.border_subtle
            )
        else: # secondary
            self.configure(
                fg_color=tokens.bg_input,
                hover_color=tokens.bg_hover,
                text_color=tokens.text_primary,
                border_width=1,
                border_color=tokens.border_button
            )

    def set_disabled(self, disabled: bool, reason: Optional[str] = None):
        """Enable or disable button with optional reason tooltip."""
        tokens = OmniTheme.get_tokens()
        if disabled:
            self.configure(state="disabled")
            if reason:
                self.disabled_reason = reason
                if self._tooltip:
                    self._tooltip.update_text(reason)
                else:
                    self._tooltip = Tooltip(self, reason)
        else:
            self.configure(state="normal")
            if self._tooltip:
                self._tooltip.update_text("")
                self.disabled_reason = None
        self._apply_variant_colors(tokens)

    def _on_focus_in(self, event=None):
        tokens = OmniTheme.get_tokens()
        self.configure(border_width=2, border_color=tokens.border_focus)

    def _on_focus_out(self, event=None):
        tokens = OmniTheme.get_tokens()
        self._apply_variant_colors(tokens)

    def apply_tokens(self, tokens: ThemeTokens):
        self._apply_variant_colors(tokens)
