from typing import Optional, Callable
import customtkinter as ctk

from gui.theme import OmniTheme, ThemeTokens
from gui.components.button import StudioButton

class StudioConfirmDialog(ctk.CTkToplevel):
    """
    Standard Windows 11 Confirmation Dialog for Destructive Actions.
    Adheres to Desktop Guidelines:
    - Only shown for destructive / irreversible actions (e.g. permanent file deletion, aborting active take)
    - Specific consequence clearly articulated in body text
    - Confirm button carries the explicit action name (e.g. 'Delete 3 Recordings', 'Discard Take'), NEVER generic 'OK'
    - Supports synchronous or asynchronous callback resolution
    """

    def __init__(
        self,
        parent,
        title: str,
        message: str,
        consequence: str,
        confirm_text: str = "Confirm",
        cancel_text: str = "Cancel",
        is_danger: bool = True,
        on_confirm: Optional[Callable[[], None]] = None,
        on_cancel: Optional[Callable[[], None]] = None
    ):
        super().__init__(parent)
        self.on_confirm = on_confirm
        self.on_cancel = on_cancel
        self.result = False

        self.title(title)
        self.geometry("460x240")
        self.resizable(False, False)
        self.attributes("-topmost", True)

        tokens = OmniTheme.get_tokens()
        self.configure(fg_color=tokens.bg_root)

        # Center relative to parent
        self.update_idletasks()
        try:
            px = parent.winfo_rootx()
            py = parent.winfo_rooty()
            pw = parent.winfo_width()
            ph = parent.winfo_height()
            x = px + (pw - 460) // 2
            y = py + (ph - 240) // 2
            self.geometry(f"+{max(20, x)}+{max(20, y)}")
        except Exception:
            pass

        self._build_ui(tokens, title, message, consequence, confirm_text, cancel_text, is_danger)

    def _build_ui(
        self,
        tokens: ThemeTokens,
        title: str,
        message: str,
        consequence: str,
        confirm_text: str,
        cancel_text: str,
        is_danger: bool
    ):
        container = ctk.CTkFrame(self, fg_color=tokens.bg_panel, corner_radius=0)
        container.pack(fill="both", expand=True)

        # Header area
        header_row = ctk.CTkFrame(container, fg_color="transparent")
        header_row.pack(fill="x", padx=20, pady=(18, 6))

        # Red / amber accent warning bar
        accent_bar = ctk.CTkFrame(header_row, width=4, height=20, fg_color=tokens.status_recording if is_danger else tokens.status_warning)
        accent_bar.pack(side="left", padx=(0, 10))

        ctk.CTkLabel(
            header_row,
            text=title,
            font=OmniTheme.font_title(),
            text_color=tokens.text_primary,
            anchor="w"
        ).pack(side="left")

        # Body & Consequence text
        body = ctk.CTkFrame(container, fg_color="transparent")
        body.pack(fill="both", expand=True, padx=20, pady=(4, 12))

        ctk.CTkLabel(
            body,
            text=message,
            font=OmniTheme.font_body(),
            text_color=tokens.text_secondary,
            anchor="w",
            justify="left",
            wraplength=410
        ).pack(anchor="w")

        if consequence:
            ctk.CTkLabel(
                body,
                text=consequence,
                font=OmniTheme.font_body_bold(),
                text_color=tokens.status_recording if is_danger else tokens.text_primary,
                anchor="w",
                justify="left",
                wraplength=410
            ).pack(anchor="w", pady=(8, 0))

        # Bottom actions row
        actions = ctk.CTkFrame(container, fg_color=tokens.bg_header, height=52, corner_radius=0)
        actions.pack(fill="x", side="bottom")

        # Action-named confirm button (never "OK")
        self.confirm_btn = StudioButton(
            actions,
            text=confirm_text,
            variant="danger" if is_danger else "primary",
            size="normal",
            command=self._do_confirm
        )
        self.confirm_btn.pack(side="right", padx=16, pady=10)

        # Cancel button
        self.cancel_btn = StudioButton(
            actions,
            text=cancel_text,
            variant="secondary",
            size="normal",
            command=self._do_cancel
        )
        self.cancel_btn.pack(side="right", padx=(0, 4), pady=10)

    def _do_confirm(self):
        self.result = True
        if self.on_confirm:
            self.on_confirm()
        self.destroy()

    def _do_cancel(self):
        self.result = False
        if self.on_cancel:
            self.on_cancel()
        self.destroy()
