from typing import List, Optional, Callable
import customtkinter as ctk

from gui.theme import OmniTheme, ThemeTokens

class StudioSegmentedControl(ctk.CTkSegmentedButton):
    """
    Windows 11 Studio Segmented Control.
    Features:
    - 32px standard height, 8px corner radius
    - Arrow key navigation (<Left> / <Right>)
    - Visible focus ring (<FocusIn> / <FocusOut>)
    - High contrast token styling
    """

    def __init__(
        self,
        parent,
        values: List[str],
        command: Optional[Callable[[str], None]] = None,
        **kwargs
    ):
        self._values_list = values
        self._external_command = command
        tokens = OmniTheme.get_tokens()

        super().__init__(
            parent,
            values=values,
            height=OmniTheme.CONTROL_HEIGHT,
            corner_radius=OmniTheme.RADIUS_CONTROL,
            font=OmniTheme.font_body(),
            command=self._on_segment_click,
            **kwargs
        )

        self._apply_tokens(tokens)

        # Keyboard accessibility via internal canvas
        if hasattr(self, "_canvas"):
            self._canvas.bind("<Left>", self._on_key_left, add="+")
            self._canvas.bind("<Right>", self._on_key_right, add="+")
            self._canvas.bind("<FocusIn>", self._on_focus_in, add="+")
            self._canvas.bind("<FocusOut>", self._on_focus_out, add="+")

    def _apply_tokens(self, tokens: ThemeTokens):
        if not tokens.is_dark:
            # Windows 11 Light: white selected thumb on grey track with dark text and quiet 1px border
            self.configure(
                selected_color="#FFFFFF",
                selected_hover_color="#FFFFFF",
                unselected_color=tokens.bg_raised,
                unselected_hover_color=tokens.bg_hover,
                text_color=tokens.text_primary,
                fg_color=tokens.bg_raised,
                border_width=1
            )
            curr = self.get()
            for val, btn in self._buttons_dict.items():
                if val == curr:
                    btn.configure(border_width=1, border_color=tokens.border_button, text_color=tokens.text_primary)
                else:
                    btn.configure(border_width=0, text_color=tokens.text_muted)
        else:
            # Windows 11 Dark: raised distinct thumb (#282A3A) on dark track (#1A1B26) with #F3F4F6 text and quiet 1px border
            self.configure(
                selected_color="#282A3A",
                selected_hover_color="#323548",
                unselected_color=tokens.bg_input,
                unselected_hover_color=tokens.bg_hover,
                text_color=tokens.text_primary,
                fg_color=tokens.bg_input,
                border_width=1
            )
            curr = self.get()
            for val, btn in self._buttons_dict.items():
                if val == curr:
                    btn.configure(border_width=1, border_color=tokens.border_button, text_color=tokens.text_primary)
                else:
                    btn.configure(border_width=0, text_color=tokens.text_muted)

    def _select_button_by_value(self, value: str):
        super()._select_button_by_value(value)
        tokens = OmniTheme.get_tokens()
        if value in self._buttons_dict:
            self._buttons_dict[value].configure(border_width=1, border_color=tokens.border_button, text_color=tokens.text_primary)

    def _unselect_button_by_value(self, value: str):
        super()._unselect_button_by_value(value)
        tokens = OmniTheme.get_tokens()
        if value in self._buttons_dict:
            self._buttons_dict[value].configure(border_width=0, text_color=tokens.text_muted)

    def _on_segment_click(self, value: str):
        if self._external_command:
            self._external_command(value)

    def _on_key_left(self, event=None):
        curr = self.get()
        if curr in self._values_list:
            idx = self._values_list.index(curr)
            if idx > 0:
                new_val = self._values_list[idx - 1]
                self.set(new_val)
                self._on_segment_click(new_val)

    def _on_key_right(self, event=None):
        curr = self.get()
        if curr in self._values_list:
            idx = self._values_list.index(curr)
            if idx < len(self._values_list) - 1:
                new_val = self._values_list[idx + 1]
                self.set(new_val)
                self._on_segment_click(new_val)

    def _on_focus_in(self, event=None):
        tokens = OmniTheme.get_tokens()
        self.configure(border_width=2)

    def _on_focus_out(self, event=None):
        tokens = OmniTheme.get_tokens()
        self.configure(border_width=1)

    def apply_tokens(self, tokens: ThemeTokens):
        self._apply_tokens(tokens)
