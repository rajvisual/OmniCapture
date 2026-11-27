from typing import List, Dict, Any, Callable, Optional
import customtkinter as ctk

from gui.theme import OmniTheme, ThemeTokens

class MenuDropdown(ctk.CTkToplevel):
    """
    Custom Styled Desktop Menu Dropdown with Native Behavior.
    - Keyboard navigation (Up, Down, Enter, Escape)
    - Check mark indicators for toggle actions
    - Right-aligned accelerator hints
    - Disabled item styling
    - 8px corner radius with 1px border
    - Outside-click and window-deactivate auto-dismiss
    """

    def __init__(
        self,
        parent,
        items: List[Dict[str, Any]],
        x: int,
        y: int,
        animate: bool = True
    ):
        super().__init__(parent)
        self.parent_window = parent
        self.items = items
        self.selectable_buttons: List[ctk.CTkButton] = []
        self.selectable_actions: List[Optional[Callable]] = []
        self.selected_index = -1

        tokens = OmniTheme.get_tokens()

        self.overrideredirect(True)
        self.attributes("-topmost", True)
        self.configure(fg_color=tokens.bg_panel)

        # 8px corner radius Fluent container
        self.container = ctk.CTkFrame(
            self,
            fg_color=tokens.bg_panel,
            border_width=1,
            border_color=tokens.border_default,
            corner_radius=OmniTheme.RADIUS_POPUP
        )
        self.container.pack(fill="both", expand=True, padx=1, pady=1)

        total_height = 8
        max_width = 240

        for item in items:
            if item.get("separator"):
                sep = ctk.CTkFrame(
                    self.container,
                    fg_color=tokens.border_subtle,
                    height=1
                )
                sep.pack(fill="x", padx=8, pady=4)
                total_height += 9
                continue

            btn_row = ctk.CTkFrame(self.container, fg_color="transparent")
            btn_row.pack(fill="x", padx=4, pady=1)

            raw_label = item.get("label", "")
            is_checked = item.get("checked")
            if is_checked is True:
                display_label = f"✓  {raw_label}"
            elif is_checked is False:
                display_label = f"    {raw_label}"
            else:
                display_label = raw_label

            sc = item.get("accelerator", "")
            action = item.get("command")
            is_disabled = item.get("disabled", False)

            # Button row
            btn = ctk.CTkButton(
                btn_row,
                text=display_label,
                anchor="w",
                font=OmniTheme.font_body(),
                height=26,
                fg_color="transparent",
                hover_color=tokens.bg_hover if not is_disabled else "transparent",
                text_color=tokens.text_dim if is_disabled else tokens.text_primary,
                corner_radius=4,
                state="disabled" if is_disabled else "normal",
                command=lambda a=action: self._trigger(a)
            )
            btn.pack(side="left", fill="x", expand=True)

            if not is_disabled:
                idx = len(self.selectable_buttons)
                btn.bind("<Enter>", lambda e, i=idx: self._set_highlight(i))
                btn.bind("<Leave>", lambda e: self._clear_highlight())
                self.selectable_buttons.append(btn)
                self.selectable_actions.append(action)

            if sc:
                sc_lbl = ctk.CTkLabel(
                    btn_row,
                    text=sc,
                    font=OmniTheme.font_mono(10),
                    text_color=tokens.text_dim
                )
                sc_lbl.pack(side="right", padx=(4, 8))

            total_height += 28

        self.geometry(f"{max_width}x{total_height}+{x}+{y}")

        # Bind keyboard navigation
        self.bind("<Up>", self._on_key_up)
        self.bind("<Down>", self._on_key_down)
        self.bind("<Return>", self._on_key_return)
        self.bind("<Escape>", lambda e: self.close())
        self.bind("<FocusOut>", self._on_focus_lost)

        # Smooth 100ms fade-in if animated
        if animate:
            self.attributes("-alpha", 0.0)
            self._fade_in(step=0.2)
        else:
            self.attributes("-alpha", 1.0)

        self.after(50, self._grab_focus)

    def _grab_focus(self):
        try:
            self.focus_force()
        except Exception:
            pass

    def _fade_in(self, step: float = 0.25):
        try:
            curr = float(self.attributes("-alpha"))
            if curr < 1.0:
                self.attributes("-alpha", min(1.0, curr + step))
                self.after(20, lambda: self._fade_in(step))
        except Exception:
            try:
                self.attributes("-alpha", 1.0)
            except Exception:
                pass

    def _set_highlight(self, index: int):
        tokens = OmniTheme.get_tokens()
        self._clear_highlight()
        if 0 <= index < len(self.selectable_buttons):
            self.selected_index = index
            self.selectable_buttons[index].configure(fg_color=tokens.bg_hover)

    def _clear_highlight(self):
        for btn in self.selectable_buttons:
            try:
                btn.configure(fg_color="transparent")
            except Exception:
                pass
        self.selected_index = -1

    def _on_key_up(self, event):
        if not self.selectable_buttons:
            return
        new_idx = (self.selected_index - 1) % len(self.selectable_buttons)
        self._set_highlight(new_idx)

    def _on_key_down(self, event):
        if not self.selectable_buttons:
            return
        new_idx = (self.selected_index + 1) % len(self.selectable_buttons)
        self._set_highlight(new_idx)

    def _on_key_return(self, event):
        if 0 <= self.selected_index < len(self.selectable_actions):
            self._trigger(self.selectable_actions[self.selected_index])

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
