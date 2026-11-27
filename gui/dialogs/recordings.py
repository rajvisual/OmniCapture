import os
import subprocess
from pathlib import Path
from typing import Optional, List, Dict, Any
import customtkinter as ctk
from tkinter import messagebox

from gui.theme import OmniTheme

class RecordingsGalleryDialog(ctk.CTkToplevel):
    """
    Professional Media Library / Recordings Manager.
    Allows searching, filtering, playing, revealing in Explorer, uploading, and managing captures.
    """

    def __init__(self, parent, controller, on_toast: Optional[callable] = None):
        super().__init__(parent)
        self.controller = controller
        self.on_toast = on_toast

        self.title("OmniCapture — Media Library & Recordings")
        self.geometry("780x540")
        self.minsize(680, 420)
        self.configure(fg_color=OmniTheme.BG_ROOT)

        self.items: List[Dict[str, Any]] = []
        self.filtered_items: List[Dict[str, Any]] = []

        self._build_ui()
        self._load_recordings()

        # Lift & focus
        self.lift()
        self.focus_force()

    def _build_ui(self):
        # 1. Top Toolbar (Search, Filter, Actions)
        top_bar = ctk.CTkFrame(self, fg_color=OmniTheme.BG_DOCK, height=52, corner_radius=0)
        top_bar.pack(fill="x")

        # Search Bar
        search_frame = ctk.CTkFrame(top_bar, fg_color="transparent")
        search_frame.pack(side="left", padx=16, pady=10)

        self.search_var = ctk.StringVar()
        self.search_var.trace_add("write", self._on_filter_changed)

        self.search_entry = ctk.CTkEntry(
            search_frame,
            textvariable=self.search_var,
            placeholder_text="Filter recordings by filename or mode...",
            width=280,
            height=30,
            fg_color=OmniTheme.BG_INPUT,
            border_width=1,
            border_color=OmniTheme.BORDER_DEFAULT
        )
        self.search_entry.pack(side="left")

        # Right Action Buttons
        actions = ctk.CTkFrame(top_bar, fg_color="transparent")
        actions.pack(side="right", padx=16, pady=10)

        ctk.CTkButton(
            actions,
            text="Open Folder",
            width=95,
            height=30,
            font=OmniTheme.font_body(),
            fg_color=OmniTheme.BG_INPUT,
            hover_color=OmniTheme.BG_CARD_HOVER,
            corner_radius=OmniTheme.RADIUS_CONTROL,
            command=self.controller.open_recordings_folder
        ).pack(side="left", padx=4)

        ctk.CTkButton(
            actions,
            text="Refresh",
            width=70,
            height=30,
            font=OmniTheme.font_body(),
            fg_color=OmniTheme.BG_INPUT,
            hover_color=OmniTheme.BG_CARD_HOVER,
            corner_radius=OmniTheme.RADIUS_CONTROL,
            command=self._load_recordings
        ).pack(side="left", padx=4)

        # 2. Summary Status Strip
        self.status_strip = ctk.CTkFrame(self, fg_color=OmniTheme.BG_DOCK_HEADER, height=26, corner_radius=0)
        self.status_strip.pack(fill="x")

        self.summary_label = ctk.CTkLabel(
            self.status_strip,
            text="Loading library...",
            font=OmniTheme.font_label(),
            text_color=OmniTheme.TEXT_MUTED
        )
        self.summary_label.pack(side="left", padx=16, pady=3)

        # 3. Media Items List
        self.scroll_frame = ctk.CTkScrollableFrame(self, fg_color="transparent")
        self.scroll_frame.pack(fill="both", expand=True, padx=16, pady=12)

    def _load_recordings(self):
        self.items = self.controller.get_recordings_list()
        self._apply_filter()

    def _on_filter_changed(self, *args):
        self._apply_filter()

    def _apply_filter(self):
        query = self.search_var.get().strip().lower()
        if not query:
            self.filtered_items = list(self.items)
        else:
            self.filtered_items = [
                it for it in self.items
                if query in it["name"].lower() or query in it.get("tag", "").lower()
            ]

        total_bytes = sum(it.get("size_bytes", 0) for it in self.filtered_items)
        total_mb = total_bytes / (1024 * 1024)
        rec_dir = self.controller.recordings_dir

        self.summary_label.configure(
            text=f"Showing {len(self.filtered_items)} of {len(self.items)} files  ·  Total Size: {total_mb:.1f} MB  ·  Folder: {rec_dir}"
        )
        self._render_rows()

    def _render_rows(self):
        for child in self.scroll_frame.winfo_children():
            child.destroy()

        if not self.filtered_items:
            empty_box = ctk.CTkFrame(self.scroll_frame, fg_color=OmniTheme.BG_CARD, corner_radius=OmniTheme.RADIUS_CARD)
            empty_box.pack(fill="x", pady=40, padx=20)
            ctk.CTkLabel(
                empty_box,
                text="No recordings found in library",
                font=OmniTheme.font_section(),
                text_color=OmniTheme.TEXT_MUTED
            ).pack(pady=(24, 4))
            ctk.CTkLabel(
                empty_box,
                text="Captures and screen recordings will automatically appear here.",
                font=OmniTheme.font_label(),
                text_color=OmniTheme.TEXT_DIM
            ).pack(pady=(0, 24))
            return

        for it in self.filtered_items:
            row = ctk.CTkFrame(
                self.scroll_frame,
                fg_color=OmniTheme.BG_CARD,
                border_width=1,
                border_color=OmniTheme.BORDER_SUBTLE,
                corner_radius=OmniTheme.RADIUS_CONTROL
            )
            row.pack(fill="x", pady=3)

            # Metadata column
            col = ctk.CTkFrame(row, fg_color="transparent")
            col.pack(side="left", fill="x", expand=True, padx=12, pady=8)

            name_row = ctk.CTkFrame(col, fg_color="transparent")
            name_row.pack(fill="x")

            # Tag badge
            tag_badge = ctk.CTkLabel(
                name_row,
                text=it["tag"],
                font=ctk.CTkFont(size=9, weight="bold"),
                fg_color=OmniTheme.BG_INPUT,
                text_color=OmniTheme.ACCENT_PRIMARY,
                corner_radius=OmniTheme.RADIUS_CONTROL,
                padx=6,
                pady=1
            )
            tag_badge.pack(side="left", padx=(0, 8))

            ctk.CTkLabel(
                name_row,
                text=it["name"],
                font=ctk.CTkFont(family="Consolas", size=11, weight="bold"),
                text_color=OmniTheme.TEXT_MAIN
            ).pack(side="left")

            meta_lbl = ctk.CTkLabel(
                col,
                text=f"Modified: {it['mtime_str']}   ·   Size: {it['size_str']}",
                font=OmniTheme.font_label(),
                text_color=OmniTheme.TEXT_MUTED
            )
            meta_lbl.pack(anchor="w", pady=(2, 0))

            # Row Action Buttons
            btn_box = ctk.CTkFrame(row, fg_color="transparent")
            btn_box.pack(side="right", padx=10, pady=8)

            # 1. Play
            ctk.CTkButton(
                btn_box,
                text="Play",
                width=55,
                height=26,
                font=OmniTheme.font_label(),
                fg_color=OmniTheme.ACCENT_PRIMARY,
                hover_color=OmniTheme.ACCENT_PRIMARY_HOVER,
                corner_radius=OmniTheme.RADIUS_CONTROL,
                command=lambda p=it["path"]: self.controller.open_recording_file(p)
            ).pack(side="left", padx=3)

            # 2. Reveal in Explorer
            ctk.CTkButton(
                btn_box,
                text="Explorer",
                width=65,
                height=26,
                font=OmniTheme.font_label(),
                fg_color=OmniTheme.BG_INPUT,
                hover_color=OmniTheme.BG_CARD_HOVER,
                corner_radius=OmniTheme.RADIUS_CONTROL,
                command=lambda p=it["path"]: self._reveal_in_explorer(p)
            ).pack(side="left", padx=3)

            # 3. Upload to Google Drive
            ctk.CTkButton(
                btn_box,
                text="Upload",
                width=60,
                height=26,
                font=OmniTheme.font_label(),
                fg_color=OmniTheme.BG_INPUT,
                hover_color=OmniTheme.BG_CARD_HOVER,
                corner_radius=OmniTheme.RADIUS_CONTROL,
                command=lambda p=it["path"]: self._upload_to_drive(p)
            ).pack(side="left", padx=3)

            # 4. Delete
            ctk.CTkButton(
                btn_box,
                text="Delete",
                width=55,
                height=26,
                font=OmniTheme.font_label(),
                fg_color="transparent",
                hover_color=OmniTheme.STATUS_RECORDING,
                text_color=OmniTheme.TEXT_MUTED,
                corner_radius=OmniTheme.RADIUS_CONTROL,
                command=lambda p=it["path"], n=it["name"]: self._confirm_delete(p, n)
            ).pack(side="left", padx=3)

    def _reveal_in_explorer(self, path: Path):
        try:
            if os.name == "nt":
                subprocess.Popen(f'explorer /select,"{path.resolve()}"')
        except Exception:
            pass

    def _upload_to_drive(self, path: Path):
        ok, msg = self.controller.uploader.upload_file(str(path))
        if self.on_toast:
            self.on_toast(
                "Cloud Upload",
                f"{path.name}: {msg}",
                level="success" if ok else "warning"
            )

    def _confirm_delete(self, path: Path, filename: str):
        if messagebox.askyesno("Confirm Delete", f"Are you sure you want to delete:\n\n{filename}\n\nThis cannot be undone.", parent=self):
            try:
                if path.exists():
                    path.unlink()
                self._load_recordings()
                if self.on_toast:
                    self.on_toast("File Deleted", f"Removed {filename}", level="info")
            except Exception as e:
                messagebox.showerror("Delete Failed", f"Could not delete file:\n{e}", parent=self)
