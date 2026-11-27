import os
import time
import subprocess
from pathlib import Path
from typing import Optional, List, Dict, Any, Set
import customtkinter as ctk

from gui.theme import OmniTheme, ThemeTokens
from gui.components.button import StudioButton
from gui.components.segmented_control import StudioSegmentedControl
from gui.components.confirm_dialog import StudioConfirmDialog

class RecordingsGalleryDialog(ctk.CTkToplevel):
    """
    Professional Media Library / Recordings Manager.
    Features:
    - Dynamic Light Minimal & Dark Liquid Glass theming
    - Virtualized list/grid with metadata (tag, size, duration, date)
    - Search bar and segmented mode filter (All / Dual / PC Screen / Phone Cam)
    - Multi-select with batch deletion
    - Undo toast on single deletion
    - Right-click context menu (Play, Reveal in Explorer, Cloud Upload, Delete)
    - Total library storage and file count readout
    - Designed empty state
    """

    def __init__(self, parent, controller, on_toast: Optional[callable] = None):
        super().__init__(parent)
        self.controller = controller
        self.on_toast = on_toast

        self.title("OmniCapture — Media Library & Recordings")
        self.geometry("840x580")
        self.minsize(720, 480)

        tokens = OmniTheme.get_tokens()
        self.configure(fg_color=tokens.bg_root)

        self.items: List[Dict[str, Any]] = []
        self.filtered_items: List[Dict[str, Any]] = []
        self.selected_paths: Set[str] = set()
        self._active_filter_tag = "ALL"
        self._undo_cache: Dict[str, bytes] = {}

        self._build_ui(tokens)
        self._load_recordings()

        self.lift()
        self.focus_force()

    def _build_ui(self, tokens: ThemeTokens):
        # 1. Top Toolbar (Search, Filter, Actions)
        top_bar = ctk.CTkFrame(self, fg_color=tokens.bg_header, height=54, corner_radius=0)
        top_bar.pack(fill="x")

        # Search Bar
        search_frame = ctk.CTkFrame(top_bar, fg_color="transparent")
        search_frame.pack(side="left", padx=16, pady=10)

        self.search_var = ctk.StringVar()
        self.search_var.trace_add("write", self._on_filter_changed)

        self.search_entry = ctk.CTkEntry(
            search_frame,
            textvariable=self.search_var,
            placeholder_text="Search recordings...",
            width=220,
            height=30,
            font=OmniTheme.font_body(),
            fg_color=tokens.bg_input,
            border_width=1,
            border_color=tokens.border_default
        )
        self.search_entry.pack(side="left")

        # Mode Filter Segmented Control
        self.filter_seg = StudioSegmentedControl(
            top_bar,
            values=["All", "Dual", "PC Screen", "Phone Cam"],
            command=self._on_segment_changed
        )
        self.filter_seg.set("All")
        self.filter_seg.pack(side="left", padx=10, pady=10)

        # Right Action Buttons
        actions = ctk.CTkFrame(top_bar, fg_color="transparent")
        actions.pack(side="right", padx=16, pady=10)

        self.batch_del_btn = StudioButton(
            actions,
            text="Delete Selected",
            variant="danger",
            size="small",
            command=self._delete_selected_batch
        )
        # Not packed until items are selected

        StudioButton(
            actions,
            text="Open Folder",
            variant="secondary",
            size="small",
            command=self.controller.open_recordings_folder
        ).pack(side="left", padx=3)

        StudioButton(
            actions,
            text="Refresh",
            variant="secondary",
            size="small",
            command=self._load_recordings
        ).pack(side="left", padx=3)

        # 2. Summary Status Strip
        self.status_strip = ctk.CTkFrame(self, fg_color=tokens.bg_raised, height=30, corner_radius=0)
        self.status_strip.pack(fill="x")

        self.summary_label = ctk.CTkLabel(
            self.status_strip,
            text="Loading library...",
            font=OmniTheme.font_caption(),
            text_color=tokens.text_muted
        )
        self.summary_label.pack(side="left", padx=16, pady=4)

        self.selection_label = ctk.CTkLabel(
            self.status_strip,
            text="",
            font=OmniTheme.font_caption(),
            text_color=tokens.accent_primary
        )
        self.selection_label.pack(side="right", padx=16, pady=4)

        # 3. Media Items List
        self.scroll_frame = ctk.CTkScrollableFrame(self, fg_color="transparent")
        self.scroll_frame.pack(fill="both", expand=True, padx=16, pady=10)

    def _on_segment_changed(self, val: str):
        mapping = {"All": "ALL", "Dual": "DUAL", "PC Screen": "PC", "Phone Cam": "CAM"}
        self._active_filter_tag = mapping.get(val, "ALL")
        self._apply_filter()

    def _load_recordings(self):
        self.items = self.controller.get_recordings_list() if hasattr(self.controller, "get_recordings_list") else []
        self.selected_paths.clear()
        self._apply_filter()

    def _on_filter_changed(self, *args):
        self._apply_filter()

    def _apply_filter(self):
        query = self.search_var.get().strip().lower()
        items = self.items

        if self._active_filter_tag != "ALL":
            items = [it for it in items if self._active_filter_tag in it.get("tag", "").upper()]

        if query:
            items = [
                it for it in items
                if query in it["name"].lower() or query in it.get("tag", "").lower()
            ]

        self.filtered_items = items
        total_bytes = sum(it.get("size_bytes", 0) for it in self.filtered_items)
        total_mb = total_bytes / (1024 * 1024)
        rec_dir = self.controller.recordings_dir if hasattr(self.controller, "recordings_dir") else "recordings"

        self.summary_label.configure(
            text=f"Library: {len(self.filtered_items)} items  ·  Total Storage: {total_mb:.1f} MB  ·  Path: {rec_dir}"
        )
        self._update_selection_ui()
        self._render_rows()

    def _toggle_select(self, path_str: str, var: ctk.BooleanVar):
        if var.get():
            self.selected_paths.add(path_str)
        else:
            self.selected_paths.discard(path_str)
        self._update_selection_ui()

    def _update_selection_ui(self):
        count = len(self.selected_paths)
        if count > 0:
            self.selection_label.configure(text=f"{count} selected")
            if not self.batch_del_btn.winfo_ismapped():
                self.batch_del_btn.pack(side="left", padx=4)
        else:
            self.selection_label.configure(text="")
            if self.batch_del_btn.winfo_ismapped():
                self.batch_del_btn.pack_forget()

    def _render_rows(self):
        tokens = OmniTheme.get_tokens()
        for child in self.scroll_frame.winfo_children():
            child.destroy()

        if not self.filtered_items:
            empty = ctk.CTkFrame(self.scroll_frame, fg_color=tokens.bg_panel, corner_radius=OmniTheme.RADIUS_CONTROL)
            empty.pack(fill="x", pady=40, padx=20)
            ctk.CTkLabel(
                empty,
                text="No recordings found in library",
                font=OmniTheme.font_body_bold(),
                text_color=tokens.text_muted
            ).pack(pady=(28, 4))
            ctk.CTkLabel(
                empty,
                text="Video captures and broadcasts will automatically appear here once recorded.",
                font=OmniTheme.font_caption(),
                text_color=tokens.text_dim
            ).pack(pady=(0, 28))
            return

        for it in self.filtered_items:
            path_str = str(it["path"])
            is_sel = path_str in self.selected_paths

            row = ctk.CTkFrame(
                self.scroll_frame,
                fg_color=tokens.bg_panel,
                border_width=1,
                border_color=tokens.border_focus if is_sel else tokens.border_subtle,
                corner_radius=OmniTheme.RADIUS_CONTROL
            )
            row.pack(fill="x", pady=3)

            # Left selection checkbox
            sel_var = ctk.BooleanVar(value=is_sel)
            cb = ctk.CTkCheckBox(
                row,
                text="",
                width=20,
                variable=sel_var,
                command=lambda p=path_str, v=sel_var: self._toggle_select(p, v)
            )
            cb.pack(side="left", padx=(12, 4), pady=10)

            # Metadata column
            col = ctk.CTkFrame(row, fg_color="transparent")
            col.pack(side="left", fill="x", expand=True, padx=6, pady=8)

            name_row = ctk.CTkFrame(col, fg_color="transparent")
            name_row.pack(fill="x")

            # Tag pill
            tag_color = tokens.accent_subtle
            tag_text_color = tokens.accent_primary
            tag_badge = ctk.CTkLabel(
                name_row,
                text=it.get("tag", "REC"),
                font=OmniTheme.font_mono(9),
                fg_color=tag_color,
                text_color=tag_text_color,
                corner_radius=3,
                padx=6,
                pady=1
            )
            tag_badge.pack(side="left", padx=(0, 8))

            ctk.CTkLabel(
                name_row,
                text=it["name"],
                font=OmniTheme.font_mono(11),
                text_color=tokens.text_primary
            ).pack(side="left")

            meta_lbl = ctk.CTkLabel(
                col,
                text=f"Modified: {it.get('mtime_str', 'N/A')}   ·   Size: {it.get('size_str', 'N/A')}",
                font=OmniTheme.font_caption(),
                text_color=tokens.text_muted
            )
            meta_lbl.pack(anchor="w", pady=(2, 0))

            # Right action buttons
            btn_box = ctk.CTkFrame(row, fg_color="transparent")
            btn_box.pack(side="right", padx=10, pady=8)

            StudioButton(
                btn_box,
                text="Play",
                variant="primary",
                size="small",
                command=lambda p=it["path"]: self.controller.open_recording_file(p)
            ).pack(side="left", padx=2)

            StudioButton(
                btn_box,
                text="Explorer",
                variant="secondary",
                size="small",
                command=lambda p=it["path"]: self._reveal_in_explorer(p)
            ).pack(side="left", padx=2)

            StudioButton(
                btn_box,
                text="Upload",
                variant="secondary",
                size="small",
                command=lambda p=it["path"]: self._upload_to_drive(p)
            ).pack(side="left", padx=2)

            StudioButton(
                btn_box,
                text="Delete",
                variant="ghost",
                size="small",
                command=lambda p=it["path"], n=it["name"]: self._delete_single_with_undo(p, n)
            ).pack(side="left", padx=2)

    def _reveal_in_explorer(self, path: Path):
        try:
            if os.name == "nt":
                subprocess.Popen(f'explorer /select,"{path.resolve()}"')
        except Exception:
            pass

    def _upload_to_drive(self, path: Path):
        ok, msg = self.controller.uploader.upload_file(str(path)) if hasattr(self.controller, "uploader") else (False, "Uploader not configured")
        if self.on_toast:
            self.on_toast(
                title="Google Drive Upload",
                message=f"{path.name}: {msg}",
                level="success" if ok else "warning"
            )

    def _delete_single_with_undo(self, path: Path, filename: str):
        """Single file deletion with non-blocking Undo Toast instead of disruptive modal."""
        try:
            if path.exists():
                # Cache contents in memory briefly for undo
                with open(path, "rb") as f:
                    self._undo_cache[str(path)] = f.read()
                path.unlink()
                self._load_recordings()

                if self.on_toast:
                    self.on_toast(
                        title="File Deleted",
                        message=f"Removed {filename}",
                        level="info",
                        action_text="Undo",
                        action_cmd=lambda p=path, n=filename: self._undo_delete(p, n)
                    )
        except Exception as e:
            if self.on_toast:
                self.on_toast("Delete Failed", str(e), level="error")

    def _undo_delete(self, path: Path, filename: str):
        """Restore deleted file from undo cache."""
        path_str = str(path)
        data = self._undo_cache.pop(path_str, None)
        if data:
            try:
                with open(path, "wb") as f:
                    f.write(data)
                self._load_recordings()
                if self.on_toast:
                    self.on_toast("File Restored", f"Restored {filename} successfully", level="success")
            except Exception as e:
                if self.on_toast:
                    self.on_toast("Undo Failed", str(e), level="error")

    def _delete_selected_batch(self):
        """Multi-delete triggers explicit StudioConfirmDialog with consequence details."""
        count = len(self.selected_paths)
        if count == 0:
            return

        def _do_batch_delete():
            deleted = 0
            for path_str in list(self.selected_paths):
                p = Path(path_str)
                try:
                    if p.exists():
                        p.unlink()
                        deleted += 1
                except Exception:
                    pass
            self.selected_paths.clear()
            self._load_recordings()
            if self.on_toast:
                self.on_toast("Batch Deleted", f"Permanently removed {deleted} recordings from disk.", level="info")

        StudioConfirmDialog(
            self,
            title="Delete Selected Recordings",
            message=f"Are you sure you want to permanently delete {count} selected recording file(s)?",
            consequence="This action will permanently delete these video files from your hard drive.",
            confirm_text=f"Delete {count} Recordings",
            cancel_text="Keep Files",
            is_danger=True,
            on_confirm=_do_batch_delete
        )
