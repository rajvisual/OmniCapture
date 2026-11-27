from typing import Optional, Callable
import customtkinter as ctk

from gui.theme import OmniTheme, ThemeTokens
from gui.components.icons import get_icon

class SourceRow(ctk.CTkFrame):
    """
    OBS-style Source Row Component.
    Features:
    - Checkbox (include/exclude in active mix)
    - Status dot (green = streaming, dim = idle/disconnected)
    - Source name label
    - Visibility eye toggle (render / hide viewfinder preview)
    """

    def __init__(
        self,
        parent,
        name: str,
        initial_checked: bool = True,
        initial_visible: bool = True,
        initial_active: bool = False,
        on_check_toggle: Optional[Callable[[bool], None]] = None,
        on_visibility_toggle: Optional[Callable[[bool], None]] = None,
        **kwargs
    ):
        tokens = OmniTheme.get_tokens()
        super().__init__(
            parent,
            fg_color=tokens.bg_input,
            height=32,
            corner_radius=OmniTheme.RADIUS_CONTROL,
            border_width=1,
            border_color=tokens.border_subtle,
            **kwargs
        )
        self.pack_propagate(False)

        self.name = name
        self.is_checked = initial_checked
        self.is_visible = initial_visible
        self.is_active = initial_active
        self.on_check_toggle = on_check_toggle
        self.on_visibility_toggle = on_visibility_toggle

        # 1. Checkbox (blue only when checked, 3:1 border when unchecked)
        self.check_var = ctk.BooleanVar(value=initial_checked)
        self.checkbox = ctk.CTkCheckBox(
            self,
            text="",
            variable=self.check_var,
            width=20,
            height=20,
            checkbox_width=18,
            checkbox_height=18,
            corner_radius=4,
            border_color=tokens.border_default,
            checkmark_color="#FFFFFF",
            fg_color=tokens.accent_primary,
            hover_color=tokens.accent_hover,
            command=self._on_check_changed
        )
        self.checkbox.pack(side="left", padx=(8, 4), pady=4)

        # 2. Status dot
        self.dot = ctk.CTkLabel(
            self,
            text="●",
            font=ctk.CTkFont(size=9),
            text_color=tokens.status_connected if initial_active else tokens.text_dim
        )
        self.dot.pack(side="left", padx=(0, 6))

        # 3. Label
        self.label = ctk.CTkLabel(
            self,
            text=name,
            font=OmniTheme.font_body(),
            text_color=tokens.text_primary,
            anchor="w"
        )
        self.label.pack(side="left", fill="x", expand=True)

        # 4. Eye toggle
        self.eye_btn = ctk.CTkButton(
            self,
            text="",
            image=get_icon("eye" if initial_visible else "eye_closed", size=(14, 14)),
            width=28,
            height=24,
            fg_color="transparent",
            hover_color=tokens.bg_hover,
            corner_radius=4,
            command=self._on_eye_clicked
        )
        self.eye_btn.pack(side="right", padx=(0, 6), pady=4)

    def _on_check_changed(self):
        self.is_checked = self.check_var.get()
        if self.on_check_toggle:
            self.on_check_toggle(self.is_checked)

    def _on_eye_clicked(self):
        self.is_visible = not self.is_visible
        self.eye_btn.configure(
            image=get_icon("eye" if self.is_visible else "eye_closed", size=(14, 14))
        )
        if self.on_visibility_toggle:
            self.on_visibility_toggle(self.is_visible)

    def set_active_state(self, active: bool):
        self.is_active = active
        tokens = OmniTheme.get_tokens()
        self.dot.configure(
            text_color=tokens.status_connected if active else tokens.text_dim
        )

    def select(self):
        self.check_var.set(True)
        self.is_checked = True

    def deselect(self):
        self.check_var.set(False)
        self.is_checked = False

    def apply_tokens(self, tokens: ThemeTokens):
        self.configure(
            fg_color=tokens.bg_input,
            border_color=tokens.border_subtle
        )
        self.checkbox.configure(
            border_color=tokens.border_default,
            fg_color=tokens.accent_primary,
            hover_color=tokens.accent_hover,
            checkmark_color="#FFFFFF"
        )
        self.dot.configure(
            text_color=tokens.status_connected if self.is_active else tokens.text_dim
        )
        self.label.configure(text_color=tokens.text_primary)
        self.eye_btn.configure(hover_color=tokens.bg_hover)
