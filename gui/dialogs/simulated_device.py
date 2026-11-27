from typing import Optional, Callable
import customtkinter as ctk

from gui.theme import OmniTheme, ThemeTokens
from gui.components.button import StudioButton
from core.simulated_device import SimulatedADBManager

class SimulatedDeviceControlDialog(ctk.CTkToplevel):
    """
    Developer-only Simulated Device Control Panel.
    Allows testing every hardware and network state in the State Matrix instantly:
    - No device, Scanning, Connecting, Unauthorized
    - Connected USB, Connected Wi-Fi, Camera Locked
    - Low Battery, High Battery, Disconnect Mid-Recording, Slow Latency, I/O Failure
    """

    def __init__(self, parent, sim_engine: SimulatedADBManager, on_state_change: Optional[Callable[[str], None]] = None):
        super().__init__(parent)
        self.sim_engine = sim_engine
        self.on_state_change = on_state_change

        self.title("Developer — Simulated Device Control")
        self.geometry("520x460")
        self.minsize(480, 420)
        self.attributes("-topmost", True)

        tokens = OmniTheme.get_tokens()
        self.configure(fg_color=tokens.bg_root)

        self._build_ui(tokens)

    def _build_ui(self, tokens: ThemeTokens):
        # Header banner
        header = ctk.CTkFrame(self, fg_color=tokens.bg_header, corner_radius=0, height=50)
        header.pack(fill="x")

        title_box = ctk.CTkFrame(header, fg_color="transparent")
        title_box.pack(side="left", padx=16, pady=10)

        ctk.CTkLabel(
            title_box,
            text="Simulated Device Engine",
            font=OmniTheme.font_title(),
            text_color=tokens.text_primary
        ).pack(anchor="w")

        ctk.CTkLabel(
            title_box,
            text="Switch device states to test UI reactivity & error recovery without USB hardware",
            font=OmniTheme.font_caption(),
            text_color=tokens.text_muted
        ).pack(anchor="w")

        badge = ctk.CTkFrame(header, fg_color="#F59E0B", corner_radius=OmniTheme.RADIUS_PILL)
        badge.pack(side="right", padx=16, pady=12)
        ctk.CTkLabel(
            badge,
            text="DEV ONLY",
            font=OmniTheme.font_mono(10),
            text_color="#000000"
        ).pack(padx=8, pady=2)

        # Body: Scrollable list of available states
        body = ctk.CTkScrollableFrame(self, fg_color="transparent")
        body.pack(fill="both", expand=True, padx=16, pady=12)

        self.state_var = ctk.StringVar(value=self.sim_engine.state)

        categories = [
            ("Connection & Discovery", [
                ("connected_usb", "Connected USB 3.0 (POCO X6 Pro)", "Direct Camera2 + D3D11 mirror link ready"),
                ("connected_wifi", "Connected 5GHz Wi-Fi (192.168.1.155:5555)", "Wireless network capture stream"),
                ("scanning", "Scanning for Devices", "Emulates active ADB polling loop"),
                ("connecting", "Connecting / Handshake", "Handshake negotiation in progress"),
                ("no_device", "No Device Attached", "Clean disconnected state (0 devices)"),
            ]),
            ("Hardware & Protocol Errors", [
                ("unauthorized", "Unauthorized (RSA Confirmation Pending)", "Prompts user to accept RSA key on phone"),
                ("camera_locked", "Camera Hardware Locked", "Camera2 held by com.google.android.GoogleCamera"),
                ("unplugged_mid_recording", "Device Detached Mid-Recording", "Simulates abrupt USB cable pull during take"),
                ("battery_low", "Battery Level Low (12%)", "Critical battery telemetry alert"),
                ("slow_response", "High Latency Response (+1.5s delay)", "Simulates slow ADB daemon response"),
                ("failure", "USB Bus I/O Hardware Failure", "Simulates bus reset / driver error"),
            ]),
            ("Cloud & Engine Failure States", [
                ("upload_failed", "Cloud Upload Failed (Timeout)", "Simulates Google Drive upload error with one-click Retry"),
                ("upload_done", "Cloud Upload Complete", "Simulates upload completion with Show in Explorer action"),
                ("scrcpy_missing", "Scrcpy Binary Missing", "Simulates missing scrcpy.exe with installer guidance"),
                ("adb_missing", "ADB Binary Missing", "Simulates missing adb.exe with SDK guidance"),
                ("engine_crashed", "Engine Subprocess Crashed", "Simulates worker crash with Restart Engine & Copy details"),
            ])
        ]

        for cat_name, state_list in categories:
            ctk.CTkLabel(
                body,
                text=cat_name,
                font=OmniTheme.font_section(),
                text_color=tokens.text_primary
            ).pack(anchor="w", pady=(8, 4))

            for state_id, label, desc in state_list:
                row = ctk.CTkFrame(body, fg_color=tokens.bg_panel, corner_radius=OmniTheme.RADIUS_CONTROL)
                row.pack(fill="x", pady=2)

                rb = ctk.CTkRadioButton(
                    row,
                    text=label,
                    variable=self.state_var,
                    value=state_id,
                    font=OmniTheme.font_body_bold(),
                    text_color=tokens.text_primary,
                    command=lambda s=state_id: self._select_state(s)
                )
                rb.pack(anchor="w", padx=12, pady=(8, 2))

                ctk.CTkLabel(
                    row,
                    text=desc,
                    font=OmniTheme.font_caption(),
                    text_color=tokens.text_muted
                ).pack(anchor="w", padx=36, pady=(0, 8))

        # Bottom actions
        footer = ctk.CTkFrame(self, fg_color=tokens.bg_header, height=44, corner_radius=0)
        footer.pack(fill="x", side="bottom")

        StudioButton(
            footer,
            text="Close",
            variant="secondary",
            size="small",
            command=self.destroy
        ).pack(side="right", padx=16, pady=8)

    def _select_state(self, state_name: str):
        self.sim_engine.set_state(state_name)
        if self.on_state_change:
            self.on_state_change(state_name)
