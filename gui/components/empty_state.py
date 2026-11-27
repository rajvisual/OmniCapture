from typing import Callable, Optional
import customtkinter as ctk

from gui.theme import OmniTheme, ThemeTokens

class CanvasEmptyState(ctk.CTkFrame):
    """
    Polished Empty State for Live Studio Canvas.
    Displayed when no hardware device is connected or active.
    Features:
    - Subtle device icon wireframe
    - Clear, readable typography (Segoe UI Variable)
    - Actionable secondary button to initiate hardware discovery or diagnostics
    """

    def __init__(
        self,
        parent,
        on_refresh: Optional[Callable] = None,
        on_diagnostics: Optional[Callable] = None,
        **kwargs
    ):
        tokens = OmniTheme.get_tokens()
        super().__init__(
            parent,
            fg_color=tokens.stage_bg_card,
            border_width=1,
            border_color=tokens.stage_border_card,
            corner_radius=OmniTheme.RADIUS_CARD,
            **kwargs
        )
        self.on_refresh = on_refresh
        self.on_diagnostics = on_diagnostics

        self._build_ui(tokens)

    def _build_ui(self, tokens: ThemeTokens):
        inner = ctk.CTkFrame(self, fg_color="transparent")
        inner.place(relx=0.5, rely=0.5, anchor="center")

        # Subtle device symbol (Phone + Display)
        self.icon_lbl = ctk.CTkLabel(
            inner,
            text="📱",
            font=ctk.CTkFont(size=32),
            text_color=tokens.stage_text_dim
        )
        self.icon_lbl.pack(pady=(0, 6))

        # Primary Guidance (light-on-dark token pair on stage)
        self.title_lbl = ctk.CTkLabel(
            inner,
            text="Connect a phone via USB to start",
            font=OmniTheme.font_section(),
            text_color=tokens.stage_text_primary
        )
        self.title_lbl.pack(pady=(0, 4))

        # Secondary Description
        self.desc_lbl = ctk.CTkLabel(
            inner,
            text="Enable USB Debugging on your Android device to stream\nlow-latency screen mirror or raw camera sensor feeds.",
            font=OmniTheme.font_caption(),
            text_color=tokens.stage_text_muted,
            justify="center"
        )
        self.desc_lbl.pack(pady=(0, 14))

        # Secondary Action Buttons (Stage dark controls)
        btn_box = ctk.CTkFrame(inner, fg_color="transparent")
        btn_box.pack()

        self.btn_refresh = ctk.CTkButton(
            btn_box,
            text="Scan for Devices",
            width=130,
            height=OmniTheme.CONTROL_HEIGHT,
            font=OmniTheme.font_body(),
            fg_color=tokens.stage_btn_bg,
            hover_color=tokens.stage_btn_hover,
            text_color=tokens.stage_text_primary,
            border_width=1,
            border_color=tokens.stage_border_card,
            corner_radius=OmniTheme.RADIUS_CONTROL,
            command=self.on_refresh
        )
        self.btn_refresh.pack(side="left", padx=4)

        if self.on_diagnostics:
            self.btn_diag = ctk.CTkButton(
                btn_box,
                text="Diagnostics",
                width=110,
                height=OmniTheme.CONTROL_HEIGHT,
                font=OmniTheme.font_body(),
                fg_color="transparent",
                hover_color=tokens.stage_btn_bg,
                text_color=tokens.stage_text_muted,
                border_width=1,
                border_color=tokens.stage_border_card,
                corner_radius=OmniTheme.RADIUS_CONTROL,
                command=self.on_diagnostics
            )
            self.btn_diag.pack(side="left", padx=4)

    def apply_tokens(self, tokens: ThemeTokens):
        self.configure(
            fg_color=tokens.stage_bg_card,
            border_color=tokens.stage_border_card
        )
        self.icon_lbl.configure(text_color=tokens.stage_text_dim)
        self.title_lbl.configure(text_color=tokens.stage_text_primary)
        self.desc_lbl.configure(text_color=tokens.stage_text_muted)
        self.btn_refresh.configure(
            fg_color=tokens.stage_btn_bg,
            hover_color=tokens.stage_btn_hover,
            text_color=tokens.stage_text_primary,
            border_color=tokens.stage_border_card
        )
        if hasattr(self, "btn_diag"):
            self.btn_diag.configure(
                hover_color=tokens.stage_btn_bg,
                text_color=tokens.stage_text_muted,
                border_color=tokens.stage_border_card
            )
