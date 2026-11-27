import tkinter as tk
from typing import Optional, Callable
import customtkinter as ctk

from gui.theme import OmniTheme, ThemeTokens

class Divider(ctk.CTkFrame):
    """1px Subtle divider line respecting theme tokens."""
    def __init__(self, parent, orientation: str = "horizontal", **kwargs):
        tokens = OmniTheme.get_tokens()
        if orientation == "horizontal":
            super().__init__(parent, height=1, fg_color=tokens.border_subtle, **kwargs)
        else:
            super().__init__(parent, width=1, fg_color=tokens.border_subtle, **kwargs)

    def apply_tokens(self, tokens: ThemeTokens):
        self.configure(fg_color=tokens.border_subtle)


class SectionHeader(ctk.CTkFrame):
    """
    Sentence-case 13px bold section header.
    Features:
    - High contrast text
    - Optional count badge or action link
    - Strict 4px vertical rhythm
    """
    def __init__(self, parent, text: str, badge_text: Optional[str] = None, **kwargs):
        tokens = OmniTheme.get_tokens()
        super().__init__(parent, fg_color="transparent", **kwargs)

        self.label = ctk.CTkLabel(
            self,
            text=text,
            font=OmniTheme.font_section(),
            text_color=tokens.text_primary,
            anchor="w"
        )
        self.label.pack(side="left", padx=(2, 6), pady=(8, 4))

        self.badge = None
        if badge_text:
            self.badge = ctk.CTkLabel(
                self,
                text=f" {badge_text} ",
                font=OmniTheme.font_meta(),
                text_color=tokens.text_dim,
                fg_color=tokens.bg_input,
                corner_radius=4
            )
            self.badge.pack(side="left", pady=(8, 4))

    def set_text(self, text: str):
        self.label.configure(text=text)

    def apply_tokens(self, tokens: ThemeTokens):
        self.label.configure(text_color=tokens.text_primary)
        if self.badge:
            self.badge.configure(text_color=tokens.text_dim, fg_color=tokens.bg_input)


class Tooltip:
    """
    Lightweight, token-styled desktop tooltip.
    Appears after 350ms hover delay, vanishes on mouse leave or click.
    """
    def __init__(self, widget, text: str):
        self.widget = widget
        self.text = text
        self.tip_window = None
        self._after_id = None

        self.widget.bind("<Enter>", self._schedule, add="+")
        self.widget.bind("<Leave>", self._hide, add="+")
        self.widget.bind("<Button-1>", self._hide, add="+")

    def _schedule(self, event=None):
        self._cancel()
        self._after_id = self.widget.after(350, self._show)

    def _cancel(self):
        if self._after_id:
            try:
                self.widget.after_cancel(self._after_id)
            except Exception:
                pass
            self._after_id = None

    def _show(self):
        if not self.text:
            return
        tokens = OmniTheme.get_tokens()

        x = self.widget.winfo_rootx() + (self.widget.winfo_width() // 2)
        y = self.widget.winfo_rooty() + self.widget.winfo_height() + 4

        self.tip_window = tw = tk.Toplevel(self.widget)
        tw.wm_overrideredirect(True)
        tw.wm_geometry(f"+{x}+{y}")
        tw.attributes("-topmost", True)

        frame = tk.Frame(
            tw,
            background=tokens.bg_raised,
            highlightbackground=tokens.border_default,
            highlightthickness=1,
            padx=8,
            pady=4
        )
        frame.pack()

        lbl = tk.Label(
            frame,
            text=self.text,
            background=tokens.bg_raised,
            foreground=tokens.text_primary,
            font=("Segoe UI", 9)
        )
        lbl.pack()

    def _hide(self, event=None):
        self._cancel()
        if self.tip_window:
            try:
                self.tip_window.destroy()
            except Exception:
                pass
            self.tip_window = None

    def update_text(self, text: str):
        self.text = text


class InputField(ctk.CTkEntry):
    """
    Standard 32px form text entry.
    Features:
    - 32px height standard
    - 8px corner radius
    - Focus ring: changes border color to border_focus on focus in
    """
    def __init__(self, parent, placeholder: str = "", **kwargs):
        tokens = OmniTheme.get_tokens()
        super().__init__(
            parent,
            height=OmniTheme.CONTROL_HEIGHT,
            corner_radius=OmniTheme.RADIUS_CONTROL,
            fg_color=tokens.bg_input,
            text_color=tokens.text_primary,
            placeholder_text_color=tokens.text_dim,
            border_color=tokens.border_default,
            border_width=1,
            placeholder_text=placeholder,
            font=OmniTheme.font_body(),
            **kwargs
        )
        self.bind("<FocusIn>", self._on_focus_in, add="+")
        self.bind("<FocusOut>", self._on_focus_out, add="+")

    def _on_focus_in(self, event=None):
        tokens = OmniTheme.get_tokens()
        self.configure(border_color=tokens.border_focus, border_width=2)

    def _on_focus_out(self, event=None):
        tokens = OmniTheme.get_tokens()
        self.configure(border_color=tokens.border_default, border_width=1)

    def apply_tokens(self, tokens: ThemeTokens):
        self.configure(
            fg_color=tokens.bg_input,
            text_color=tokens.text_primary,
            placeholder_text_color=tokens.text_dim,
            border_color=tokens.border_default
        )
