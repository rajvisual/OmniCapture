from typing import Optional, Callable
import tkinter as tk
import customtkinter as ctk

from gui.theme import OmniTheme, ThemeTokens

class SceneListItem(ctk.CTkFrame):
    """
    Studio Scene List Item Component.
    Features:
    - Number badge (1-4) with keyboard shortcut hint
    - Active indicator strip (accent_primary)
    - Scene title
    - Inline rename support (double-click to edit name in place)
    """

    def __init__(
        self,
        parent,
        scene_id: str,
        number: int,
        title: str,
        is_active: bool = False,
        on_select: Optional[Callable[[str], None]] = None,
        on_rename: Optional[Callable[[str, str], None]] = None,
        **kwargs
    ):
        tokens = OmniTheme.get_tokens()
        super().__init__(
            parent,
            fg_color=tokens.accent_subtle if is_active else "transparent",
            height=32,
            corner_radius=OmniTheme.RADIUS_CONTROL,
            **kwargs
        )
        self.pack_propagate(False)

        self.scene_id = scene_id
        self.number = number
        self.title_text = title
        self.is_active = is_active
        self.on_select = on_select
        self.on_rename = on_rename
        self._is_editing = False

        # 1. Left active indicator bar (3px width)
        self.indicator = ctk.CTkFrame(
            self,
            width=3,
            height=20,
            corner_radius=1,
            fg_color=tokens.accent_primary if is_active else "transparent"
        )
        self.indicator.pack(side="left", padx=(4, 6), pady=6)

        # 2. Number badge
        self.badge = ctk.CTkLabel(
            self,
            text=f" {number} ",
            font=OmniTheme.font_mono(10, weight="bold"),
            text_color=tokens.text_dim,
            fg_color=tokens.bg_input,
            corner_radius=4,
            width=18,
            height=18
        )
        self.badge.pack(side="left", padx=(0, 8), pady=6)

        # 3. Scene Title Label
        self.title_lbl = ctk.CTkLabel(
            self,
            text=title,
            font=OmniTheme.font_body_bold() if is_active else OmniTheme.font_body(),
            text_color=tokens.text_primary,
            anchor="w"
        )
        self.title_lbl.pack(side="left", fill="x", expand=True, pady=6)

        # 4. Hidden Entry for inline renaming
        self.entry_var = tk.StringVar(value=title)
        self.entry = ctk.CTkEntry(
            self,
            textvariable=self.entry_var,
            font=OmniTheme.font_body(),
            height=24,
            corner_radius=4,
            border_width=1,
            border_color=tokens.accent_primary
        )

        # Mouse and keyboard bindings
        self.bind("<Button-1>", self._on_click)
        self.title_lbl.bind("<Button-1>", self._on_click)
        self.badge.bind("<Button-1>", self._on_click)

        # Double click to rename
        self.title_lbl.bind("<Double-Button-1>", self._start_rename)
        self.entry.bind("<Return>", self._finish_rename)
        self.entry.bind("<FocusOut>", self._finish_rename)
        self.entry.bind("<Escape>", self._cancel_rename)

    def _on_click(self, event=None):
        if not self._is_editing and self.on_select:
            self.on_select(self.scene_id)

    def _start_rename(self, event=None):
        self._is_editing = True
        self.title_lbl.pack_forget()
        self.entry.pack(side="left", fill="x", expand=True, padx=(0, 6), pady=4)
        self.entry.focus_set()
        self.entry.select_range(0, tk.END)

    def _finish_rename(self, event=None):
        if not self._is_editing:
            return
        self._is_editing = False
        new_text = self.entry_var.get().strip()
        if new_text and new_text != self.title_text:
            self.title_text = new_text
            self.title_lbl.configure(text=new_text)
            if self.on_rename:
                self.on_rename(self.scene_id, new_text)
        else:
            self.entry_var.set(self.title_text)

        self.entry.pack_forget()
        self.title_lbl.pack(side="left", fill="x", expand=True, pady=6)

    def _cancel_rename(self, event=None):
        if not self._is_editing:
            return
        self._is_editing = False
        self.entry_var.set(self.title_text)
        self.entry.pack_forget()
        self.title_lbl.pack(side="left", fill="x", expand=True, pady=6)

    def set_active(self, active: bool):
        self.is_active = active
        tokens = OmniTheme.get_tokens()
        self.configure(fg_color=tokens.accent_subtle if active else "transparent")
        self.indicator.configure(fg_color=tokens.accent_primary if active else "transparent")
        self.title_lbl.configure(
            font=OmniTheme.font_body_bold() if active else OmniTheme.font_body()
        )

    def apply_tokens(self, tokens: ThemeTokens):
        self.configure(fg_color=tokens.accent_subtle if self.is_active else "transparent")
        self.indicator.configure(fg_color=tokens.accent_primary if self.is_active else "transparent")
        self.badge.configure(text_color=tokens.text_dim, fg_color=tokens.bg_input)
        self.title_lbl.configure(text_color=tokens.text_primary)
        self.entry.configure(border_color=tokens.accent_primary)
