from typing import List, Dict, Any, Callable, Optional
import customtkinter as ctk

from gui.theme import OmniTheme, ThemeTokens

class MenuDropdown(ctk.CTkToplevel):
    """
    Custom Styled Desktop Menu Dropdown.
    Replaces the classic clashing white Win32 menu bar with a unified Fluent dropdown
    matching the active theme with 8px corner radius, hover highlights, and shortcut badges.
    """

    def __init__(
        self,
        parent,
        items: List[Dict[str, Any]],
        x: int,
        y: int
    ):
        super().__init__(parent)
        self.parent_window = parent

        tokens = OmniTheme.get_tokens()

        self.overrideredirect(True)
        self.attributes("-topmost", True)
        self.configure(fg_color=tokens.bg_panel)

        # Build Container with subtle 1px border
        self.container = ctk.CTkFrame(
            self,
            fg_color=tokens.bg_panel,
            border_width=1,
            border_color=tokens.border_default,
            corner_radius=OmniTheme.RADIUS_CONTROL
        )
        self.container.pack(fill="both", expand=True, padx=1, pady=1)

        total_height = 8
        max_width = 220

        for item in items:
            if item.get("separator"):
                sep = ctk.CTkFrame(
                    self.container,
                    fg_color=tokens.border_subtle,
                    height=1
                )
                sep.pack(fill="x", padx=6, pady=4)
                total_height += 9
                continue

            btn_row = ctk.CTkFrame(self.container, fg_color="transparent")
            btn_row.pack(fill="x", padx=3, pady=1)

            lbl = item["label"]
            sc = item.get("accelerator", "")
            action = item.get("command")

            # Clickable row button
            btn = ctk.CTkButton(
                btn_row,
                text=lbl,
                anchor="w",
                font=OmniTheme.font_body(),
                height=26,
                fg_color="transparent",
                hover_color=tokens.bg_hover,
                text_color=tokens.text_primary,
                corner_radius=4,
                command=lambda a=action: self._trigger(a)
            )
            btn.pack(side="left", fill="x", expand=True)

            if sc:
                sc_lbl = ctk.CTkLabel(
                    btn_row,
                    text=sc,
                    font=OmniTheme.font_mono(10),
                    text_color=tokens.text_dim
                )
                sc_lbl.pack(side="right", padx=(0, 8))

            total_height += 28

        self.geometry(f"{max_width}x{total_height}+{x}+{y}")

        # Bind auto-close events
        self.bind("<Escape>", lambda e: self.close())
        self.bind("<FocusOut>", self._on_focus_lost)
        self.after(50, lambda: self.focus_force())

    def _trigger(self, action: Optional[Callable]):
        self.close()
        if action:
            self.parent_window.after(30, action)

    def _on_focus_lost(self, event):
        self.after(120, self._check_focus)

    def _check_focus(self):
        try:
            focused = self.focus_get()
            if focused is None or str(self) not in str(focused):
                self.close()
        except Exception:
            self.close()

    def close(self):
        try:
            self.destroy()
        except Exception:
            pass
