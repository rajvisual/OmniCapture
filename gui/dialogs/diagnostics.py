from typing import Dict, Any, Optional
import customtkinter as ctk
import tkinter as tk
from tkinter import messagebox

from gui.theme import OmniTheme

class DiagnosticsDialog(ctk.CTkToplevel):
    """
    Technical System & Hardware Diagnostics Dialog.
    Displays real hardware detection, ADB version, FFmpeg capabilities, and Camera2 sensor states.
    Provides 1-click repair actions (Restart ADB, Release Camera Lock, Copy Report).
    """

    def __init__(self, parent, controller, on_toast: Optional[callable] = None):
        super().__init__(parent)
        self.controller = controller
        self.on_toast = on_toast

        self.title("OmniCapture — System & Device Diagnostics")
        self.geometry("700x560")
        self.minsize(620, 460)
        self.configure(fg_color=OmniTheme.BG_ROOT)

        self._build_ui()
        self._refresh_data()

        self.lift()
        self.focus_force()

    def _build_ui(self):
        # Header strip
        header = ctk.CTkFrame(self, fg_color=OmniTheme.BG_DOCK_HEADER, height=44, corner_radius=0)
        header.pack(fill="x")

        ctk.CTkLabel(
            header,
            text="System Diagnostics & Hardware Inspector",
            font=ctk.CTkFont(family="Segoe UI", size=13, weight="bold"),
            text_color=OmniTheme.TEXT_MAIN
        ).pack(side="left", padx=16, pady=10)

        # Quick Actions in Header
        act_box = ctk.CTkFrame(header, fg_color="transparent")
        act_box.pack(side="right", padx=16, pady=8)

        ctk.CTkButton(
            act_box,
            text="Copy Report",
            width=90,
            height=28,
            font=OmniTheme.font_label(),
            fg_color=OmniTheme.BG_INPUT,
            hover_color=OmniTheme.BG_CARD_HOVER,
            corner_radius=OmniTheme.RADIUS_CONTROL,
            command=self._copy_to_clipboard
        ).pack(side="left", padx=4)

        ctk.CTkButton(
            act_box,
            text="Refresh",
            width=70,
            height=28,
            font=OmniTheme.font_label(),
            fg_color=OmniTheme.BG_INPUT,
            hover_color=OmniTheme.BG_CARD_HOVER,
            corner_radius=OmniTheme.RADIUS_CONTROL,
            command=self._refresh_data
        ).pack(side="left", padx=4)

        # Body Scrollable Frame
        self.body = ctk.CTkScrollableFrame(self, fg_color="transparent")
        self.body.pack(fill="both", expand=True, padx=16, pady=12)

        # Footer Action Strip (Hardware repair actions)
        footer = ctk.CTkFrame(self, fg_color=OmniTheme.BG_DOCK, height=52, corner_radius=0)
        footer.pack(fill="x", side="bottom")

        ctk.CTkButton(
            footer,
            text="Release Camera Sensor Lock",
            width=190,
            height=32,
            font=OmniTheme.font_body(),
            fg_color=OmniTheme.BG_INPUT,
            hover_color=OmniTheme.BG_CARD_HOVER,
            corner_radius=OmniTheme.RADIUS_CONTROL,
            command=self._release_camera_lock
        ).pack(side="left", padx=16, pady=10)

        ctk.CTkButton(
            footer,
            text="Restart ADB Server",
            width=140,
            height=32,
            font=OmniTheme.font_body(),
            fg_color=OmniTheme.BG_INPUT,
            hover_color=OmniTheme.BG_CARD_HOVER,
            corner_radius=OmniTheme.RADIUS_CONTROL,
            command=self._restart_adb
        ).pack(side="left", padx=4, pady=10)

        ctk.CTkButton(
            footer,
            text="Close",
            width=80,
            height=32,
            font=OmniTheme.font_body(),
            fg_color=OmniTheme.BG_INPUT,
            hover_color=OmniTheme.BG_CARD_HOVER,
            corner_radius=OmniTheme.RADIUS_CONTROL,
            command=self.destroy
        ).pack(side="right", padx=16, pady=10)

    def _refresh_data(self):
        for child in self.body.winfo_children():
            child.destroy()

        diag = self.controller.query_diagnostics()
        cached = self.controller.get_cached_device()

        # Section 1: Connected Android Device
        self._add_card(
            "Android Hardware Device",
            [
                ("Status", cached.get("status", "Unknown")),
                ("Device Model", cached.get("model", "No Device")),
                ("Serial / ID", cached.get("device_id") or "None"),
                ("Connection Mode", "Wi-Fi TCP/IP" if cached.get("is_wireless") else "USB Direct (Low-Latency)"),
                ("Battery", cached.get("battery", {}).get("level", "N/A")),
                ("Wi-Fi IP Address", cached.get("wifi_ip") or "Not connected to Wi-Fi"),
            ]
        )

        # Section 2: Core Subsystem Binaries
        self._add_card(
            "Core Execution Subsystems",
            [
                ("ADB Path", diag.get("adb_path", "Not set")),
                ("ADB Version", diag.get("adb_version", "Unknown")),
                ("Scrcpy Path", diag.get("scrcpy_path", "Not set")),
                ("Scrcpy Ready", "Installed & Verified" if diag.get("scrcpy_ready") else "Missing"),
                ("FFmpeg Path", diag.get("ffmpeg_path", "Not found")),
                ("FFmpeg Version", diag.get("ffmpeg_version", "Not found")),
                ("FFmpeg Available", "Yes (Hardware accelerated)" if diag.get("ffmpeg_available") else "No"),
            ]
        )

        # Section 3: Android Camera2 Sensor Telemetry
        self._add_text_card(
            "Android Camera2 Sensors & Modes",
            str(diag.get("cameras_info", "No device attached"))
        )

    def _add_card(self, title: str, rows: list):
        ctk.CTkLabel(
            self.body,
            text=title.upper(),
            font=OmniTheme.font_section(),
            text_color=OmniTheme.TEXT_MUTED
        ).pack(anchor="w", padx=2, pady=(10, 4))

        card = ctk.CTkFrame(self.body, fg_color=OmniTheme.BG_CARD, corner_radius=OmniTheme.RADIUS_CONTROL)
        card.pack(fill="x", pady=2)

        for label, val in rows:
            r = ctk.CTkFrame(card, fg_color="transparent")
            r.pack(fill="x", padx=12, pady=4)

            ctk.CTkLabel(
                r,
                text=label,
                font=OmniTheme.font_body(),
                text_color=OmniTheme.TEXT_MUTED,
                width=160,
                anchor="w"
            ).pack(side="left")

            ctk.CTkLabel(
                r,
                text=str(val),
                font=OmniTheme.font_mono(10),
                text_color=OmniTheme.TEXT_MAIN,
                anchor="w"
            ).pack(side="left", fill="x", expand=True)

    def _add_text_card(self, title: str, text_content: str):
        ctk.CTkLabel(
            self.body,
            text=title.upper(),
            font=OmniTheme.font_section(),
            text_color=OmniTheme.TEXT_MUTED
        ).pack(anchor="w", padx=2, pady=(10, 4))

        card = ctk.CTkFrame(self.body, fg_color=OmniTheme.BG_CARD, corner_radius=OmniTheme.RADIUS_CONTROL)
        card.pack(fill="x", pady=2)

        txt = ctk.CTkTextbox(
            card,
            height=110,
            font=OmniTheme.font_mono(9),
            fg_color="transparent",
            text_color=OmniTheme.TEXT_BODY
        )
        txt.pack(fill="both", expand=True, padx=8, pady=6)
        txt.insert("1.0", text_content)
        txt.configure(state="disabled")

    def _copy_to_clipboard(self):
        diag = self.controller.query_diagnostics()
        cached = self.controller.get_cached_device()
        report = (
            f"=== OMNICAPTURE STUDIO DIAGNOSTICS REPORT ===\n"
            f"Device: {cached.get('model')} (Status: {cached.get('status')})\n"
            f"ADB: {diag.get('adb_path')} [{diag.get('adb_version')}]\n"
            f"Scrcpy: {diag.get('scrcpy_path')}\n"
            f"FFmpeg: {diag.get('ffmpeg_path')} [{diag.get('ffmpeg_version')}]\n"
            f"Camera Info:\n{diag.get('cameras_info')}\n"
        )
        self.clipboard_clear()
        self.clipboard_append(report)
        if self.on_toast:
            self.on_toast("Copied", "Diagnostics report copied to clipboard.", level="info")

    def _release_camera_lock(self):
        ok, msg = self.controller.release_camera_lock()
        if self.on_toast:
            self.on_toast("Camera Sensor", msg, level="success" if ok else "warning")
        self._refresh_data()

    def _restart_adb(self):
        self.controller.adb.restart_server()
        self.controller.refresh_device_now()
        if self.on_toast:
            self.on_toast("ADB Subsystem", "ADB daemon restarted.", level="info")
        self._refresh_data()
