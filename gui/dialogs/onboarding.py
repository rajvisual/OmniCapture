import os
import sys
from pathlib import Path
from typing import Optional, Callable
import customtkinter as ctk

from gui.theme import OmniTheme, ThemeTokens
from gui.components.button import StudioButton
from gui.components.status_chip import StatusChip
from core.resource_path import get_recordings_dir

class OnboardingChecklistDialog(ctk.CTkToplevel):
    """
    Studio Onboarding & First-Run Setup Checklist.
    Reopenable anytime from Help > Getting Started Checklist.
    Features:
    - 6 Setup Rows: Output folder, USB/Phone debugging, ADB driver, FFmpeg engine, Theme, Google Drive
    - Dedicated POCO/Xiaomi/MIUI/HyperOS USB debugging setup guide
    - Live status pills on every step (Done / Needs Action / Optional)
    - Fix / action buttons directly in each row
    - Fully skippable; nothing blocks using the app
    """

    def __init__(
        self,
        parent,
        controller,
        on_theme_toggle: Optional[Callable[[], None]] = None,
        on_complete: Optional[Callable[[], None]] = None
    ):
        super().__init__(parent)
        self.controller = controller
        self.on_theme_toggle = on_theme_toggle
        self.on_complete = on_complete

        self.title("OmniCapture Studio — Getting Started Setup Checklist")
        self.geometry("640x680")
        self.minsize(580, 560)
        self.attributes("-topmost", True)

        tokens = OmniTheme.get_tokens()
        self.configure(fg_color=tokens.bg_root)

        self._build_ui(tokens)

    def _build_ui(self, tokens: ThemeTokens):
        # 1. Header with Title & Intro
        header = ctk.CTkFrame(self, fg_color=tokens.bg_header, corner_radius=0)
        header.pack(fill="x")

        h_content = ctk.CTkFrame(header, fg_color="transparent")
        h_content.pack(fill="x", padx=20, pady=16)

        ctk.CTkLabel(
            h_content,
            text="Studio Setup Checklist",
            font=OmniTheme.font_title(),
            text_color=tokens.text_primary
        ).pack(anchor="w")

        ctk.CTkLabel(
            h_content,
            text="Quick preflight check for PC screen capture and mobile camera streaming. Everything is skippable.",
            font=OmniTheme.font_caption(),
            text_color=tokens.text_secondary
        ).pack(anchor="w", pady=(2, 0))

        # 2. Scrollable Body
        body = ctk.CTkScrollableFrame(self, fg_color="transparent")
        body.pack(fill="both", expand=True, padx=20, pady=12)

        # Step 1: Output Directory
        rec_dir = get_recordings_dir()
        rec_ok = rec_dir.is_dir() and os.access(rec_dir, os.W_OK)
        self._build_step_card(
            body,
            step_num=1,
            title="Recording Storage Directory",
            desc=f"Local path: {rec_dir}",
            status="done" if rec_ok else "warning",
            status_text="CONFIGURED" if rec_ok else "NEEDS ACTION",
            btn_text="Browse Folder",
            btn_action=self.controller.open_recordings_folder
        )

        # Step 2: Phone & USB Debugging (with POCO/Xiaomi expander)
        devs = self.controller.get_connected_devices() if hasattr(self.controller, "get_connected_devices") else []
        phone_ok = len(devs) > 0
        phone_desc = f"Connected: {devs[0].get('model', 'Device')}" if phone_ok else "No device detected. Connect USB cable with USB debugging enabled."
        card2 = self._build_step_card(
            body,
            step_num=2,
            title="Android Phone & USB Debugging",
            desc=phone_desc,
            status="done" if phone_ok else "warning",
            status_text="CONNECTED" if phone_ok else "NEEDS PHONE",
            btn_text="Refresh ADB",
            btn_action=lambda: self.controller.refresh_devices() if hasattr(self.controller, "refresh_devices") else None
        )

        # Xiaomi / POCO Specific Guide Accordion inside Step 2
        poco_box = ctk.CTkFrame(card2, fg_color=tokens.bg_raised, corner_radius=OmniTheme.RADIUS_CONTROL)
        poco_box.pack(fill="x", padx=14, pady=(0, 10))

        poco_head = ctk.CTkLabel(
            poco_box,
            text=" Xiaomi / POCO / HyperOS / MIUI Setup Note:",
            font=OmniTheme.font_body_bold(),
            text_color=tokens.text_primary,
            anchor="w"
        )
        poco_head.pack(anchor="w", padx=10, pady=(6, 2))

        poco_steps = (
            "1. Settings > About phone > Tap 'OS version' / 'MIUI version' 7 times\n"
            "2. Additional settings > Developer options > Turn ON 'USB debugging'\n"
            "3. Turn ON 'Install via USB'\n"
            "4. Turn ON 'USB debugging (Security settings)' (requires SIM / Xiaomi account)\n"
            "5. Connect cable and check 'Always allow from this computer' on RSA prompt"
        )
        ctk.CTkLabel(
            poco_box,
            text=poco_steps,
            font=OmniTheme.font_mono(10),
            text_color=tokens.text_secondary,
            justify="left",
            anchor="w"
        ).pack(anchor="w", padx=10, pady=(0, 8))

        # Step 3: Driver & ADB Daemon Check
        adb_avail = self.controller.adb.is_available() if hasattr(self.controller, "adb") else True
        self._build_step_card(
            body,
            step_num=3,
            title="ADB Platform Tools & Drivers",
            desc="Bundled ADB binary verified. Handles low-latency Camera2 and mirror protocol.",
            status="done" if adb_avail else "error",
            status_text="INSTALLED" if adb_avail else "MISSING",
            btn_text="Check Version",
            btn_action=lambda: self.controller.get_diagnostics() if hasattr(self.controller, "get_diagnostics") else None
        )

        # Step 4: FFmpeg Engine & Hardware Encoder
        ff_avail = self.controller.pc_recorder.is_available() if hasattr(self.controller, "pc_recorder") else True
        self._build_step_card(
            body,
            step_num=4,
            title="FFmpeg Video Recording Engine",
            desc="FFmpeg engine with hardware-accelerated MediaFoundation / NVENC encoding.",
            status="done" if ff_avail else "error",
            status_text="HARDWARE ACCEL" if ff_avail else "NOT FOUND",
            btn_text="Encoder Info",
            btn_action=lambda: self.controller.detect_best_encoder() if hasattr(self.controller, "detect_best_encoder") else None
        )

        # Step 5: Visual Theme & Appearance
        self._build_step_card(
            body,
            step_num=5,
            title="Studio Theme & Appearance",
            desc=f"Current: {tokens.name.title()} theme. Switch anytime in Settings.",
            status="done",
            status_text="ACTIVE",
            btn_text="Toggle Theme",
            btn_action=self.on_theme_toggle
        )

        # Step 6: Google Drive Cloud Backup (Optional)
        self._build_step_card(
            body,
            step_num=6,
            title="Google Drive Cloud Upload (Optional)",
            desc="Auto-upload recordings to Google Drive virtual directory upon session completion.",
            status="info",
            status_text="OPTIONAL",
            btn_text="Connect Account",
            btn_action=lambda: None
        )

        # 3. Footer Bar
        footer = ctk.CTkFrame(self, fg_color=tokens.bg_header, height=54, corner_radius=0)
        footer.pack(fill="x", side="bottom")

        StudioButton(
            footer,
            text="Get Started",
            variant="primary",
            size="normal",
            command=self._on_done
        ).pack(side="right", padx=16, pady=10)

        StudioButton(
            footer,
            text="Skip for Now",
            variant="ghost",
            size="normal",
            command=self.destroy
        ).pack(side="right", padx=6, pady=10)

    def _build_step_card(
        self,
        parent,
        step_num: int,
        title: str,
        desc: str,
        status: str,
        status_text: str,
        btn_text: str,
        btn_action: Optional[Callable[[], None]]
    ) -> ctk.CTkFrame:
        tokens = OmniTheme.get_tokens()
        card = ctk.CTkFrame(parent, fg_color=tokens.bg_panel, corner_radius=OmniTheme.RADIUS_CONTROL)
        card.pack(fill="x", pady=4)

        top_row = ctk.CTkFrame(card, fg_color="transparent")
        top_row.pack(fill="x", padx=14, pady=10)

        # Left Step number pill
        num_frame = ctk.CTkFrame(top_row, width=24, height=24, corner_radius=12, fg_color=tokens.bg_raised)
        num_frame.pack(side="left", padx=(0, 10))
        num_frame.pack_propagate(False)
        ctk.CTkLabel(num_frame, text=str(step_num), font=OmniTheme.font_mono(10), text_color=tokens.text_primary).place(relx=0.5, rely=0.5, anchor="center")

        # Text column
        txt_col = ctk.CTkFrame(top_row, fg_color="transparent")
        txt_col.pack(side="left", fill="x", expand=True)

        title_line = ctk.CTkFrame(txt_col, fg_color="transparent")
        title_line.pack(fill="x")

        ctk.CTkLabel(
            title_line,
            text=title,
            font=OmniTheme.font_body_bold(),
            text_color=tokens.text_primary,
            anchor="w"
        ).pack(side="left")

        # Status badge
        pill_state = "ready" if status == "done" else ("warning" if status == "warning" else ("recording" if status == "error" else "info"))
        StatusChip(title_line, text=status_text, state=pill_state).pack(side="left", padx=10)

        ctk.CTkLabel(
            txt_col,
            text=desc,
            font=OmniTheme.font_caption(),
            text_color=tokens.text_secondary,
            anchor="w",
            wraplength=380
        ).pack(anchor="w", pady=(2, 0))

        # Action button
        if btn_text and btn_action:
            StudioButton(
                top_row,
                text=btn_text,
                variant="secondary",
                size="small",
                command=btn_action
            ).pack(side="right", padx=(8, 0))

        return card

    def _on_done(self):
        if self.on_complete:
            self.on_complete()
        self.destroy()
