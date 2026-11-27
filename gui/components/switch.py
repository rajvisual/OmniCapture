from typing import Optional, Callable
import customtkinter as ctk

from gui.theme import OmniTheme, ThemeTokens

class StudioSwitch(ctk.CTkFrame):
    """
    Fluent Windows 11 Compound Switch.
    Features:
    - 32px height container
    - Primary label in Segoe UI Variable (font_body)
    - Optional helper text underneath in font_caption (text_muted)
    - Accent progress color respecting theme tokens
    """

    def __init__(
        self,
        parent,
        text: str,
        helper_text: Optional[str] = None,
        variable: Optional[ctk.BooleanVar] = None,
        command: Optional[Callable[[], None]] = None,
        **kwargs
    ):
        tokens = OmniTheme.get_tokens()
        super().__init__(parent, fg_color="transparent", **kwargs)

        self.variable = variable or ctk.BooleanVar(value=False)
        self.command = command

        # Layout: switch control on left, text block on right
        is_on = self.variable.get()
        btn_col = "#FFFFFF" if is_on else (tokens.text_muted if not tokens.is_dark else tokens.text_secondary)
        btn_hover = "#F3F4F6" if is_on else (tokens.text_primary if not tokens.is_dark else tokens.text_primary)
        b_width = 0 if is_on else 1

        self.switch = ctk.CTkSwitch(
            self,
            text="",
            variable=self.variable,
            command=self._on_toggled,
            width=42,
            height=20,
            switch_width=38,
            switch_height=20,
            progress_color=tokens.accent_primary,
            button_color=btn_col,
            button_hover_color=btn_hover,
            border_width=b_width,
            border_color=tokens.border_default,
            fg_color=tokens.bg_input
        )
        self.switch.pack(side="left", padx=(0, 10), pady=4)

        text_col = ctk.CTkFrame(self, fg_color="transparent")
        text_col.pack(side="left", fill="x", expand=True)

        self.label = ctk.CTkLabel(
            text_col,
            text=text,
            font=OmniTheme.font_body(),
            text_color=tokens.text_primary,
            anchor="w"
        )
        self.label.pack(anchor="w")

        self.helper_lbl = None
        if helper_text:
            self.helper_lbl = ctk.CTkLabel(
                text_col,
                text=helper_text,
                font=OmniTheme.font_caption(),
                text_color=tokens.text_muted,
                anchor="w"
            )
            self.helper_lbl.pack(anchor="w")

    def _sync_switch_visuals(self):
        tokens = OmniTheme.get_tokens()
        is_on = self.variable.get()
        if is_on:
            self.switch.configure(
                button_color="#FFFFFF",
                button_hover_color="#F3F4F6",
                border_width=0,
                progress_color=tokens.accent_primary,
                fg_color=tokens.bg_input
            )
        else:
            # Windows 11 style OFF state: 1px border at >= 3:1 and dark thumb at >= 3:1
            thumb_col = tokens.text_muted if not tokens.is_dark else tokens.text_secondary
            self.switch.configure(
                button_color=thumb_col,
                button_hover_color=tokens.text_primary,
                border_width=1,
                border_color=tokens.border_default,
                fg_color=tokens.bg_input
            )

    def _on_toggled(self):
        self._sync_switch_visuals()
        if self.command:
            self.command()

    def get(self) -> bool:
        return self.variable.get()

    def set(self, val: bool):
        self.variable.set(val)
        self._sync_switch_visuals()

    def apply_tokens(self, tokens: ThemeTokens):
        self.label.configure(text_color=tokens.text_primary)
        if self.helper_lbl:
            self.helper_lbl.configure(text_color=tokens.text_muted)
        self._sync_switch_visuals()
