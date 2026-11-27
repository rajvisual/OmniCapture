from typing import Optional, Callable, Dict, Any
import tkinter as tk
import customtkinter as ctk

from gui.theme import OmniTheme, ThemeTokens
from gui.components.button import StudioButton
from gui.components.icons import get_icon

class StudioStateBanner(ctk.CTkFrame):
    """
    Standard Windows 11 State Banner & Error Card for OmniCapture Studio.
    Implements the complete State Matrix:
    - What happened (plain-language summary)
    - Why it happened (context/cause)
    - One-click primary fix action button
    - 'Copy details' clipboard action (no raw exception text in main UI)
    - Seamless Light and Dark theme adaptation
    """

    STATE_PRESETS = {
        "no_device": {
            "level": "warning",
            "title": "No Android Device Detected",
            "desc": "Connect your Android phone via USB cable or ensure Wi-Fi ADB is active.",
            "action_text": "Setup Guide",
            "details": "ADB Error: 0 devices attached to host controller. Verified ports: USB 1.1-3.2."
        },
        "scanning": {
            "level": "info",
            "title": "Scanning Hardware Bus...",
            "desc": "Polling USB ports and local network for ADB targets.",
            "action_text": "Refresh",
            "details": "Executing: adb devices -l on local daemon."
        },
        "connecting": {
            "level": "info",
            "title": "Establishing Device Link...",
            "desc": "Negotiating DirectShow Camera2 stream with Android daemon.",
            "action_text": "Cancel",
            "details": "Handshake in progress with scrcpy server v3.3.4."
        },
        "unauthorized": {
            "level": "error",
            "title": "Device Unauthorized (RSA Prompt)",
            "desc": "Unlock your phone screen and tap 'Allow USB Debugging' (check 'Always allow').",
            "action_text": "Check Again",
            "details": "Device reports state 'unauthorized'. RSA key confirmation dialog is pending on phone display."
        },
        "camera_locked": {
            "level": "warning",
            "title": "Camera Sensor Busy",
            "desc": "Another app on the phone (e.g. Google Camera) is holding the Camera2 hardware lock.",
            "action_text": "Release Lock",
            "details": "Camera2 device busy: Active client holding sensor resource. Run adb shell am force-stop."
        },
        "connected_usb": {
            "level": "success",
            "title": "High-Speed USB Connected",
            "desc": "Direct 1080p60 Camera2 pipeline is ready with ultra-low latency.",
            "action_text": "Start Mirror",
            "details": "USB 3.0 transport verified. Target: POCO X6 Pro (Android 14, SDK 34)."
        },
        "connected_wifi": {
            "level": "info",
            "title": "Wireless ADB Link Active",
            "desc": "5GHz Wi-Fi stream active at 192.168.1.155:5555. Keep phone near access point.",
            "action_text": "Switch to USB",
            "details": "TCP/IP 5555 connected. Network latency: ~14 ms round-trip."
        },
        "recording": {
            "level": "recording",
            "title": "Broadcast Recording Active",
            "desc": "PC screen and camera sensor streams are recording in parallel at 60 FPS.",
            "action_text": "Stop Recording",
            "details": "Hardware Encoder: MediaFoundation h264_mf MFT active. Container: MP4 (fragmented)."
        },
        "stopping": {
            "level": "info",
            "title": "Finalizing Recording Files...",
            "desc": "Flushing MP4 index atoms and synchronizing dual audio tracks to disk.",
            "action_text": "Please Wait",
            "details": "FFmpeg subprocess closing muxer cleanly with duration header."
        },
        "device_unplugged": {
            "level": "error",
            "title": "Device Detached Mid-Recording",
            "desc": "USB connection was interrupted during recording. PC screen recording is continuing safely.",
            "action_text": "Reconnect Cable",
            "details": "USB Bus disconnect signal received. Scrcpy camera worker safely terminated to prevent host hang."
        },
        "disk_nearly_full": {
            "level": "warning",
            "title": "Disk Space Running Low (< 5 GB)",
            "desc": "Recording drive is approaching capacity. Finish current take or switch storage drive.",
            "action_text": "Storage Settings",
            "details": "Drive volume capacity check: Free space is under the 5.0 GB threshold."
        },
        "disk_full": {
            "level": "error",
            "title": "Recording Stopped: Disk Full",
            "desc": "Less than 500 MB remaining on disk. Recording was safely closed to prevent file corruption.",
            "action_text": "Open Library",
            "details": "Emergency safe shutdown triggered: Free space reached critical 500 MB limit."
        },
        "upload_queued": {
            "level": "info",
            "title": "Cloud Upload Queued",
            "desc": "Recording saved locally and placed in background cloud upload queue.",
            "action_text": "View Queue",
            "details": "Queue position: 1. Target destination: Google Drive virtual path."
        },
        "uploading": {
            "level": "info",
            "title": "Uploading to Google Drive...",
            "desc": "Streaming recording file to cloud storage in background.",
            "action_text": "Cancel Upload",
            "details": "Drive REST API v3 chunked upload active."
        },
        "upload_failed": {
            "level": "error",
            "title": "Cloud Upload Failed",
            "desc": "Google Drive upload was interrupted by network timeout or token expiry.",
            "action_text": "Retry Upload",
            "details": "Drive API v3 HTTP 503 Service Unavailable / Socket timeout after 3 chunks. Session cached."
        },
        "upload_done": {
            "level": "success",
            "title": "Cloud Upload Complete",
            "desc": "Recording was successfully uploaded to Google Drive folder.",
            "action_text": "Show in Explorer",
            "details": "File ID: 1aBcDeFgHiJkLmNoPqRsTuVwXyZ. Destination: Google Drive virtual path verified."
        },
        "scrcpy_missing": {
            "level": "error",
            "title": "Scrcpy Binary Not Found",
            "desc": "scrcpy.exe is required for Android display mirroring and Camera2 stream decoding.",
            "action_text": "Install Guide",
            "details": "resolve_binary('scrcpy') failed across system PATH and bin/ directory. Minimum version 2.0+ required."
        },
        "adb_missing": {
            "level": "error",
            "title": "ADB Binary Not Found",
            "desc": "Android Debug Bridge (adb.exe) is required for device discovery and telemetry.",
            "action_text": "Install Guide",
            "details": "resolve_binary('adb') failed across system PATH and bin/ directory. Install Android SDK Platform-Tools."
        },
        "engine_crashed": {
            "level": "error",
            "title": "Capture Engine Crashed Abruptly",
            "desc": "An underlying video capture subprocess crashed unexpectedly with a non-zero exit code.",
            "action_text": "Restart Engine",
            "details": "Subprocess worker exited unexpectedly with code 0xC0000005 (Access Violation in Direct3D11 graphics driver)."
        },
        "ffmpeg_missing": {
            "level": "error",
            "title": "FFmpeg Engine Not Found",
            "desc": "FFmpeg is required for PC screen video capture and hardware encoder dispatch.",
            "action_text": "Install Guide",
            "details": "resolve_binary('ffmpeg') failed across system PATH and bin/ directory."
        },
        "permission_denied": {
            "level": "error",
            "title": "Storage Access Denied",
            "desc": "OmniCapture lacks write permission for the selected output folder.",
            "action_text": "Change Folder",
            "details": "OS Error 13: Permission denied while attempting to create recording lock file."
        }
    }

    def __init__(
        self,
        parent,
        initial_state: str = "no_device",
        on_action: Optional[Callable[[str], None]] = None,
        on_copy_details: Optional[Callable[[str], None]] = None,
        on_dismiss: Optional[Callable[[], None]] = None,
        **kwargs
    ):
        tokens = OmniTheme.get_tokens()
        super().__init__(
            parent,
            fg_color=tokens.bg_raised,
            border_width=1,
            border_color=tokens.border_subtle,
            corner_radius=OmniTheme.RADIUS_POPUP,
            **kwargs
        )

        self.current_state = initial_state
        self.on_action = on_action
        self.on_copy_details = on_copy_details
        self.on_dismiss = on_dismiss
        self.current_details = ""

        self._build_ui(tokens)
        self.set_state(initial_state)

    def _build_ui(self, tokens: ThemeTokens):
        # Left status accent pillar
        self.pillar = ctk.CTkFrame(self, width=4, corner_radius=2, fg_color=tokens.accent_primary)
        self.pillar.pack(side="left", fill="y", padx=(6, 8), pady=6)

        # Content column
        content = ctk.CTkFrame(self, fg_color="transparent")
        content.pack(side="left", fill="both", expand=True, pady=6)

        self.title_lbl = ctk.CTkLabel(
            content,
            text="",
            font=OmniTheme.font_body_bold(),
            text_color=tokens.text_primary,
            anchor="w"
        )
        self.title_lbl.pack(anchor="w")

        self.desc_lbl = ctk.CTkLabel(
            content,
            text="",
            font=OmniTheme.font_caption(),
            text_color=tokens.text_secondary,
            anchor="w",
            wraplength=480
        )
        self.desc_lbl.pack(anchor="w", pady=(1, 0))

        # Actions row on right
        actions = ctk.CTkFrame(self, fg_color="transparent")
        actions.pack(side="right", padx=(8, 10), pady=6)

        self.action_btn = StudioButton(
            actions,
            text="Action",
            variant="secondary",
            size="small",
            command=self._handle_action
        )
        self.action_btn.pack(side="right", padx=(4, 0))

        self.copy_btn = ctk.CTkButton(
            actions,
            text="Copy details",
            width=76,
            height=28,
            font=OmniTheme.font_caption(),
            fg_color="transparent",
            hover_color=tokens.bg_hover,
            text_color=tokens.accent_primary,
            command=self._handle_copy_details
        )
        self.copy_btn.pack(side="right", padx=(0, 4))

    def get_details(self) -> str:
        """Return formatted diagnostic details string for clipboard / diagnostics."""
        preset = self.STATE_PRESETS.get(self.current_state, {})
        title = preset.get("title", self.current_state)
        return f"OmniCapture Diagnostics [{self.current_state}] - {title}\n{self.current_details}"

    def set_state(self, state_name: str, custom_desc: Optional[str] = None, custom_details: Optional[str] = None):
        """Update banner content to reflect any state in the State Matrix."""
        self.current_state = state_name
        tokens = OmniTheme.get_tokens()
        preset = self.STATE_PRESETS.get(state_name, self.STATE_PRESETS["no_device"])

        level = preset["level"]
        title = preset["title"]
        desc = custom_desc or preset["desc"]
        action_text = preset["action_text"]
        self.current_details = custom_details or preset["details"]

        # Color-code left pillar according to semantic level
        if level == "error":
            pillar_color = tokens.status_recording
        elif level == "warning":
            pillar_color = tokens.status_warning
        elif level == "success":
            pillar_color = tokens.status_connected
        elif level == "recording":
            pillar_color = tokens.status_recording
        else: # info
            pillar_color = tokens.accent_primary

        self.pillar.configure(fg_color=pillar_color)
        self.title_lbl.configure(text=title)
        self.desc_lbl.configure(text=desc)
        self.action_btn.configure(text=action_text)

    def _handle_action(self):
        if self.on_action:
            self.on_action(self.current_state)

    def _handle_copy_details(self):
        if self.on_copy_details:
            self.on_copy_details(self.current_details)
        else:
            try:
                self.clipboard_clear()
                self.clipboard_append(f"OmniCapture Diagnostics [{self.current_state}]\n{self.current_details}")
                self.copy_btn.configure(text="Copied!")
                self.after(2000, lambda: self.copy_btn.configure(text="Copy details"))
            except Exception:
                pass

    def apply_tokens(self, tokens: ThemeTokens):
        self.configure(fg_color=tokens.bg_raised, border_color=tokens.border_subtle)
        self.title_lbl.configure(text_color=tokens.text_primary)
        self.desc_lbl.configure(text_color=tokens.text_secondary)
        self.copy_btn.configure(text_color=tokens.accent_primary, hover_color=tokens.bg_hover)
        self.action_btn.apply_tokens(tokens)
        self.set_state(self.current_state)
