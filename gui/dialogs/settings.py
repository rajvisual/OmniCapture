from pathlib import Path
from typing import Dict, Any, Optional
import customtkinter as ctk
from tkinter import filedialog, messagebox

from gui.theme import OmniTheme

class StudioSettingsDialog(ctk.CTkToplevel):
    """
    Comprehensive Studio Settings & Preferences Window.
    Features:
    - Capture defaults (format MP4/MKV, frame rate, video bitrate)
    - Hardware input preferences (UHID toggle, auto screen-off)
    - Storage location with native Windows folder picker
    - Google Drive Desktop virtual drive sync status
    - System tray & global hotkeys toggles
    """

    def __init__(
        self,
        parent,
        config: Dict[str, Any],
        controller,
        minimize_to_tray_var: ctk.BooleanVar,
        enable_hotkeys_var: ctk.BooleanVar,
        on_save_callback: Optional[callable] = None,
        on_toast: Optional[callable] = None
    ):
        super().__init__(parent)
        self.config = config
        self.controller = controller
        self.minimize_to_tray_var = minimize_to_tray_var
        self.enable_hotkeys_var = enable_hotkeys_var
        self.on_save_callback = on_save_callback
        self.on_toast = on_toast

        self.title("OmniCapture — Studio Preferences")
        self.geometry("620x560")
        self.resizable(False, False)
        self.configure(fg_color=OmniTheme.BG_ROOT)

        self._build_ui()
        self.lift()
        self.focus_force()

    def _build_ui(self):
        # Header strip
        header = ctk.CTkFrame(self, fg_color=OmniTheme.BG_DOCK_HEADER, height=44, corner_radius=0)
        header.pack(fill="x")
        ctk.CTkLabel(
            header,
            text="Preferences",
            font=ctk.CTkFont(family="Segoe UI", size=13, weight="bold"),
            text_color=OmniTheme.TEXT_MAIN
        ).pack(side="left", padx=16, pady=10)

        # Main Scrollable Settings Container
        body = ctk.CTkScrollableFrame(self, fg_color="transparent")
        body.pack(fill="both", expand=True, padx=16, pady=12)

        # ---------------------------------------------------------------------
        # 1. Video & Recording Defaults
        # ---------------------------------------------------------------------
        self._build_section_header(body, "Video & Capture Defaults")

        row1 = ctk.CTkFrame(body, fg_color=OmniTheme.BG_CARD, corner_radius=OmniTheme.RADIUS_CONTROL)
        row1.pack(fill="x", pady=4)
        c1 = ctk.CTkFrame(row1, fg_color="transparent")
        c1.pack(fill="x", padx=14, pady=10)

        ctk.CTkLabel(c1, text="Default Container Format", font=OmniTheme.font_body(), text_color=OmniTheme.TEXT_MAIN).pack(anchor="w")
        self.format_seg = ctk.CTkSegmentedButton(
            c1,
            values=["MP4", "MKV (Crash-Safe)"],
            selected_color=OmniTheme.ACCENT_PRIMARY,
            corner_radius=OmniTheme.RADIUS_CONTROL
        )
        def_fmt = self.config.get("default_record_format", "mp4").upper()
        self.format_seg.set("MKV (Crash-Safe)" if "MKV" in def_fmt else "MP4")
        self.format_seg.pack(fill="x", pady=(4, 10))

        ctk.CTkLabel(c1, text="Capture Frame Rate", font=OmniTheme.font_body(), text_color=OmniTheme.TEXT_MAIN).pack(anchor="w")
        self.fps_seg = ctk.CTkSegmentedButton(
            c1,
            values=["30 FPS", "60 FPS"],
            selected_color=OmniTheme.ACCENT_PRIMARY,
            corner_radius=OmniTheme.RADIUS_CONTROL
        )
        self.fps_seg.set("60 FPS" if self.config.get("max_fps", 60) == 60 else "30 FPS")
        self.fps_seg.pack(fill="x", pady=(4, 4))

        # ---------------------------------------------------------------------
        # 2. Output Storage & Folder Location
        # ---------------------------------------------------------------------
        self._build_section_header(body, "Output Storage & Recordings Directory")

        row2 = ctk.CTkFrame(body, fg_color=OmniTheme.BG_CARD, corner_radius=OmniTheme.RADIUS_CONTROL)
        row2.pack(fill="x", pady=4)
        c2 = ctk.CTkFrame(row2, fg_color="transparent")
        c2.pack(fill="x", padx=14, pady=10)

        ctk.CTkLabel(c2, text="Saved Recordings Path", font=OmniTheme.font_body(), text_color=OmniTheme.TEXT_MAIN).pack(anchor="w")

        dir_box = ctk.CTkFrame(c2, fg_color="transparent")
        dir_box.pack(fill="x", pady=(4, 6))

        self.path_var = ctk.StringVar(value=str(self.controller.recordings_dir))
        self.path_entry = ctk.CTkEntry(
            dir_box,
            textvariable=self.path_var,
            font=OmniTheme.font_mono(10),
            fg_color=OmniTheme.BG_INPUT,
            height=30
        )
        self.path_entry.pack(side="left", fill="x", expand=True, padx=(0, 8))

        ctk.CTkButton(
            dir_box,
            text="Browse...",
            width=80,
            height=30,
            font=OmniTheme.font_body(),
            fg_color=OmniTheme.BG_INPUT,
            hover_color=OmniTheme.BG_CARD_HOVER,
            corner_radius=OmniTheme.RADIUS_CONTROL,
            command=self._browse_recordings_dir
        ).pack(side="right")

        # ---------------------------------------------------------------------
        # 3. System Behavior & Tray
        # ---------------------------------------------------------------------
        self._build_section_header(body, "Appearance & Desktop Integration")

        row3 = ctk.CTkFrame(body, fg_color=OmniTheme.BG_CARD, corner_radius=OmniTheme.RADIUS_CONTROL)
        row3.pack(fill="x", pady=4)
        c3 = ctk.CTkFrame(row3, fg_color="transparent")
        c3.pack(fill="x", padx=14, pady=10)

        ctk.CTkLabel(c3, text="Theme Appearance", font=OmniTheme.font_body(), text_color=OmniTheme.TEXT_MAIN).pack(anchor="w")
        self.theme_seg = ctk.CTkSegmentedButton(
            c3,
            values=["Dark Liquid Glass", "Light Minimal"],
            selected_color=OmniTheme.ACCENT_PRIMARY,
            corner_radius=OmniTheme.RADIUS_CONTROL
        )
        curr_theme = OmniTheme.get_tokens().name
        self.theme_seg.set("Dark Liquid Glass" if curr_theme == "dark" else "Light Minimal")
        self.theme_seg.pack(fill="x", pady=(4, 10))

        ctk.CTkSwitch(
            c3,
            text="Minimize to Windows System Tray on close",
            variable=self.minimize_to_tray_var,
            font=OmniTheme.font_body(),
            progress_color=OmniTheme.ACCENT_PRIMARY
        ).pack(anchor="w", pady=4)

        ctk.CTkSwitch(
            c3,
            text="Enable global system hotkeys (Ctrl+Alt+D, Ctrl+Alt+M)",
            variable=self.enable_hotkeys_var,
            font=OmniTheme.font_body(),
            progress_color=OmniTheme.ACCENT_PRIMARY
        ).pack(anchor="w", pady=4)

        # ---------------------------------------------------------------------
        # 4. Google Drive Cloud Integration
        # ---------------------------------------------------------------------
        self._build_section_header(body, "Google Drive Auto-Sync")

        row4 = ctk.CTkFrame(body, fg_color=OmniTheme.BG_CARD, corner_radius=OmniTheme.RADIUS_CONTROL)
        row4.pack(fill="x", pady=4)
        c4 = ctk.CTkFrame(row4, fg_color="transparent")
        c4.pack(fill="x", padx=14, pady=10)

        drive_target = self.controller.uploader.desktop_sync_path or "Auto-detecting virtual drive (G:\\My Drive)"
        ctk.CTkLabel(c4, text=f"Target: {drive_target}", font=OmniTheme.font_label(), text_color=OmniTheme.TEXT_MUTED).pack(anchor="w")

        # 5. Footer Buttons
        footer = ctk.CTkFrame(self, fg_color=OmniTheme.BG_DOCK, height=50, corner_radius=0)
        footer.pack(fill="x", side="bottom")

        ctk.CTkButton(
            footer,
            text="Save Preferences",
            width=130,
            height=32,
            font=OmniTheme.font_section(),
            fg_color=OmniTheme.ACCENT_PRIMARY,
            hover_color=OmniTheme.ACCENT_PRIMARY_HOVER,
            corner_radius=OmniTheme.RADIUS_CONTROL,
            command=self._save_preferences
        ).pack(side="right", padx=16, pady=9)

        ctk.CTkButton(
            footer,
            text="Cancel",
            width=80,
            height=32,
            font=OmniTheme.font_body(),
            fg_color=OmniTheme.BG_INPUT,
            hover_color=OmniTheme.BG_CARD_HOVER,
            corner_radius=OmniTheme.RADIUS_CONTROL,
            command=self.destroy
        ).pack(side="right", padx=6, pady=9)

    def _build_section_header(self, parent, text: str):
        ctk.CTkLabel(
            parent,
            text=text.upper(),
            font=OmniTheme.font_section(),
            text_color=OmniTheme.TEXT_MUTED
        ).pack(anchor="w", padx=2, pady=(12, 4))

    def _browse_recordings_dir(self):
        chosen = filedialog.askdirectory(
            initialdir=self.path_var.get(),
            title="Select Recordings Directory",
            parent=self
        )
        if chosen:
            self.path_var.set(chosen)

    def _save_preferences(self):
        new_dir = Path(self.path_var.get().strip())
        if not new_dir.exists():
            try:
                new_dir.mkdir(parents=True, exist_ok=True)
            except Exception as e:
                messagebox.showerror("Invalid Directory", f"Could not create selected folder:\n{e}", parent=self)
                return

        # Update controller and config
        self.controller.recordings_dir = new_dir
        fmt_val = "mkv" if "MKV" in self.format_seg.get() else "mp4"
        self.config["default_record_format"] = fmt_val
        self.config["max_fps"] = 60 if "60" in self.fps_seg.get() else 30

        # Update Theme
        theme_choice = "dark" if "Dark" in self.theme_seg.get() else "light"
        self.config["theme"] = theme_choice
        OmniTheme.set_theme(theme_choice)

        if self.on_save_callback:
            self.on_save_callback()

        if self.on_toast:
            self.on_toast("Preferences Saved", "Studio configuration successfully updated.", level="success")

        self.destroy()
