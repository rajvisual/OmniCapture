import customtkinter as ctk
from typing import Tuple

class OmniTheme:
    """
    Centralized, professional desktop design system for OmniCapture Studio.
    Inspired by OBS Studio, DaVinci Resolve, and modern Windows 11 design guidelines.
    Eliminates decorative AI visual slop in favor of functional clarity, precise 4px spacing,
    and a disciplined dark studio palette.
    """
    # -------------------------------------------------------------------------
    # Neutral Surfaces & Studio Panels (4-tier hierarchy)
    # -------------------------------------------------------------------------
    BG_ROOT = "#0F1015"               # Deepest background (application root)
    BG_CANVAS = "#08090D"             # Viewfinder / broadcast canvas background
    BG_DOCK = "#15161E"               # Modular dock panels (Scenes, Sources, Mixer, Inspector)
    BG_DOCK_HEADER = "#1B1D27"        # Dock headers and toolbar strips
    BG_CARD = "#191B24"               # Interactive elements and containers
    BG_CARD_HOVER = "#232634"         # Surface hover state
    BG_CARD_ACTIVE = "#2C3042"        # Surface active / pressed state
    BG_INPUT = "#1E202B"              # Form controls, text entries, and segmented buttons
    BG_INPUT_HOVER = "#272937"        # Input hover state
    BG_TOOLTIP = "#252838"            # Flyout menus and tooltips

    # Borders & Dividers
    BORDER_SUBTLE = "#252736"         # Low-contrast dock boundaries
    BORDER_DEFAULT = "#2D3042"        # Standard control borders
    BORDER_FOCUS = "#3B82F6"          # Keyboard focus / selection outline
    BG_CARD_BORDER = BORDER_SUBTLE

    # -------------------------------------------------------------------------
    # Primary Interactive Accent (Disciplined Studio Blue)
    # -------------------------------------------------------------------------
    ACCENT_PRIMARY = "#2563EB"
    ACCENT_PRIMARY_HOVER = "#1D4ED8"
    ACCENT_PRIMARY_ACTIVE = "#1E40AF"

    # -------------------------------------------------------------------------
    # Semantic Status & Operational Indicators
    # -------------------------------------------------------------------------
    STATUS_CONNECTED = "#10B981"      # Emerald green (Live, ready, active hardware)
    STATUS_DISCONNECTED = "#71717A"   # Muted slate (Idle, unattached)
    STATUS_WARNING = "#F59E0B"         # Amber (Caution, unauthorized, dropped frames)
    STATUS_RECORDING = "#EF4444"       # Crimson red (Active capture, live broadcast)
    STATUS_RECORDING_HOVER = "#DC2626"
    STATUS_INFO = "#38BDF8"            # Sky blue (Informational messages)
    STATUS_OFFLINE = "#EF4444"

    # Audio Digital Metering Scale (DAW standard: Green -> Amber -> Red)
    VU_BG = "#0D1017"
    VU_GREEN = "#10B981"              # Normal signal (-inf to -12 dB)
    VU_YELLOW = "#F59E0B"             # Peak warning (-12 dB to -3 dB)
    VU_RED = "#EF4444"                # Digital clipping (-3 dB to 0 dB)

    # -------------------------------------------------------------------------
    # Typography Scale (Strict hierarchy based on Segoe UI & Consolas)
    # -------------------------------------------------------------------------
    TEXT_MAIN = "#F4F4F6"             # Primary high-contrast text
    TEXT_BODY = "#D4D5DC"             # Secondary reading text
    TEXT_MUTED = "#9DA3B4"            # Labels, secondary descriptions
    TEXT_DIM = "#6B7285"              # Disabled text, placeholders, hotkey legends

    # -------------------------------------------------------------------------
    # Spacing Scale (Standard 4px base grid)
    # -------------------------------------------------------------------------
    SPACE_XS = 4
    SPACE_SM = 8
    SPACE_MD = 12
    SPACE_LG = 16
    SPACE_XL = 24

    # Corner Radius (Restrained 4-6px; clean industrial aesthetic)
    RADIUS_CONTROL = 4
    RADIUS_CARD = 6
    RADIUS_POPUP = 6

    # -------------------------------------------------------------------------
    # Backward Compatibility Aliases for Unit Tests
    # -------------------------------------------------------------------------
    ACCENT_CYAN = ACCENT_PRIMARY
    ACCENT_CYAN_HOVER = ACCENT_PRIMARY_HOVER
    ACCENT_GREEN = STATUS_CONNECTED
    ACCENT_GREEN_HOVER = "#059669"
    ACCENT_RED = STATUS_RECORDING
    ACCENT_RED_HOVER = STATUS_RECORDING_HOVER
    ACCENT_AMBER = STATUS_WARNING
    ACCENT_PURPLE = ACCENT_PRIMARY
    ACCENT_PURPLE_HOVER = ACCENT_PRIMARY_HOVER

    # -------------------------------------------------------------------------
    # Helper Methods
    # -------------------------------------------------------------------------
    @classmethod
    def font_title(cls) -> tuple:
        return ("Segoe UI", 13, "bold")

    @classmethod
    def font_section(cls) -> tuple:
        return ("Segoe UI", 11, "bold")

    @classmethod
    def font_body(cls) -> tuple:
        return ("Segoe UI", 11)

    @classmethod
    def font_label(cls) -> tuple:
        return ("Segoe UI", 10)

    @classmethod
    def font_mono(cls, size: int = 10, weight: str = "normal") -> tuple:
        return ("Consolas", size, weight)

    @classmethod
    def apply_appearance(cls):
        """Configure global CustomTkinter appearance settings."""
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")
