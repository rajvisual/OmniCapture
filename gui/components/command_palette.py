from typing import List, Dict, Any, Callable, Optional
import customtkinter as ctk

from gui.theme import OmniTheme

class CommandPalette(ctk.CTkToplevel):
    """
    Fast, searchable Command Palette (Ctrl+Shift+P / Ctrl+K).
    Allows executing any studio command instantly using fuzzy search and keyboard navigation.
    """

    def __init__(self, parent: ctk.CTk, commands: List[Dict[str, Any]]):
        super().__init__(parent)

        self.parent_window = parent
        self.all_commands = commands
        self.filtered_commands: List[Dict[str, Any]] = list(commands)
        self.selected_index = 0

        # Modal configuration
        self.title("Command Palette")
        self.overrideredirect(True) # Borderless floating palette
        self.attributes("-topmost", True)
        self.configure(fg_color=OmniTheme.BG_ROOT)

        # Size & Center Position relative to parent
        w, h = 540, 360
        px = parent.winfo_rootx()
        py = parent.winfo_rooty()
        pw = parent.winfo_width()
        x = max(10, px + (pw - w) // 2)
        y = max(10, py + 60)
        self.geometry(f"{w}x{h}+{x}+{y}")

        self._build_ui()
        self._bind_keys()

        # Focus entry immediately
        self.after(50, lambda: self.search_entry.focus_set())

    def _build_ui(self):
        # Outer Border Box
        container = ctk.CTkFrame(
            self,
            fg_color=OmniTheme.BG_CARD,
            border_width=1,
            border_color=OmniTheme.BORDER_FOCUS,
            corner_radius=OmniTheme.RADIUS_POPUP
        )
        container.pack(fill="both", expand=True, padx=2, pady=2)

        # Search Bar
        search_row = ctk.CTkFrame(container, fg_color="transparent")
        search_row.pack(fill="x", padx=12, pady=(12, 8))

        ctk.CTkLabel(
            search_row,
            text=">",
            font=ctk.CTkFont(family="Consolas", size=14, weight="bold"),
            text_color=OmniTheme.ACCENT_PRIMARY
        ).pack(side="left", padx=(0, 8))

        self.search_var = ctk.StringVar()
        self.search_var.trace_add("write", self._on_search_change)

        self.search_entry = ctk.CTkEntry(
            search_row,
            textvariable=self.search_var,
            placeholder_text="Type a command or search action...",
            font=OmniTheme.font_body(),
            fg_color=OmniTheme.BG_INPUT,
            border_width=0,
            height=32
        )
        self.search_entry.pack(side="left", fill="x", expand=True)

        # Separator line
        sep = ctk.CTkFrame(container, fg_color=OmniTheme.BORDER_SUBTLE, height=1)
        sep.pack(fill="x", padx=8, pady=(0, 6))

        # Command Results List
        self.scroll_list = ctk.CTkScrollableFrame(container, fg_color="transparent")
        self.scroll_list.pack(fill="both", expand=True, padx=8, pady=(0, 8))

        # Footer Hint
        hint_bar = ctk.CTkFrame(container, fg_color=OmniTheme.BG_DOCK_HEADER, height=24, corner_radius=0)
        hint_bar.pack(fill="x", side="bottom")
        ctk.CTkLabel(
            hint_bar,
            text="↑↓ to navigate  ·  Enter to select  ·  Esc to close",
            font=OmniTheme.font_label(),
            text_color=OmniTheme.TEXT_DIM
        ).pack(side="left", padx=12, pady=3)

        self._render_results()

    def _bind_keys(self):
        self.bind("<Escape>", lambda e: self.close())
        self.bind("<Return>", lambda e: self._execute_selected())
        self.bind("<Up>", lambda e: self._move_selection(-1))
        self.bind("<Down>", lambda e: self._move_selection(1))
        self.bind("<FocusOut>", self._on_focus_lost)

    def _on_focus_lost(self, event):
        # Gracefully close if user clicks outside
        self.after(100, self._check_focus)

    def _check_focus(self):
        try:
            focused = self.focus_get()
            if focused is None or str(self) not in str(focused):
                self.close()
        except Exception:
            self.close()

    def _on_search_change(self, *args):
        query = self.search_var.get().strip().lower()
        if not query:
            self.filtered_commands = list(self.all_commands)
        else:
            self.filtered_commands = [
                c for c in self.all_commands
                if query in c["title"].lower() or query in c.get("category", "").lower() or query in c.get("keywords", "").lower()
            ]
        self.selected_index = 0
        self._render_results()

    def _move_selection(self, delta: int):
        if not self.filtered_commands:
            return
        self.selected_index = (self.selected_index + delta) % len(self.filtered_commands)
        self._render_results()

    def _render_results(self):
        # Clear existing items
        for child in self.scroll_list.winfo_children():
            child.destroy()

        if not self.filtered_commands:
            ctk.CTkLabel(
                self.scroll_list,
                text="No matching commands found",
                font=OmniTheme.font_label(),
                text_color=OmniTheme.TEXT_MUTED
            ).pack(pady=24)
            return

        for idx, cmd in enumerate(self.filtered_commands[:15]): # Cap at 15 for responsiveness
            is_selected = (idx == self.selected_index)
            bg = OmniTheme.BG_CARD_HOVER if is_selected else "transparent"
            bw = 1 if is_selected else 0
            border_col = OmniTheme.BORDER_FOCUS

            row = ctk.CTkFrame(self.scroll_list, fg_color=bg, border_width=bw, border_color=border_col, corner_radius=OmniTheme.RADIUS_CONTROL)
            row.pack(fill="x", pady=1)

            # Left content: Category + Title
            col = ctk.CTkFrame(row, fg_color="transparent")
            col.pack(side="left", fill="x", expand=True, padx=8, pady=4)

            cat = cmd.get("category", "General")
            title_text = cmd["title"]

            title_lbl = ctk.CTkLabel(
                col,
                text=f"{cat}:  {title_text}",
                font=OmniTheme.font_body(),
                text_color=OmniTheme.TEXT_MAIN if is_selected else OmniTheme.TEXT_BODY,
                anchor="w"
            )
            title_lbl.pack(anchor="w")

            # Right content: Shortcut badge
            if cmd.get("shortcut"):
                sc_badge = ctk.CTkLabel(
                    row,
                    text=cmd["shortcut"],
                    font=OmniTheme.font_mono(9),
                    text_color=OmniTheme.TEXT_MUTED,
                    fg_color=OmniTheme.BG_INPUT,
                    corner_radius=OmniTheme.RADIUS_CONTROL,
                    padx=6,
                    pady=2
                )
                sc_badge.pack(side="right", padx=8)

            # Click handler
            row.bind("<Button-1>", lambda e, c=cmd: self._execute_command(c))
            title_lbl.bind("<Button-1>", lambda e, c=cmd: self._execute_command(c))

    def _execute_selected(self):
        if 0 <= self.selected_index < len(self.filtered_commands):
            cmd = self.filtered_commands[self.selected_index]
            self._execute_command(cmd)

    def _execute_command(self, cmd: Dict[str, Any]):
        action = cmd.get("action")
        self.close()
        if action:
            self.parent_window.after(50, action)

    def close(self):
        try:
            self.destroy()
        except Exception:
            pass
